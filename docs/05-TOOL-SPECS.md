# Agent Tool Interface Specification — Cowork

## 1. Tool Interface Contract

Every tool in Cowork follows this interface:

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ToolParam(BaseModel):
    """Describes a single parameter for tool selection by the LLM."""
    name: str
    type: str                    # string | integer | number | boolean | array | object
    description: str
    required: bool = True
    default: any = None


class ToolResult(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None
    needs_confirmation: bool = False
    confirmation_message: str | None = None


class BaseTool(ABC):
    name: str                          # Unique identifier (snake_case)
    description: str                   # Shown to LLM for tool selection
    parameters: list[ToolParam]        # Input schema
    requires_confirmation: bool        # True for destructive operations

    @abstractmethod
    async def execute(self, args: dict, context: "TaskContext") -> ToolResult:
        """Execute the tool with validated arguments."""
        ...

    def to_llm_schema(self) -> dict:
        """Convert to LLM-compatible tool/function schema."""
        ...
```

---

## 2. Tool Registry

```python
class ToolRegistry:
    """Central registry of all available tools."""

    def register(self, tool: BaseTool) -> None: ...
    def get(self, name: str) -> BaseTool: ...
    def list_all(self) -> list[BaseTool]: ...
    def to_llm_schemas(self) -> list[dict]: ...
```

Tools are registered at sidecar startup. The registry is passed to the planner so the LLM knows what tools are available.

---

## 3. Phase 1 Tools (MVP)

### 3.1 list_directory

```
Name:        list_directory
Description: List files and folders in a directory. Returns name, type, size, and
             modified date for each entry.
Confirmation: No

Parameters:
  - path (string, required): Absolute or ~ path to directory
  - recursive (boolean, optional, default: false): List recursively
  - max_depth (integer, optional, default: 3): Max recursion depth

Returns:
  {
    "path": "/home/user/Documents",
    "entries": [
      {"name": "report.pdf", "type": "file", "size": 204800, "modified": "2026-03-20T10:00:00Z"},
      {"name": "drafts", "type": "directory", "children_count": 5, "modified": "2026-03-19T14:00:00Z"}
    ],
    "total_files": 12,
    "total_dirs": 3
  }
```

### 3.2 read_file

```
Name:        read_file
Description: Read the text content of a file. Supports TXT, MD, JSON, CSV, and
             other text-based formats. For binary formats (PDF, DOCX, XLSX), use
             the corresponding parse_* tool instead.
Confirmation: No

Parameters:
  - path (string, required): Absolute or ~ path to file
  - max_lines (integer, optional, default: 1000): Maximum lines to return
  - encoding (string, optional, default: "utf-8"): File encoding

Returns:
  {
    "path": "/home/user/notes.md",
    "content": "# Meeting Notes\n...",
    "lines": 45,
    "size": 2048,
    "truncated": false
  }
```

### 3.3 write_file

```
Name:        write_file
Description: Write text content to a file. Creates the file if it doesn't exist.
             If the file exists, requires confirmation before overwriting.
Confirmation: Yes (if overwriting existing file)

Parameters:
  - path (string, required): Absolute or ~ path to file
  - content (string, required): Content to write
  - create_dirs (boolean, optional, default: true): Create parent directories if needed

Returns:
  {
    "path": "/home/user/Documents/summary.md",
    "size": 1024,
    "created": true,           // true if new file, false if overwrite
    "overwritten": false
  }
```

---

## 4. Phase 2 Tools (File Intelligence)

### 4.1 parse_pdf

```
Name:        parse_pdf
Description: Extract text content from a PDF file. Returns the full text and
             page-by-page breakdown.
Confirmation: No

Parameters:
  - path (string, required): Path to PDF file
  - pages (string, optional): Page range e.g. "1-5" or "1,3,7". Default: all.

Returns:
  {
    "path": "...",
    "total_pages": 12,
    "text": "Full extracted text...",
    "pages": [
      {"page": 1, "text": "..."},
      {"page": 2, "text": "..."}
    ]
  }
```

### 4.2 parse_docx

```
Name:        parse_docx
Description: Extract text content from a Microsoft Word document.
Confirmation: No

Parameters:
  - path (string, required): Path to .docx file

Returns:
  {
    "path": "...",
    "text": "Full extracted text...",
    "paragraphs": 45,
    "tables": [{"rows": 5, "cols": 3, "data": [[...]]}]
  }
```

### 4.3 parse_xlsx

```
Name:        parse_xlsx
Description: Extract data from an Excel spreadsheet. Returns sheet names and
             data as arrays.
Confirmation: No

Parameters:
  - path (string, required): Path to .xlsx file
  - sheet (string, optional): Sheet name. Default: first sheet.
  - max_rows (integer, optional, default: 10000): Max rows to read

Returns:
  {
    "path": "...",
    "sheets": ["Sheet1", "Revenue", "Costs"],
    "active_sheet": "Sheet1",
    "headers": ["Name", "Amount", "Date"],
    "rows": [["Acme", 5000, "2026-01-15"], ...],
    "total_rows": 150
  }
```

### 4.4 parse_csv

```
Name:        parse_csv
Description: Read and parse a CSV or TSV file.
Confirmation: No

Parameters:
  - path (string, required): Path to CSV file
  - delimiter (string, optional, default: ","): Field delimiter
  - max_rows (integer, optional, default: 10000): Max rows to read

Returns: Same structure as parse_xlsx
```

### 4.5 parse_image_ocr

```
Name:        parse_image_ocr
Description: Extract text from an image using OCR. Supports PNG, JPG, TIFF.
Confirmation: No

Parameters:
  - path (string, required): Path to image file

Returns:
  {
    "path": "...",
    "text": "Extracted text...",
    "confidence": 0.92
  }
```

### 4.6 move_file

```
Name:        move_file
Description: Move or rename a file or directory.
Confirmation: Yes

Parameters:
  - source (string, required): Current path
  - destination (string, required): New path

Returns:
  {
    "source": "...",
    "destination": "...",
    "type": "file"
  }
```

### 4.7 copy_file

```
Name:        copy_file
Description: Copy a file or directory.
Confirmation: No (non-destructive)

Parameters:
  - source (string, required): Source path
  - destination (string, required): Destination path

Returns: Same as move_file
```

### 4.8 delete_file

```
Name:        delete_file
Description: Delete a file. This is destructive and always requires confirmation.
Confirmation: Yes (always)

Parameters:
  - path (string, required): Path to file to delete

Returns:
  {
    "path": "...",
    "backup_path": "~/.cowork/undo/..."  // Shadow copy location
  }
```

### 4.9 create_directory

```
Name:        create_directory
Description: Create a new directory, including parent directories.
Confirmation: No

Parameters:
  - path (string, required): Path to create

Returns:
  {
    "path": "...",
    "created": true
  }
```

### 4.10 get_file_info

```
Name:        get_file_info
Description: Get metadata about a file (size, type, dates, permissions).
Confirmation: No

Parameters:
  - path (string, required): Path to file

Returns:
  {
    "path": "...",
    "name": "report.pdf",
    "extension": "pdf",
    "size": 204800,
    "size_human": "200 KB",
    "type": "file",
    "mime_type": "application/pdf",
    "created": "2026-03-20T10:00:00Z",
    "modified": "2026-03-21T14:30:00Z",
    "is_readable": true,
    "is_writable": true
  }
```

### 4.11 search_files_glob

```
Name:        search_files_glob
Description: Search for files matching a glob pattern.
Confirmation: No

Parameters:
  - pattern (string, required): Glob pattern e.g. "**/*.pdf"
  - directory (string, required): Root directory to search in
  - max_results (integer, optional, default: 100): Max files to return

Returns:
  {
    "pattern": "**/*.pdf",
    "directory": "...",
    "matches": ["path1.pdf", "path2.pdf"],
    "total_matches": 15,
    "truncated": false
  }
```

---

## 5. Phase 3 Tools (Document Generation)

### 5.1 generate_docx

```
Name:        generate_docx
Description: Generate a formatted Microsoft Word document.
Confirmation: No (creates new file)

Parameters:
  - path (string, required): Output path (.docx)
  - title (string, required): Document title
  - content (string, required): Markdown-formatted content to convert to DOCX
  - author (string, optional): Author metadata

Returns:
  {
    "path": "...",
    "size": 15360,
    "pages_estimate": 5
  }
```

### 5.2 generate_xlsx

```
Name:        generate_xlsx
Description: Generate an Excel spreadsheet from structured data.
Confirmation: No

Parameters:
  - path (string, required): Output path (.xlsx)
  - sheets (array, required): Array of {name, headers, rows}

Returns:
  {
    "path": "...",
    "size": 8192,
    "sheets": 2,
    "total_rows": 150
  }
```

### 5.3 generate_csv

```
Name:        generate_csv
Description: Generate a CSV file from structured data.
Confirmation: No

Parameters:
  - path (string, required): Output path (.csv)
  - headers (array, required): Column headers
  - rows (array, required): Data rows
  - delimiter (string, optional, default: ","): Delimiter

Returns:
  {
    "path": "...",
    "size": 4096,
    "total_rows": 100
  }
```

### 5.4 generate_markdown

```
Name:        generate_markdown
Description: Write a markdown file with proper formatting.
Confirmation: No

Parameters:
  - path (string, required): Output path (.md)
  - content (string, required): Markdown content

Returns:
  {
    "path": "...",
    "size": 2048
  }
```

---

## 6. Phase 4 Tools (Knowledge Base)

### 6.1 index_directory

```
Name:        index_directory
Description: Index all documents in a directory into the local knowledge base
             for semantic search. Supports PDF, DOCX, TXT, MD, CSV.
Confirmation: No

Parameters:
  - path (string, required): Directory to index
  - collection_name (string, optional): Name for this index collection

Returns:
  {
    "path": "...",
    "collection": "documents_abc",
    "documents_indexed": 25,
    "chunks_created": 340,
    "skipped": 3,
    "skipped_reasons": ["binary file", "too large", "unsupported format"]
  }
```

### 6.2 semantic_search

```
Name:        semantic_search
Description: Search the indexed knowledge base using natural language. Returns
             the most relevant text chunks with source attribution.
Confirmation: No

Parameters:
  - query (string, required): Natural language search query
  - collection (string, optional): Specific collection to search. Default: all.
  - max_results (integer, optional, default: 10): Max results

Returns:
  {
    "query": "...",
    "results": [
      {
        "text": "Relevant chunk text...",
        "source": "/path/to/file.pdf",
        "page": 3,
        "score": 0.92
      }
    ]
  }
```

### 6.3 keyword_search

```
Name:        keyword_search
Description: Search files for exact text matches (like grep).
Confirmation: No

Parameters:
  - query (string, required): Text to search for
  - directory (string, required): Directory to search in
  - case_sensitive (boolean, optional, default: false): Case sensitivity
  - max_results (integer, optional, default: 50): Max results

Returns:
  {
    "query": "...",
    "matches": [
      {
        "file": "/path/to/file.md",
        "line": 42,
        "text": "...matching line content..."
      }
    ],
    "total_matches": 15
  }
```

---

## 7. Utility Tools

### 7.1 open_file_in_app

```
Name:        open_file_in_app
Description: Open a file in its default application (e.g., open a DOCX in Word).
Confirmation: No

Parameters:
  - path (string, required): Path to file to open

Returns:
  {
    "path": "...",
    "opened": true
  }
```

### 7.2 send_notification

```
Name:        send_notification
Description: Send an OS-level notification to the user.
Confirmation: No

Parameters:
  - title (string, required): Notification title
  - body (string, required): Notification body text

Returns:
  {
    "sent": true
  }
```

---

## 8. Tool Selection Prompt

The planner receives this context to choose tools:

```
You have access to these tools. Choose the right tool for each step of your plan.

FILE READING:
- list_directory: See what files exist in a folder
- read_file: Read text files (txt, md, json, csv)
- get_file_info: Get file metadata (size, dates, type)
- search_files_glob: Find files matching a pattern

DOCUMENT PARSING (for non-text formats):
- parse_pdf: Extract text from PDF
- parse_docx: Extract text from Word documents
- parse_xlsx: Extract data from Excel spreadsheets
- parse_csv: Read CSV/TSV files
- parse_image_ocr: Extract text from images via OCR

FILE OPERATIONS:
- write_file: Create or overwrite a text file
- move_file: Move or rename a file [REQUIRES CONFIRMATION]
- copy_file: Copy a file
- delete_file: Delete a file [REQUIRES CONFIRMATION]
- create_directory: Create a new folder

DOCUMENT GENERATION:
- generate_docx: Create a formatted Word document
- generate_xlsx: Create an Excel spreadsheet
- generate_csv: Create a CSV file
- generate_markdown: Create a markdown file

KNOWLEDGE BASE:
- index_directory: Index a folder for semantic search
- semantic_search: Search indexed documents by meaning
- keyword_search: Search files for exact text

UTILITY:
- open_file_in_app: Open a file in its default app
- send_notification: Send an OS notification
```
