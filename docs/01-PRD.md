# Product Requirements Document — Cowork

## 1. Overview

**Product name:** Cowork
**Tagline:** A local-first AI desktop agent that autonomously handles knowledge work on your computer.
**Version:** 0.1.0 (MVP)
**Date:** 2026-03-24

### 1.1 Problem Statement

Non-technical knowledge workers (managers, analysts, marketers, ops teams) spend hours on repetitive, high-effort tasks: organizing files, synthesizing reports from multiple sources, extracting data from unstructured documents, and preparing deliverables. Chat-based AI tools require users to break work into individual prompts and manually coordinate each step.

### 1.2 Solution

Cowork is a **desktop application** that runs locally on the user's machine. The user gives it a goal ("Organize my Downloads folder", "Create a report from these files"), and Cowork autonomously plans, executes, and delivers the result — reading local files, processing documents, and producing finished deliverables.

### 1.3 Target Users

| Persona | Need |
|---|---|
| **Manager / Team Lead** | Weekly reports, meeting summaries, status updates |
| **Analyst** | Data extraction from PDFs, contract review, research synthesis |
| **Marketing / Ops** | File organization, document drafting, content assembly |
| **Any knowledge worker** | Automating repetitive file-based tasks |

---

## 2. Core Use Cases

### UC-1: Organize & Manage Local Files
**Goal:** Point Cowork at a folder → it renames, sorts, deduplicates, and organizes files.
**Input:** A folder path (e.g., ~/Downloads)
**Output:** Files moved into categorized subfolders with clean names.
**Acceptance criteria:**
- Supports grouping by file type, date, or AI-inferred topic
- Detects and flags duplicate files (exact + near-duplicate)
- Confirms destructive operations (move/delete) before executing
- Produces a summary report of changes made

### UC-2: Prepare Documents from Source Files
**Goal:** Given source files, produce a structured report/document.
**Input:** Multiple files (PDF, DOCX, XLSX, MD, TXT, CSV)
**Output:** A formatted DOCX or MD deliverable.
**Acceptance criteria:**
- Reads and parses all common file formats
- Synthesizes content across sources into a structured document
- Produces a downloadable/openable deliverable
- Includes proper sections, headings, and formatting

### UC-3: Synthesize Research
**Goal:** Read multiple sources and produce a structured summary.
**Input:** Question + set of source files/folders
**Output:** Research synthesis document with key findings.
**Acceptance criteria:**
- Extracts relevant information from each source
- Clusters findings into themes
- Identifies gaps, conflicts, and consensus
- Includes source attribution

### UC-4: Extract Data from Unstructured Files
**Goal:** Pull structured data from contracts, reports, invoices, etc.
**Input:** Set of unstructured documents + extraction schema/prompt
**Output:** Structured spreadsheet (XLSX/CSV) with extracted data.
**Acceptance criteria:**
- Handles PDF, DOCX, scanned images (OCR)
- Extracts entities: names, dates, amounts, terms
- Outputs clean tabular data
- Flags low-confidence extractions for review

---

## 3. Functional Requirements

### 3.1 Desktop Application
- **FR-01:** Runs as a native desktop app (Windows, macOS, Linux)
- **FR-02:** Simple goal-input interface (text box + optional file/folder attachment)
- **FR-03:** Live activity feed showing agent steps in real-time
- **FR-04:** Deliverable preview panel (rendered MD, document preview)
- **FR-05:** Task history — view, re-run, and reference past tasks
- **FR-06:** Settings panel for API keys, model selection, permissions

### 3.2 Agent Engine
- **FR-07:** Autonomous planning — break goals into executable steps
- **FR-08:** Multi-step execution — run steps sequentially with context carry-forward
- **FR-09:** Self-verification — review output quality, re-plan if needed
- **FR-10:** Tool invocation — call registered tools (file ops, parsing, generation)
- **FR-11:** Streaming progress — emit step-level progress to the UI

### 3.3 File & Document Processing
- **FR-12:** Read files: TXT, MD, PDF, DOCX, XLSX, CSV, JSON, images
- **FR-13:** Write files: MD, DOCX, XLSX, CSV, PDF, TXT
- **FR-14:** File operations: list, read, write, move, copy, rename, delete
- **FR-15:** Directory operations: list, create, watch, recursive traversal

### 3.4 Knowledge & Search
- **FR-16:** Index folders into a local vector store for semantic search
- **FR-17:** Query indexed knowledge base with natural language
- **FR-18:** Keyword search across files (grep-like)

### 3.5 Safety & Oversight
- **FR-19:** Permission tiers: auto (read), notify (create), confirm (delete/move/overwrite)
- **FR-20:** Scoped access — user grants per-folder access, not full filesystem
- **FR-21:** Audit log — every file operation logged with timestamp
- **FR-22:** Undo support — shadow copy before destructive operations
- **FR-23:** Dry-run mode — show planned actions without executing

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| **NFR-01** | Startup time | < 3 seconds |
| **NFR-02** | File processing speed | < 2s per average document |
| **NFR-03** | App binary size | < 50 MB (Tauri) |
| **NFR-04** | Offline support | Full offline via Ollama |
| **NFR-05** | Data privacy | Zero data leaves machine unless LLM API call |
| **NFR-06** | OS support | Windows 10+, macOS 12+, Ubuntu 22+ |
| **NFR-07** | Concurrent tasks | 1 active task (v1), queue for multiple |

---

## 5. Out of Scope (v1)

- Cloud sync / multi-device
- Team collaboration / shared workspaces
- Browser extension
- Mobile app
- Scheduled/recurring tasks (v2)
- App automation beyond file system (e.g., controlling Excel, browser)
- Voice input

---

## 6. Success Metrics

| Metric | Target |
|---|---|
| Task completion rate | > 80% of tasks produce a usable deliverable |
| User intervention rate | < 2 confirmations per average task |
| Time savings | 3-10x faster than manual for supported use cases |
| Error rate | < 5% of file operations require undo |
