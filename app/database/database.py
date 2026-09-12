"""SQLite connection + schema management for local app data.

No external server, ever — this file is local-first by construction.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.constants import database_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS recent_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    page_count INTEGER,
    last_operation TEXT,
    last_opened_at TEXT NOT NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL,
    tool_label TEXT NOT NULL,
    input_summary TEXT,
    output_path TEXT,
    status TEXT NOT NULL,        -- 'success' | 'failed' | 'cancelled'
    detail TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS favorites (
    tool_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_recent_files_opened_at
    ON recent_files(last_opened_at DESC);

CREATE INDEX IF NOT EXISTS idx_history_started_at
    ON history(started_at DESC);
"""


class Database:
    """Thin wrapper around a single SQLite file with WAL enabled."""

    def __init__(self, path: Path | None = None):
        self.path = path or database_path()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(SCHEMA)
        logger.info("Database ready at %s", self.path)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


_instance: Database | None = None


def get_database() -> Database:
    global _instance
    if _instance is None:
        _instance = Database()
    return _instance
