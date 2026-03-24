# Cowork

A local-first AI desktop agent that autonomously handles knowledge work on your computer.

Give it a goal in plain English — Cowork reads your files, calls tools, and delivers results. No cloud uploads, no subscriptions: everything runs locally on your machine, with LLM calls going directly to your own API key.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20%2B-green)
![Electron](https://img.shields.io/badge/electron-41-blueviolet)

---

## Features

- **Agentic tool-calling loop** — powered by OpenAI-compatible function calling (GPT-4o, GPT-5, Azure OpenAI, etc.)
- **File system tools** — list, read, write, search, create directories
- **Dark-themed desktop UI** — built with React, TypeScript, and Zustand
- **Multi-provider LLM support** — Azure OpenAI, OpenAI, Anthropic, Ollama
- **Local-first** — your data never leaves your machine; LLM calls use your own API key
- **Real-time activity feed** — watch the agent think, call tools, and deliver results

## Architecture

```
┌──────────────────────────────────────────────┐
│              Electron Shell                  │
│  ┌────────────────────────────────────────┐  │
│  │     React + TypeScript Frontend        │  │
│  │  (Vite · Zustand · Dark Theme)         │  │
│  └──────────────┬─────────────────────────┘  │
│                 │ IPC (contextBridge)         │
│  ┌──────────────┴─────────────────────────┐  │
│  │       Electron Main Process            │  │
│  │  (Window · IPC Handlers · Sidecar Mgr) │  │
│  └──────────────┬─────────────────────────┘  │
└─────────────────┼────────────────────────────┘
                  │ JSON-RPC (stdin/stdout)
┌─────────────────┼────────────────────────────┐
│  Python Sidecar │                            │
│  ┌──────────────┴─────────────────────────┐  │
│  │  Agent Orchestrator (agentic loop)     │  │
│  │  LLM Client ─── Tool Registry         │  │
│  │  Config ──────── SQLite Storage        │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| [Python](https://python.org) | 3.11+ | Agent engine |
| [Node.js](https://nodejs.org) | 20+ | Electron + React frontend |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager (recommended) |
| LLM API key | — | Azure OpenAI, OpenAI, Anthropic, or local Ollama |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/hastagAB/cowork.git
cd cowork

# 2. Install Python sidecar dependencies
cd sidecar
uv sync          # or: pip install -e ".[dev]"

# 3. Install frontend dependencies
cd ../app
npm install

# 4. Configure your LLM provider
#    Option A: Settings UI (launch app → Settings → fill in fields → Save)
#    Option B: Edit ~/.cowork/config.toml directly
#    Option C: Copy .env.example to .env and set keys

# 5. Start in development mode
npm run dev      # starts Vite dev server + Electron + Python sidecar
```

## Configuration

Cowork stores configuration at `~/.cowork/config.toml`. You can edit it directly or use the Settings panel in the app.

```toml
[llm]
provider = "azure_openai"          # azure_openai | openai | anthropic | ollama
model = "gpt-4o"
api_key = "your-api-key"
endpoint = "https://your-resource.openai.azure.com"  # Azure only
deployment = "gpt-4o"              # Azure only
api_version = "2024-12-01-preview" # Azure only
max_tokens = 4096
temperature = 0.3

[permissions]
allowed_paths = []                 # restrict agent to these dirs (empty = no restriction)
confirm_destructive = true         # ask before writes/deletes

[agent]
max_steps_per_task = 50
max_replans = 3
task_timeout_seconds = 600
```

## Project Structure

```
cowork/
├── app/                         # Electron desktop application
│   ├── electron/                # Main process
│   │   ├── main.js              #   Window, IPC handlers
│   │   ├── preload.js           #   Context bridge (secure API)
│   │   └── sidecar.js           #   Python process manager
│   ├── src/                     # React frontend
│   │   ├── App.tsx              #   Root component + sidecar events
│   │   ├── store.ts             #   Zustand state management
│   │   ├── types.ts             #   TypeScript interfaces
│   │   ├── styles.css           #   Global dark theme
│   │   └── components/          #   UI components
│   │       ├── GoalInput.tsx    #     Goal entry form
│   │       ├── TaskView.tsx     #     Task activity feed + results
│   │       ├── Sidebar.tsx      #     Task list sidebar
│   │       └── SettingsPanel.tsx #     LLM configuration
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── sidecar/                     # Python agent engine
│   ├── cowork/
│   │   ├── agent/               # Agentic loop
│   │   │   ├── orchestrator.py  #   Core tool-calling loop
│   │   │   ├── context.py       #   Task context state
│   │   │   ├── executor.py      #   Step execution
│   │   │   ├── planner.py       #   (legacy) JSON plan generation
│   │   │   ├── verifier.py      #   (legacy) Result verification
│   │   │   └── permissions.py   #   Path/operation permissions
│   │   ├── llm/
│   │   │   └── client.py        #   Multi-provider LLM client
│   │   ├── tools/
│   │   │   ├── base.py          #   BaseTool ABC + ToolRegistry
│   │   │   └── fs.py            #   6 filesystem tools
│   │   ├── rpc/
│   │   │   └── server.py        #   JSON-RPC over stdin/stdout
│   │   ├── storage/
│   │   │   ├── config.py        #   TOML config management
│   │   │   └── database.py      #   SQLite schema
│   │   ├── models.py            #   Pydantic data models
│   │   └── __main__.py          #   Entry point
│   ├── tests/                   #   pytest test suite
│   └── pyproject.toml
├── docs/                        # Design documents
│   ├── 01-PRD.md                #   Product requirements
│   ├── 02-TECHNICAL-SPEC.md     #   Architecture design
│   ├── 03-IMPLEMENTATION-PLAN.md#   Phased build plan
│   ├── 04-DATA-MODELS.md        #   Database schema
│   └── 05-TOOL-SPECS.md         #   Tool interface contracts
├── .env.example                 #   Environment variable template
├── .editorconfig
├── .gitignore
├── LICENSE
└── README.md
```

## Available Tools

The agent currently has 6 filesystem tools:

| Tool | Description |
|---|---|
| `list_directory` | List files and folders with metadata |
| `read_file` | Read file contents (text) |
| `write_file` | Create or overwrite a file |
| `get_file_info` | Get file size, type, modified date |
| `search_files_glob` | Search for files by glob pattern |
| `create_directory` | Create a new directory |

## How It Works

1. **You type a goal** — e.g., "Summarize all the PDF files on my Desktop"
2. **The agent thinks** — sends your goal + available tools to the LLM
3. **The LLM calls tools** — using native function calling (not JSON parsing)
4. **Tool results return** — the agent feeds results back to the LLM
5. **Loop continues** — until the LLM decides the task is complete
6. **You get a summary** — displayed in the activity feed

This is the same pattern used by Claude's computer use and OpenAI's assistants API — a conversational agentic loop with native tool calling.

## Development

### Running Components Separately

```bash
# Python sidecar standalone (for testing)
cd sidecar
uv run python -m cowork

# Vite dev server only
cd app
npm run dev:vite

# Electron only (after Vite is running on :5173)
cd app
npm run dev:electron
```

### Running Tests

```bash
cd sidecar
uv run pytest -v
```

### Code Quality

```bash
cd sidecar
uv run ruff check .
uv run ruff format .
```

## Roadmap

- [x] Phase 1: File system tools + agent loop
- [ ] Phase 2: Document parsers (PDF, DOCX, XLSX)
- [ ] Phase 3: Document generators
- [ ] Phase 4: Semantic search (ChromaDB + embeddings)
- [ ] Phase 5: OCR + image understanding

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit with conventional commits: `git commit -m "feat(agent): add web search tool"`
4. Push and open a Pull Request

## License

[MIT](LICENSE)
