"""SQLite database manager for tasks, steps, deliverables, and audit logs."""

from __future__ import annotations

import aiosqlite

from cowork.storage.config import COWORK_DIR

DB_PATH = COWORK_DIR / "cowork.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    goal            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'planning',
    attached_files  TEXT,
    result_summary  TEXT,
    deliverable_dir TEXT,
    total_steps     INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    tokens_used     INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at    TEXT,
    duration_ms     INTEGER
);

CREATE TABLE IF NOT EXISTS steps (
    id           TEXT PRIMARY KEY,
    task_id      TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_number  INTEGER NOT NULL,
    tool_name    TEXT NOT NULL,
    tool_args    TEXT NOT NULL,
    description  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    result       TEXT,
    error        TEXT,
    started_at   TEXT,
    completed_at TEXT,
    duration_ms  INTEGER
);

CREATE TABLE IF NOT EXISTS deliverables (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,
    file_type   TEXT NOT NULL,
    file_size   INTEGER,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT REFERENCES tasks(id),
    operation   TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    destination TEXT,
    status      TEXT NOT NULL,
    details     TEXT,
    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS indexed_folders (
    id              TEXT PRIMARY KEY,
    folder_path     TEXT NOT NULL UNIQUE,
    collection_name TEXT NOT NULL,
    doc_count       INTEGER DEFAULT 0,
    chunk_count     INTEGER DEFAULT 0,
    last_indexed_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS undo_records (
    id            TEXT PRIMARY KEY,
    task_id       TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    operation     TEXT NOT NULL,
    original_path TEXT NOT NULL,
    backup_path   TEXT NOT NULL,
    new_path      TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_steps_task ON steps(task_id, step_number);
CREATE INDEX IF NOT EXISTS idx_deliverables_task ON deliverables(task_id);
CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_undo_task ON undo_records(task_id);
"""


async def get_db() -> aiosqlite.Connection:
    """Open a connection to the SQLite database, creating tables if needed."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(SCHEMA)
    return db


async def insert_task(db: aiosqlite.Connection, task_id: str, goal: str, attached_files: str) -> None:
    await db.execute(
        "INSERT INTO tasks (id, goal, attached_files) VALUES (?, ?, ?)",
        (task_id, goal, attached_files),
    )
    await db.commit()


async def update_task_status(db: aiosqlite.Connection, task_id: str, status: str, **kwargs) -> None:
    sets = ["status = ?"]
    values = [status]
    for key, value in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(value)
    values.append(task_id)
    await db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", values)
    await db.commit()


async def insert_step(
    db: aiosqlite.Connection,
    step_id: str,
    task_id: str,
    step_number: int,
    tool_name: str,
    tool_args: str,
    description: str,
) -> None:
    await db.execute(
        "INSERT INTO steps (id, task_id, step_number, tool_name, tool_args, description) VALUES (?, ?, ?, ?, ?, ?)",
        (step_id, task_id, step_number, tool_name, tool_args, description),
    )
    await db.commit()


async def update_step_status(db: aiosqlite.Connection, step_id: str, status: str, **kwargs) -> None:
    sets = ["status = ?"]
    values = [status]
    for key, value in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(value)
    values.append(step_id)
    await db.execute(f"UPDATE steps SET {', '.join(sets)} WHERE id = ?", values)
    await db.commit()


async def log_audit(
    db: aiosqlite.Connection,
    task_id: str | None,
    operation: str,
    file_path: str,
    status: str,
    destination: str | None = None,
    details: str | None = None,
) -> None:
    await db.execute(
        "INSERT INTO audit_log (task_id, operation, file_path, status, destination, details) VALUES (?, ?, ?, ?, ?, ?)",
        (task_id, operation, file_path, status, destination, details),
    )
    await db.commit()


async def get_task_history(db: aiosqlite.Connection, limit: int = 50) -> list[dict]:
    cursor = await db.execute(
        "SELECT id, goal, status, created_at, completed_at, total_steps, completed_steps FROM tasks ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
