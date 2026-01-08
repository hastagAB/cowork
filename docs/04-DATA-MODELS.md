# Data Models — Cowork

## 1. SQLite Schema

### tasks

```sql
CREATE TABLE tasks (
    id              TEXT PRIMARY KEY,           -- UUID
    goal            TEXT NOT NULL,              -- User's original goal text
    status          TEXT NOT NULL DEFAULT 'planning',
                    -- planning | running | confirming | completed | failed | cancelled
    attached_files  TEXT,                       -- JSON array of file paths
    result_summary  TEXT,                       -- Final summary shown to user
    deliverable_dir TEXT,                       -- Path to output folder/files
    total_steps     INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    tokens_used     INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at    TEXT,
    duration_ms     INTEGER
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
```

### steps

```sql
CREATE TABLE steps (
    id          TEXT PRIMARY KEY,              -- UUID
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    tool_name   TEXT NOT NULL,                 -- Tool that was called
    tool_args   TEXT NOT NULL,                 -- JSON of arguments
    description TEXT NOT NULL,                 -- Human-readable step description
    status      TEXT NOT NULL DEFAULT 'pending',
                -- pending | running | completed | failed | skipped
    result      TEXT,                          -- JSON of tool result
    error       TEXT,                          -- Error message if failed
    started_at  TEXT,
    completed_at TEXT,
    duration_ms INTEGER
);

CREATE INDEX idx_steps_task ON steps(task_id, step_number);
```

### deliverables

```sql
CREATE TABLE deliverables (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,                 -- Absolute path to generated file
    file_type   TEXT NOT NULL,                 -- md | docx | xlsx | csv | pdf | folder
    file_size   INTEGER,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX idx_deliverables_task ON deliverables(task_id);
```

### audit_log

```sql
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT REFERENCES tasks(id),
    operation   TEXT NOT NULL,                 -- READ | WRITE | DELETE | MOVE | COPY | CREATE_DIR
    file_path   TEXT NOT NULL,
    destination TEXT,                          -- For MOVE/COPY
    status      TEXT NOT NULL,                 -- ok | denied | user_confirmed | user_denied | error
    details     TEXT,                          -- Additional context
    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX idx_audit_task ON audit_log(task_id);
CREATE INDEX idx_audit_time ON audit_log(timestamp DESC);
```

### indexed_folders

