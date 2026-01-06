# Implementation Plan — Cowork

## Build Strategy

We build in **5 phases**, each delivering a working increment. Each phase has a clear deliverable that can be tested end-to-end.

---

## Phase 1: Walking Skeleton (Foundation)

**Goal:** A working desktop app that can take a goal, call an LLM, read local files, and display a result.

### Deliverables
- [ ] Tauri project scaffolded with React + TypeScript frontend
- [ ] Python sidecar project scaffolded with uv
- [ ] JSON-RPC communication bridge (Rust ↔ Python)
- [ ] Basic UI: GoalInput → ActivityFeed → ResultView
- [ ] Config system (`~/.cowork/config.toml`) with API key setup
- [ ] LLM client (Anthropic SDK) with streaming
- [ ] 3 basic tools: `list_directory`, `read_file`, `write_file`
- [ ] Simple agent loop: plan (1 pass) → execute → deliver
- [ ] Working use case: "Summarize this file"

### Tech Tasks
```
1. Initialize Tauri 2.0 project
2. Setup React + TS + Tailwind + Vite frontend
3. Create Python sidecar project with uv
4. Implement JSON-RPC server (Python) + client (Rust)
5. Build GoalInput component with file picker
6. Build ActivityFeed component
7. Build ResultView component (markdown renderer)
8. Implement LLM client (Anthropic)
9. Implement tool registry + 3 basic tools
10. Implement basic agent orchestrator (plan → execute → report)
11. Wire everything: UI → Rust → Python → LLM → back
12. First working demo: summarize a file
```

### Exit Criteria
- User can type "Summarize ~/Documents/notes.md" and get a summary displayed in the app.
- Activity feed shows each step the agent takes.
- Config file persists API key across restarts.

---

## Phase 2: File Intelligence

**Goal:** Handle all common document types and perform file organization tasks.

### Deliverables
- [ ] Document parsers: PDF, DOCX, XLSX, CSV, images (OCR)
- [ ] File system tools: move, copy, rename, delete, create_directory
- [ ] Permission system (auto/notify/confirm/block)
- [ ] Confirmation dialog for destructive operations
- [ ] Audit logging to `~/.cowork/audit.log`
- [ ] File metadata extraction (size, type, dates)
- [ ] Undo support (shadow copies before destructive ops)
- [ ] Working use case: "Organize my Downloads folder"

### Tech Tasks
```
1. Add pypdf2 / pdfplumber for PDF parsing
2. Add python-docx for DOCX parsing
3. Add openpyxl for XLSX parsing
4. Add pandas for CSV parsing
5. Add tesseract/surya for OCR
6. Implement move_file, copy_file, delete_file tools
7. Implement PermissionGuard with tier system
8. Build ConfirmDialog component (frontend)
9. Implement audit log writer
10. Implement undo system (shadow copy manager)
11. Implement file organization agent workflow
12. End-to-end test: organize a test folder
```

### Exit Criteria
- User can drop a messy folder → Cowork organizes it into subfolders.
- Destructive operations show confirmation dialog.
- All operations logged in audit.log.
- Undo works for the last task's changes.

---

## Phase 3: Multi-Step Agent & Deliverables

**Goal:** Robust agentic loop with re-planning, and ability to produce formatted output documents.

### Deliverables
- [ ] Full agent loop: plan → execute → evaluate → re-plan → verify → deliver
- [ ] Re-planning on failures or unexpected results
- [ ] Document generators: DOCX, XLSX, CSV, PDF output
- [ ] Multi-file input processing (batch)
- [ ] Task templates (pre-built task patterns)
- [ ] Task history (SQLite storage)
- [ ] Working use case: "Create a report from these 5 files"

