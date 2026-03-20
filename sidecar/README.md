# Cowork Sidecar

Python agent engine for the Cowork desktop app. Runs as a child process of Electron, communicating via JSON-RPC over stdin/stdout.

## Responsibilities

- **Agentic loop** — receives a goal, calls LLM with tools, executes tool calls, loops until done
- **LLM client** — multi-provider support (Azure OpenAI, OpenAI, Anthropic, Ollama)
- **Tool registry** — extensible tool system with OpenAI function-calling format
- **Config management** — reads/writes `~/.cowork/config.toml`
- **SQLite storage** — task and step persistence

## Setup

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"
```

## Running

```bash
# As the Electron sidecar (default — reads JSON-RPC from stdin)
uv run python -m cowork

# Run tests
uv run pytest -v

# Lint and format
uv run ruff check .
uv run ruff format .
```

## Adding a New Tool

1. Create a class extending `BaseTool` in `cowork/tools/`
2. Define `name`, `description`, `parameters` (JSON Schema), and `execute()`
3. Register it in `create_default_registry()` in `cowork/tools/base.py`

The tool is automatically exposed to the LLM via `to_openai_tool()`.

## Package Structure

```
cowork/
├── __main__.py      # Entry point
├── models.py        # Pydantic models (Task, Step, Config, etc.)
├── agent/
│   ├── orchestrator.py  # Agentic tool-calling loop
│   ├── context.py       # Task context state
│   ├── executor.py      # Tool dispatch
│   └── permissions.py   # Path permission checks
├── llm/
│   └── client.py        # LLMClient (Azure/OpenAI/Anthropic/Ollama)
├── tools/
│   ├── base.py          # BaseTool + ToolRegistry
│   └── fs.py            # Filesystem tools (6)
├── rpc/
│   └── server.py        # JSON-RPC server (stdin/stdout)
└── storage/
    ├── config.py        # TOML config (~/.cowork/config.toml)
    └── database.py      # SQLite schema
```
