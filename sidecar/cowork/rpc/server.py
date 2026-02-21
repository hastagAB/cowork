"""JSON-RPC server — communicates with the Tauri Rust host via stdin/stdout."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Callable

from cowork.agent.orchestrator import AgentEvent, Orchestrator
from cowork.llm.client import LLMClient
from cowork.models import RPCRequest, RPCResponse
from cowork.storage.config import load_config
from cowork.tools.base import create_default_registry

logger = logging.getLogger(__name__)


class RPCServer:
    """JSON-RPC server that reads from stdin and writes to stdout.

    This is the bridge between the Tauri Rust backend and the Python agent engine.
    In development, it can also be used standalone for testing.
    """

    def __init__(self):
        self.config = load_config()
        self.registry = create_default_registry()
        self.llm = LLMClient(self.config.llm)
        self._running = False

    def _emit_event(self, event: AgentEvent) -> None:
        """Push an event to the Rust host via stdout."""
        notification = {
            "jsonrpc": "2.0",
            "method": "event",
            "params": event.to_dict(),
        }
        self._write(notification)

    def _write(self, data: dict) -> None:
        """Write a JSON-RPC message to stdout."""
        line = json.dumps(data, default=str)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _respond(self, request_id: int | str | None, result: dict | None = None, error: dict | None = None) -> None:
        resp = RPCResponse(id=request_id, result=result, error=error)
        self._write(resp.model_dump(exclude_none=True))

    async def handle_request(self, request: RPCRequest) -> None:
        """Dispatch an incoming JSON-RPC request to the appropriate handler."""
        method = request.method
        params = request.params

        try:
            if method == "start_task":
                result = await self._handle_start_task(params)
            elif method == "get_config":
                result = self._handle_get_config()
            elif method == "set_config":
                result = self._handle_set_config(params)
            elif method == "ping":
                result = {"pong": True}
            elif method == "list_tools":
                result = {"tools": [t.to_llm_schema() for t in self.registry.list_all()]}
            else:
                self._respond(request.id, error={"code": -32601, "message": f"Unknown method: {method}"})
                return

            self._respond(request.id, result=result)
        except Exception as exc:
            logger.exception("Error handling %s", method)
            self._respond(request.id, error={"code": -32000, "message": str(exc)})

    async def _handle_start_task(self, params: dict) -> dict:
        """Start a new agent task."""
        goal = params.get("goal", "")
        files = params.get("files", [])

        if not goal:
            raise ValueError("Missing required parameter: goal")

        orchestrator = Orchestrator(
            llm=self.llm,
            registry=self.registry,
            config=self.config.agent,
            on_event=self._emit_event,
        )

        return await orchestrator.run_task(goal, attached_files=files)

    def _handle_get_config(self) -> dict:
        config = load_config()
        data = config.model_dump()
        # Never expose the API key
        if data.get("llm", {}).get("api_key"):
            data["llm"]["api_key"] = "***"
            data["llm"]["has_api_key"] = True
        else:
            data["llm"]["has_api_key"] = False
        return data

    def _handle_set_config(self, params: dict) -> dict:
        from cowork.storage.config import set_config_value

        key = params.get("key", "")
        value = params.get("value", "")
        if not key:
            raise ValueError("Missing required parameter: key")
        set_config_value(key, value)
        # Reload config
        self.config = load_config()
        self.llm = LLMClient(self.config.llm)
        return {"ok": True}

    async def run(self) -> None:
        """Main loop — read JSON-RPC requests from stdin, process, respond on stdout."""
        # Log to file, not stdout (stdout is for JSON-RPC)
        from cowork.storage.config import COWORK_DIR

        log_path = COWORK_DIR / "logs" / "sidecar.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            handlers=[logging.FileHandler(str(log_path), mode="a")],
            force=True,
        )

        logger.info("Cowork sidecar started")
        self._running = True

        # Signal readiness
        self._write({"jsonrpc": "2.0", "method": "ready", "params": {"version": "0.1.0"}})

        # Use a thread to read stdin (connect_read_pipe fails on Windows ProactorEventLoop)
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _read_stdin():
            """Read lines from stdin in a background thread."""
            try:
                for raw_line in sys.stdin:
                    line = raw_line.strip()
                    if line:
                        loop.call_soon_threadsafe(queue.put_nowait, line)
            except (EOFError, OSError):
                pass
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        import threading
        reader_thread = threading.Thread(target=_read_stdin, daemon=True)
        reader_thread.start()

        while self._running:
            try:
                line = await queue.get()
                if line is None:
                    break  # stdin closed

                data = json.loads(line)
                request = RPCRequest(**data)
                await self.handle_request(request)

            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON from host: %s", exc)
            except Exception as exc:
                logger.exception("Unexpected error in main loop: %s", exc)

        logger.info("Cowork sidecar shutting down")
