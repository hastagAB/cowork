"""Orchestrator — agentic loop using native OpenAI function calling."""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from typing import Callable

from cowork.agent.context import TaskContext
from cowork.llm.client import LLMClient, Message
from cowork.models import AgentConfig, ToolResult
from cowork.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Co-work, an autonomous AI agent that helps users with knowledge work on their local machine.

You have access to file system tools. Use them to accomplish the user's goal step by step.
- Think about what you need to do, then call the appropriate tool.
- After each tool result, decide whether you need to do more or if the task is complete.
- When the task is fully done, respond with a final text summary (no tool calls).
- Be thorough but efficient. Don't call tools unnecessarily.
- If a tool call fails, try to recover or find an alternative approach.
- Always provide a helpful final summary to the user.

Important: You are working on a Windows filesystem. Use backslashes in paths when appropriate."""


class AgentEvent:
    """Events emitted by the orchestrator to the UI."""

    def __init__(self, event_type: str, data: dict):
        self.type = event_type
        self.data = data

    def to_dict(self) -> dict:
        return {"type": self.type, **self.data}


EventCallback = Callable[[AgentEvent], None]


class Orchestrator:
    """Agentic loop using native function calling."""

    MAX_ITERATIONS = 30

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        config: AgentConfig,
        on_event: EventCallback | None = None,
    ):
        self.llm = llm
        self.registry = registry
        self.config = config
        self.on_event = on_event or (lambda e: None)

    def _emit(self, event_type: str, **data) -> None:
        self.on_event(AgentEvent(event_type, data))

    async def run_task(self, goal: str, attached_files: list[str] | None = None) -> dict:
        """Execute a full task from goal to deliverable using agentic tool-calling loop."""
        task_id = uuid.uuid4().hex[:12]
        context = TaskContext(
            task_id=task_id,
            goal=goal,
            attached_files=attached_files or [],
        )

        self._emit("task_started", task_id=task_id, goal=goal)

        try:
            result = await self._agentic_loop(context)
            self._emit("task_completed", task_id=task_id, **result)
            return {"task_id": task_id, "status": "completed", **result}
        except Exception as exc:
            logger.exception("Task failed: %s", exc)
            self._emit("task_failed", task_id=task_id, error=str(exc))
            return {"task_id": task_id, "status": "failed", "error": str(exc)}

    async def _agentic_loop(self, context: TaskContext) -> dict:
        """Core agentic loop: send goal → LLM calls tools → loop until done."""
        # Build the user message
        user_content = context.goal
        if context.attached_files:
            user_content += "\n\nAttached files:\n" + "\n".join(f"- {f}" for f in context.attached_files)

        # Conversation history for the LLM (list of dicts for OpenAI format)
        messages: list[dict] = [
            {"role": "user", "content": user_content},
        ]

        # Get tools in OpenAI function-calling format
        tools = self.registry.to_openai_tools()
        step_count = 0
        total_tokens = 0

        for iteration in range(self.MAX_ITERATIONS):
            # Call LLM with conversation + tools
            self._emit("thinking", task_id=context.task_id, iteration=iteration + 1)

            llm_messages = [Message(role=m["role"], content=m.get("content"),
                                    tool_calls=m.get("tool_calls"),
                                    tool_call_id=m.get("tool_call_id"),
                                    name=m.get("name"))
                           for m in messages]

            response = await self.llm.complete(llm_messages, system=SYSTEM_PROMPT, tools=tools)
            total_tokens += response.tokens_used

            # Append the assistant message to conversation
            if response.raw_message:
                messages.append(response.raw_message)
            else:
                messages.append({"role": "assistant", "content": response.content})

            # If no tool calls, the LLM is done — return its response
            if not response.tool_calls:
                logger.info("Agent completed after %d iterations, %d tool calls", iteration + 1, step_count)
                return {
                    "summary": response.content or "Task completed.",
                    "tokens_used": total_tokens,
                    "steps_completed": step_count,
                }

            # Execute each tool call
            for tool_call in response.tool_calls:
                step_count += 1
                tool_name = tool_call.name
                tool_args = tool_call.arguments

                self._emit(
                    "step_started",
                    task_id=context.task_id,
                    step_number=step_count,
                    tool=tool_name,
                    description=f"Calling {tool_name}",
                )

                # Execute the tool
                result = await self._execute_tool(tool_name, tool_args, context)

                if result.success:
                    self._emit(
                        "step_completed",
                        task_id=context.task_id,
                        step_number=step_count,
                        tool=tool_name,
                    )
                    result_content = json.dumps(result.data, default=str) if result.data else "Success"
                else:
                    self._emit(
                        "step_failed",
                        task_id=context.task_id,
                        step_number=step_count,
                        tool=tool_name,
                        error=result.error,
                    )
                    result_content = f"Error: {result.error}"

                # Append tool result as a tool message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_content,
                })

        # Exceeded max iterations
        return {
            "summary": "Task reached maximum iteration limit. Partial results may be available.",
            "tokens_used": total_tokens,
            "steps_completed": step_count,
        }

    async def _execute_tool(self, tool_name: str, tool_args: dict, context: TaskContext) -> ToolResult:
        """Execute a single tool by name."""
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

        try:
            return await tool.execute(tool_args, context)
        except Exception as exc:
            logger.exception("Tool %s failed: %s", tool_name, exc)
            return ToolResult(success=False, error=f"{type(exc).__name__}: {exc}")
