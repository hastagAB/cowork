# Technical Specification — Cowork

## 1. System Architecture

### 1.1 High-Level Overview

Cowork is an **Electron desktop application** with:
- A **React + TypeScript** frontend for the UI (bundled with Vite)
- An **Electron main process** for native OS operations and IPC
- A **Python sidecar** process for AI/ML (agentic tool-calling loop, LLM calls)

```
┌────────────────────────────────────────────────────────────────┐
│                    Electron Desktop App                         │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Frontend (React + TypeScript + Zustand)                 │  │
│  │                                                          │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │ GoalInput│  │ ActivityFeed │  │ ResultView        │  │  │
│  │  │ Panel    │  │ (live steps) │  │ (summary/output)  │  │  │
│  │  └──────────┘  └──────────────┘  └───────────────────┘  │  │
│  │  ┌──────────┐  ┌──────────────┐                         │  │
│  │  │ TaskList │  │ Settings     │                         │  │
│  │  │ (sidebar)│  │ Panel        │                         │  │
│  │  └──────────┘  └──────────────┘                         │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │ IPC (contextBridge / ipcRenderer)    │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │  Electron Main Process                                   │  │
│  │  ├── IPC handlers (bridge to sidecar)                    │  │
│  │  ├── Window management                                   │  │
│  │  ├── Sidecar process manager (spawn/monitor Python)      │  │
│  │  ├── File dialog handlers                                │  │
│  │  └── Event forwarding (sidecar → renderer)               │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │ JSON-RPC (stdin/stdout)              │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │  Python Sidecar (Agent Engine)                           │  │
│  │  ├── Agent orchestrator (agentic tool-calling loop)      │  │
│  │  ├── LLM client (Anthropic / OpenAI / Ollama)            │  │
│  │  ├── Document parsers (PDF, DOCX, XLSX, CSV, images)     │  │
│  │  ├── Embedder + vector store (ChromaDB)                  │  │
│  │  ├── Document generators (DOCX, XLSX, PDF output)        │  │
│  │  └── Tool registry                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

> **Note (2026-03-24):** The implementation pivoted from Tauri 2.0 to **Electron** due to
> Rust toolchain availability constraints. The IPC layer uses Electron's `contextBridge` /
> `ipcRenderer` instead of Tauri commands, and the agent loop uses **OpenAI native function
> calling** instead of the original plan-then-execute JSON parsing approach. The rest of
> the specification (Python sidecar, tools, data models) remains accurate.

### 1.2 Why This Architecture?

| Decision | Rationale |
|---|---|
| **Electron** | Universal cross-platform support, rich Node.js ecosystem, proven stability. |
| **Python sidecar over pure JS** | Python has the richest AI/ML/doc-parsing ecosystem. JS handles UI and OS integration. |
| **JSON-RPC over HTTP** | Sidecar communicates via stdin/stdout. No ports, no network, no firewall issues. |
| **SQLite over Postgres** | Zero-config, local-only, single-file database. |
| **ChromaDB (embedded)** | Local vector store, no server process needed. |

### 1.3 Communication Flow

```
User types goal
    │
    ▼
Frontend ──(Tauri invoke)──▶ Rust Backend
    │                            │
    │                     ──(JSON-RPC)──▶ Python Sidecar
    │                            │              │
    │                            │         Agent Loop runs
    │                            │         (plan, execute tools, verify)
    │                            │              │
    │                     ◀──(JSON-RPC events)──┘
    │                            │
    ◀──(Tauri event stream)──────┘
    │
    ▼
