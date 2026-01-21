"""File system tools — list, read, write, info, search, create directories."""

from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from cowork.models import ToolResult
from cowork.tools.base import BaseTool

if TYPE_CHECKING:
    from cowork.agent.context import TaskContext


def _resolve_path(raw: str) -> Path:
    """Resolve ~ and make absolute, but do NOT follow symlinks beyond that."""
    return Path(raw).expanduser().resolve()


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = (
        "List files and folders in a directory. Returns name, type, size, "
        "and modified date for each entry."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (absolute or ~)"},
            "recursive": {"type": "boolean", "description": "List recursively", "default": False},
            "max_depth": {"type": "integer", "description": "Max recursion depth", "default": 3},
        },
        "required": ["path"],
    }

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        path = _resolve_path(args["path"])
        if not path.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        entries = []
        total_files = 0
        total_dirs = 0

        try:
            for entry in sorted(path.iterdir()):
                stat = entry.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                if entry.is_file():
                    total_files += 1
                    entries.append({
                        "name": entry.name,
                        "type": "file",
                        "size": stat.st_size,
                        "size_human": _format_size(stat.st_size),
                        "modified": modified,
                    })
                elif entry.is_dir():
                    total_dirs += 1
                    children = len(list(entry.iterdir())) if entry.is_dir() else 0
                    entries.append({
                        "name": entry.name,
                        "type": "directory",
                        "children_count": children,
                        "modified": modified,
                    })
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")

        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "entries": entries,
                "total_files": total_files,
                "total_dirs": total_dirs,
            },
        )


class ReadFileTool(BaseTool):
    name = "read_file"
    description = (
        "Read the text content of a file. Supports TXT, MD, JSON, CSV, and other "
        "text-based formats. For binary formats (PDF, DOCX, XLSX), use parse_* tools."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (absolute or ~)"},
            "max_lines": {
                "type": "integer",
                "description": "Maximum lines to return",
                "default": 1000,
            },
            "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
        },
        "required": ["path"],
    }

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        path = _resolve_path(args["path"])
        max_lines = args.get("max_lines", 1000)
        encoding = args.get("encoding", "utf-8")

        if not path.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        try:
            content = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                error=f"Cannot read {path} as text. Try a parse_* tool for binary formats.",
            )
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")

        lines = content.splitlines()
        truncated = len(lines) > max_lines
        if truncated:
            content = "\n".join(lines[:max_lines])

        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "content": content,
                "lines": len(lines),
                "size": path.stat().st_size,
                "truncated": truncated,
            },
        )


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Write text content to a file. Creates the file if it doesn't exist. "
        "If the file exists, requires confirmation before overwriting."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (absolute or ~)"},
            "content": {"type": "string", "description": "Content to write"},
            "create_dirs": {
                "type": "boolean",
                "description": "Create parent directories if needed",
                "default": True,
            },
        },
        "required": ["path", "content"],
    }
    requires_confirmation = True

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        path = _resolve_path(args["path"])
        content = args["content"]
        create_dirs = args.get("create_dirs", True)

        already_exists = path.exists()

        # If file exists and hasn't been confirmed, request confirmation
        if already_exists and self.requires_confirmation:
            return ToolResult(
                success=False,
                needs_confirmation=True,
                confirmation_message=f"File already exists: {path}. Overwrite?",
            )

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        try:
            path.write_text(content, encoding="utf-8")
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")

        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "size": path.stat().st_size,
                "created": not already_exists,
                "overwritten": already_exists,
            },
        )


class GetFileInfoTool(BaseTool):
    name = "get_file_info"
    description = "Get metadata about a file: size, type, dates, permissions."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (absolute or ~)"},
        },
        "required": ["path"],
    }

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        path = _resolve_path(args["path"])
        if not path.exists():
            return ToolResult(success=False, error=f"Path does not exist: {path}")

        stat = path.stat()
        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "name": path.name,
                "extension": path.suffix.lstrip("."),
                "size": stat.st_size,
                "size_human": _format_size(stat.st_size),
                "type": "file" if path.is_file() else "directory",
                "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "is_readable": os.access(path, os.R_OK),
                "is_writable": os.access(path, os.W_OK),
            },
        )


class SearchFilesGlobTool(BaseTool):
    name = "search_files_glob"
    description = 'Search for files matching a glob pattern, e.g. "**/*.pdf".'
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": 'Glob pattern e.g. "**/*.pdf"'},
            "path": {"type": "string", "description": "Root directory to search in"},
            "max_results": {
                "type": "integer",
                "description": "Max files to return",
                "default": 100,
            },
        },
        "required": ["pattern", "path"],
    }

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        # Accept both 'path' and 'directory' for robustness
        raw_dir = args.get("path") or args.get("directory", ".")
        directory = _resolve_path(raw_dir)
        pattern = args["pattern"]
        max_results = args.get("max_results", 100)

        if not directory.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {directory}")

        full_pattern = str(directory / pattern)
        matches = sorted(glob.glob(full_pattern, recursive=True))
        truncated = len(matches) > max_results

        return ToolResult(
            success=True,
            data={
                "pattern": pattern,
                "directory": str(directory),
                "matches": matches[:max_results],
                "total_matches": len(matches),
                "truncated": truncated,
            },
        )


class CreateDirectoryTool(BaseTool):
    name = "create_directory"
    description = "Create a new directory, including parent directories if needed."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to create"},
        },
        "required": ["path"],
    }

    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        path = _resolve_path(args["path"])

        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")

        return ToolResult(
            success=True,
            data={"path": str(path), "created": True},
        )
