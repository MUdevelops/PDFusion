"""Plain dataclasses mirroring the SQLite rows in database.py."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecentFile:
    id: int | None
    file_path: str
    file_name: str
    file_size: int
    page_count: int | None
    last_operation: str | None
    last_opened_at: str
    is_favorite: bool = False


@dataclass
class HistoryEntry:
    id: int | None
    tool_id: str
    tool_label: str
    input_summary: str
    output_path: str | None
    status: str  # success | failed | cancelled
    detail: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