### Tech Tasks
```
1. Enhance orchestrator with evaluation + re-planning
2. Add max iteration guards (50 steps, 3 re-plans)
3. Implement generate_docx tool (python-docx)
4. Implement generate_xlsx tool (openpyxl)
5. Implement generate_csv tool
6. Implement generate_pdf tool (reportlab or weasyprint)
7. Build DeliverableView with file preview + download
8. Implement SQLite schema for task history
9. Build TaskList sidebar component
10. Implement task template system
11. End-to-end test: multi-source report generation
```

### Exit Criteria
- User gives 5 source files → gets a formatted DOCX report.
- Agent recovers from tool failures by re-planning.
- Past tasks visible in sidebar, clickable to view results.

---

## Phase 4: Knowledge Base & Search

**Goal:** Index local folders into a vector store; answer questions grounded in user's documents.

### Deliverables
- [ ] ChromaDB integration (embedded, local)
- [ ] Folder indexing pipeline (chunk → embed → store)
- [ ] Semantic search tool
- [ ] Keyword search tool (ripgrep or Python fallback)
- [ ] RAG query flow: search → retrieve → augment prompt → answer
- [ ] Index management UI (add/remove folders, reindex)
- [ ] Working use case: "What do my contracts say about liability?"

### Tech Tasks
```
1. Add ChromaDB as embedded dependency
2. Implement document chunking (by paragraph, with overlap)
3. Implement embedding (sentence-transformers local or API)
4. Implement index_directory tool
5. Implement semantic_search tool
6. Implement keyword_search tool (grep-like)
7. Build RAG augmentation in agent planner
8. Build IndexManager UI component
9. End-to-end test: index folder, ask question, get grounded answer
```

### Exit Criteria
- User indexes ~/Documents/contracts/ → asks "renewal dates" → gets tabulated answer.
- Search results include source file attribution.
- Index survives app restart (persistent ChromaDB).

---

## Phase 5: Polish, Safety & Distribution

**Goal:** Production-ready application with proper safety, UX polish, and installable builds.

### Deliverables
- [ ] OS keyring integration for API key storage
- [ ] Scoped folder access (settings UI)
- [ ] Dry-run mode
- [ ] Onboarding flow (first-run setup wizard)
- [ ] Keyboard shortcuts & accessibility
- [ ] Error recovery & user-friendly error messages
- [ ] App auto-updater
- [ ] Build pipeline: Windows .msi, macOS .dmg, Linux .deb/.AppImage
- [ ] README, user guide, contributing docs

### Tech Tasks
```
1. Integrate OS keyring (keytar / keyring crate)
2. Build folder access manager in Settings
3. Implement dry-run mode (agent plans but doesn't execute)
4. Build onboarding wizard (first launch)
5. Add keyboard shortcuts (Cmd/Ctrl+N for new task, etc.)
6. Add error boundary + user-friendly error display
7. Configure Tauri updater plugin
8. Setup CI/CD (GitHub Actions) for multi-platform builds
9. Write user-facing documentation
10. Release v0.1.0
```

### Exit Criteria
- User can download installer, run first-time setup, complete a task — zero terminal interaction.
- API keys stored securely in OS keyring.
- Builds pass CI for all 3 platforms.

---

## Dependency Graph

```
Phase 1 (Skeleton)
    │
    ├──▶ Phase 2 (File Intelligence)
    │        │
    │        └──▶ Phase 3 (Multi-Step Agent)
    │                 │
    │                 ├──▶ Phase 4 (Knowledge Base)
    │                 │
    │                 └──▶ Phase 5 (Polish & Ship)
    │                          │
    │                          └──▶ v0.1.0 Release
```

Phase 2-3 are blocking. Phase 4 and 5 can partially overlap.

---

## Dev Environment Requirements

| Tool | Version | Purpose |
|---|---|---|
| Node.js | 20+ | Frontend build |
| Rust | 1.75+ | Tauri backend |
| Python | 3.11+ | Agent sidecar |
| uv | latest | Python package management |
| pnpm | 9+ | JS package management |
| Tauri CLI | 2.x | Desktop app framework |