UI updates ActivityFeed in real-time
```

---

## 2. Component Specifications

### 2.1 Frontend (React + TypeScript)

**Framework:** React 19 + TypeScript 5 + Tailwind CSS 4 + Vite
**State management:** Zustand (lightweight, no boilerplate)
**Routing:** React Router v7 (if needed; may be single-page)

**Key components:**

| Component | Purpose |
|---|---|
| `GoalInput` | Text input + file/folder drop zone. Submit button. |
| `ActivityFeed` | Scrolling list of agent steps. Each step: icon, description, status, timestamp. |
| `DeliverableView` | Renders final output: markdown preview, file download links, folder tree. |
| `TaskList` | Sidebar showing task history. Click to view past results. |
| `SettingsPanel` | API key config, model selection, permission management. |
| `ConfirmDialog` | Modal for confirming destructive file operations. |
| `FileDropZone` | Drag-and-drop area for attaching files/folders to a task. |

### 2.2 Tauri Rust Backend

**Responsibilities:**
- Bridge between frontend and Python sidecar
- Native filesystem operations (faster than Python for bulk ops)
- Process management (start, monitor, restart sidecar)
- Config file I/O
- Permission enforcement (block operations outside allowed paths)
- Audit logging

**Key Tauri commands (IPC):**

```rust
#[tauri::command] fn start_task(goal: String, files: Vec<String>) -> TaskId;
#[tauri::command] fn cancel_task(task_id: TaskId) -> bool;
#[tauri::command] fn get_task_history() -> Vec<TaskSummary>;
#[tauri::command] fn get_task_detail(task_id: TaskId) -> TaskDetail;
#[tauri::command] fn confirm_action(action_id: ActionId, approved: bool);
#[tauri::command] fn get_config() -> Config;
#[tauri::command] fn set_config(key: String, value: String);
#[tauri::command] fn select_folder() -> Option<String>;  // native folder picker
#[tauri::command] fn select_files() -> Vec<String>;      // native file picker
```

### 2.3 Python Sidecar (Agent Engine)

**Runtime:** Python 3.11+
**Package manager:** uv (fast, deterministic)
**Communication:** JSON-RPC over stdin/stdout with the Rust host

**Core modules:**

```
agent/
├── orchestrator.py      # Main agent loop: plan → execute → verify → deliver
├── planner.py           # LLM-based task planning
├── executor.py          # Step execution engine
├── verifier.py          # Output quality checking
├── reporter.py          # Deliverable formatting
├── llm_client.py        # Unified LLM interface
├── tool_registry.py     # Register & dispatch tools
├── tools/
│   ├── fs.py            # File system tools
│   ├── parser.py        # Document parsing tools
│   ├── generator.py     # Document generation tools
│   ├── search.py        # Keyword + semantic search
│   └── data.py          # Data extraction & transformation
├── rpc_server.py        # JSON-RPC stdin/stdout server
├── models.py            # Pydantic data models
└── config.py            # Config reader
```

---

## 3. Agent Orchestrator (Core Algorithm)

### 3.1 Agentic Loop

```
                    ┌──────────────┐
                    │  User Goal   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌────▶│  PLAN        │
              │     │ (LLM builds  │
              │     │  step list)  │
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  EXECUTE     │◀──────┐
              │     │ (run next    │       │
              │     │  step tool)  │       │
     re-plan  │     └──────┬───────┘       │ next step
     if stuck │            │               │
              │     ┌──────▼───────┐       │
              │     │  EVALUATE    │───────┘
              │     │ (step ok?    │
              │     │  continue?)  │
              │     └──────┬───────┘
              │            │ all steps done
              │     ┌──────▼───────┐
              └─────│  VERIFY      │
                    │ (goal met?   │
                    │  quality ok?)│
                    └──────┬───────┘
                           │ yes
                    ┌──────▼───────┐
                    │  DELIVER     │
                    │ (format &    │
                    │  present)    │
                    └──────────────┘
```

### 3.2 Planning Prompt Structure

```
System: You are a task planner. Given a user's goal and available tools,
create a numbered step-by-step plan. Each step must use exactly one tool.

Available tools:
{tool_descriptions}

User's goal: {goal}
Attached files: {file_list}
Working directory context: {dir_listing}

Output format (JSON):
{
  "plan": [
    {"step": 1, "tool": "list_directory", "args": {...}, "reason": "..."},
    {"step": 2, "tool": "read_file", "args": {...}, "reason": "..."},
    ...
  ]
}
```

### 3.3 Max Iterations & Safeguards

| Guard | Value |
|---|---|
| Max steps per task | 50 |
| Max re-plans | 3 |
| Max LLM calls per task | 100 |
| Timeout per task | 10 minutes |
| Max file size for parsing | 50 MB |
| Confirmation required after | Any delete, move, or overwrite |

---

## 4. Tool Specifications

Each tool follows a standard interface:

```python
class Tool:
    name: str
    description: str                # Shown to LLM for tool selection
    parameters: dict                # JSON Schema of input params
    requires_confirmation: bool     # Whether to ask user before executing
    
    async def execute(self, params: dict, context: TaskContext) -> ToolResult