```sql
CREATE TABLE indexed_folders (
    id              TEXT PRIMARY KEY,
    folder_path     TEXT NOT NULL UNIQUE,
    collection_name TEXT NOT NULL,             -- ChromaDB collection name
    doc_count       INTEGER DEFAULT 0,
    chunk_count     INTEGER DEFAULT 0,
    last_indexed_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

### undo_records

```sql
CREATE TABLE undo_records (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    operation       TEXT NOT NULL,             -- MOVE | DELETE | OVERWRITE
    original_path   TEXT NOT NULL,
    backup_path     TEXT NOT NULL,             -- Path in ~/.cowork/undo/
    new_path        TEXT,                      -- For MOVE operations
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX idx_undo_task ON undo_records(task_id);
```

---

## 2. Pydantic Models (Python Sidecar)

### Core Models

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    PLANNING = "planning"
    RUNNING = "running"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(BaseModel):
    id: str
    goal: str
    status: TaskStatus = TaskStatus.PLANNING
    attached_files: list[str] = []
    result_summary: str | None = None
    deliverable_dir: str | None = None
    total_steps: int = 0
    completed_steps: int = 0
    tokens_used: int = 0
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class Step(BaseModel):
    id: str
    task_id: str
    step_number: int
    tool_name: str
    tool_args: dict
    description: str
    status: StepStatus = StepStatus.PENDING
    result: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Deliverable(BaseModel):
    id: str
    task_id: str
    file_path: str
    file_type: str
    file_size: int | None = None
    description: str | None = None
```

### Agent Models

```python
class PlanStep(BaseModel):
    """A single planned step from the LLM planner."""
    step_number: int
    tool: str
    args: dict
    reason: str


class Plan(BaseModel):
    """The full plan generated by the LLM."""
    steps: list[PlanStep]
    reasoning: str


class ToolResult(BaseModel):
    """Result returned by a tool execution."""
    success: bool
    data: dict | None = None
    error: str | None = None
    needs_confirmation: bool = False
    confirmation_message: str | None = None


class ConfirmationRequest(BaseModel):
    """Sent to UI when a destructive operation needs approval."""
    action_id: str
    task_id: str
    operation: str
    description: str
    file_path: str
    destination: str | None = None
```

### JSON-RPC Models

```python
class RPCRequest(BaseModel):
    """Incoming JSON-RPC request from Rust host."""
    jsonrpc: str = "2.0"
    method: str
    params: dict = {}
    id: int | str | None = None


class RPCResponse(BaseModel):
    """Outgoing JSON-RPC response to Rust host."""
    jsonrpc: str = "2.0"
    result: dict | None = None
    error: dict | None = None
    id: int | str | None = None


class RPCEvent(BaseModel):
    """Event pushed from Python sidecar to Rust host (no id, no response expected)."""
    jsonrpc: str = "2.0"
    method: str  # e.g., "step_started", "step_completed", "confirmation_needed"
    params: dict = {}
```

### Config Models

```python
class LLMConfig(BaseModel):
    provider: str = "anthropic"          # anthropic | openai | ollama
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None           # Loaded from OS keyring at runtime
    base_url: str | None = None          # For Ollama or custom endpoints
    max_tokens: int = 4096
    temperature: float = 0.3


class PermissionConfig(BaseModel):
    allowed_paths: list[str] = []
    confirm_destructive: bool = True
    dry_run: bool = False


class AppConfig(BaseModel):
    llm: LLMConfig = LLMConfig()
    permissions: PermissionConfig = PermissionConfig()
    max_steps_per_task: int = 50
    max_replans: int = 3
    task_timeout_seconds: int = 600
```

---

## 3. TypeScript Types (Frontend)

```typescript
// Task types
interface Task {
  id: string;
  goal: string;
  status: "planning" | "running" | "confirming" | "completed" | "failed" | "cancelled";
  attachedFiles: string[];
  resultSummary: string | null;
  totalSteps: number;
  completedSteps: number;
  tokensUsed: number;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
}

interface Step {
  id: string;
  taskId: string;
  stepNumber: number;
  toolName: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  error: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

interface Deliverable {
  id: string;
  taskId: string;
  filePath: string;
  fileType: string;
  fileSize: number | null;
  description: string | null;
}

// Events from backend
interface StepEvent {
  type: "step_started" | "step_completed" | "step_failed";
  taskId: string;
  step: Step;
}

interface ConfirmationEvent {
  type: "confirmation_needed";
  actionId: string;
  taskId: string;
  operation: string;
  description: string;
  filePath: string;
  destination: string | null;
}

interface TaskCompleteEvent {
  type: "task_completed";
  taskId: string;
  summary: string;
  deliverables: Deliverable[];
}

// Config
interface AppConfig {
  llm: {
    provider: "anthropic" | "openai" | "ollama";
    model: string;
    hasApiKey: boolean;  // Never expose actual key to frontend
    baseUrl: string | null;
  };
  permissions: {
    allowedPaths: string[];
    confirmDestructive: boolean;
    dryRun: boolean;
  };
}
```

---

## 4. config.toml Schema

```toml
[llm]
provider = "anthropic"          # anthropic | openai | ollama
model = "claude-sonnet-4-20250514"
# api_key stored in OS keyring, NOT here
base_url = ""                   # Only for ollama or custom
max_tokens = 4096
temperature = 0.3

[permissions]
allowed_paths = [
    "~/Documents",
    "~/Downloads",
    "~/Desktop"
]
confirm_destructive = true
dry_run = false

[agent]
max_steps_per_task = 50
max_replans = 3
task_timeout_seconds = 600

[ui]
theme = "system"                # system | light | dark
show_token_usage = true
```