```

### 4.1 Tool Categories

| Category | Tools |
|---|---|
| **File System** | `list_directory`, `read_file`, `write_file`, `move_file`, `copy_file`, `delete_file`, `create_directory`, `get_file_info`, `search_files_glob` |
| **Document Parsing** | `parse_pdf`, `parse_docx`, `parse_xlsx`, `parse_csv`, `parse_image_ocr`, `parse_json`, `parse_markdown` |
| **Document Generation** | `generate_docx`, `generate_xlsx`, `generate_csv`, `generate_markdown`, `generate_pdf` |
| **Data Extraction** | `extract_table`, `extract_entities`, `compare_documents`, `deduplicate_files` |
| **Search** | `keyword_search`, `semantic_search`, `index_directory` |
| **Utility** | `get_clipboard`, `set_clipboard`, `open_file_in_app`, `send_notification` |

---

## 5. Security Architecture

### 5.1 Filesystem Sandboxing

```
User configures allowed paths in settings:
  allowed_paths = ["~/Documents", "~/Downloads", "~/Desktop"]

All file operations pass through PermissionGuard:
  1. Resolve to absolute path
  2. Canonicalize (resolve symlinks, ..)
  3. Check against allowed_paths whitelist
  4. Block if outside + log attempt
```

### 5.2 Permission Tiers

| Tier | Operations | UX |
|---|---|---|
| **AUTO** | read_file, list_directory, parse_*, search, get_file_info | Silent |
| **NOTIFY** | write_file (new), create_directory | Toast notification |
| **CONFIRM** | delete_file, move_file, write_file (overwrite) | Modal dialog, user must approve |
| **BLOCKED** | Anything outside allowed_paths, system files, executables | Blocked + logged |

### 5.3 API Key Security

- Stored in OS keyring (not plaintext config) via `keyring` crate / `keytar`
- Never logged, never sent to any endpoint other than the LLM provider
- Config file stores only non-secret settings

### 5.4 Audit Log

Every file operation logged to `~/.cowork/audit.log`:
```
2026-03-24T10:30:00Z | task_abc123 | READ    | ~/Documents/report.pdf | ok
2026-03-24T10:30:01Z | task_abc123 | WRITE   | ~/Documents/summary.md | ok
2026-03-24T10:30:05Z | task_abc123 | DELETE  | ~/Downloads/dup.pdf    | user_confirmed
```

---

## 6. Data Storage

### 6.1 SQLite Schema (see 04-DATA-MODELS.md for full schema)

- `tasks` — Goal, status, timestamps, result path
- `steps` — Per-task step log with tool, args, result
- `deliverables` — Output files produced per task
- `indexed_folders` — Folders registered in the vector store
- `audit_log` — All file operations

### 6.2 Local Filesystem Layout

```
~/.cowork/
├── config.toml              # Non-secret settings
├── cowork.db                # SQLite database
├── vectors/                 # ChromaDB persistent storage
│   └── chroma.sqlite3
├── cache/                   # LLM response cache (optional)
├── templates/               # Task templates
│   ├── organize-folder.json
│   ├── weekly-report.json
│   └── data-extraction.json
├── undo/                    # Shadow copies for undo
│   └── {task_id}/
│       └── {original_path_hash}
└── logs/
    └── audit.log
```

---

## 7. LLM Integration

### 7.1 Provider Abstraction

```python
class LLMClient(Protocol):
    async def complete(self, messages: list[Message], tools: list[ToolDef]) -> LLMResponse: ...
    async def stream(self, messages: list[Message]) -> AsyncIterator[str]: ...
```

### 7.2 Supported Providers

| Provider | Model Examples | Use Case |
|---|---|---|
| **Anthropic** | claude-sonnet-4-20250514, claude-opus-4-20250514 | Best quality, default |
| **OpenAI** | gpt-4o, gpt-4o-mini | Alternative |
| **Ollama** | llama3, mistral, phi-3 | Fully offline, free |

### 7.3 Token Management

- Track token usage per task (stored in `tasks` table)
- Warn user when approaching budget limits
- Summarize context when approaching context window limits
- Cache identical sub-queries within a task to avoid duplicate LLM calls

---

## 8. Build & Distribution

| Platform | Build | Output |
|---|---|---|
| Windows | `cargo tauri build` | `.msi` installer |
| macOS | `cargo tauri build` | `.dmg` bundle |
| Linux | `cargo tauri build` | `.deb` / `.AppImage` |

Python sidecar bundled via:
- `PyInstaller` → single binary, bundled with Tauri as sidecar
- Or `uv` venv bundled in app resources
