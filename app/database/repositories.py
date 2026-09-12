"""Repository layer: the only place that writes raw SQL.

UI and core code should never import sqlite3 directly — go through these
repositories so the schema can evolve independently of callers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.database.database import Database, get_database
from app.database.models import HistoryEntry, RecentFile


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RecentFilesRepository:
    def __init__(self, db: Database | None = None):
        self.db = db or get_database()

    def touch(
        self,
        file_path: Path,
        page_count: int | None = None,
        last_operation: str | None = None,
    ) -> None:
        """Insert or update a recent-file entry (upsert on file_path)."""
        p = Path(file_path)
        size = p.stat().st_size if p.exists() else 0
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO recent_files (file_path, file_name, file_size, page_count,
                                           last_operation, last_opened_at, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_size=excluded.file_size,
                    page_count=COALESCE(excluded.page_count, recent_files.page_count),
                    last_operation=COALESCE(excluded.last_operation, recent_files.last_operation),
                    last_opened_at=excluded.last_opened_at
                """,
                (str(p), p.name, size, page_count, last_operation, _now_iso()),
            )

    def list_recent(self, limit: int = 25) -> list[RecentFile]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recent_files ORDER BY last_opened_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            RecentFile(
                id=r["id"], file_path=r["file_path"], file_name=r["file_name"],
                file_size=r["file_size"], page_count=r["page_count"],
                last_operation=r["last_operation"], last_opened_at=r["last_opened_at"],
                is_favorite=bool(r["is_favorite"]),
            )
            for r in rows
        ]

    def set_favorite(self, file_path: str, favorite: bool) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE recent_files SET is_favorite=? WHERE file_path=?",
                (1 if favorite else 0, file_path),
            )

    def remove(self, file_path: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM recent_files WHERE file_path=?", (file_path,))

    def clear(self) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM recent_files")


class HistoryRepository:
    def __init__(self, db: Database | None = None):
        self.db = db or get_database()

    def start(self, tool_id: str, tool_label: str, input_summary: str) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                """INSERT INTO history (tool_id, tool_label, input_summary, output_path,
                                         status, detail, started_at)
                   VALUES (?, ?, ?, NULL, 'running', '', ?)""",
                (tool_id, tool_label, input_summary, _now_iso()),
            )
            return cur.lastrowid

    def finish(
        self,
        entry_id: int,
        status: str,
        output_path: str | None,
        detail: str,
        duration_ms: int,
    ) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """UPDATE history SET status=?, output_path=?, detail=?,
                       finished_at=?, duration_ms=? WHERE id=?""",
                (status, output_path, detail, _now_iso(), duration_ms, entry_id),
            )

    def list_recent(self, limit: int = 50) -> list[HistoryEntry]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def clear(self) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM history")


class FavoritesRepository:
    def __init__(self, db: Database | None = None):
        self.db = db or get_database()

    def list_favorites(self) -> list[str]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT tool_id FROM favorites").fetchall()
        return [r["tool_id"] for r in rows]

    def toggle(self, tool_id: str) -> bool:
        """Returns the new favorite state."""
        with self.db.connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM favorites WHERE tool_id=?", (tool_id,)
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM favorites WHERE tool_id=?", (tool_id,))
                return False
            conn.execute("INSERT INTO favorites (tool_id) VALUES (?)", (tool_id,))
            return True


class SettingsRepository:
    def __init__(self, db: Database | None = None):
        self.db = db or get_database()

    def get(self, key: str, default: str | None = None) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def all(self) -> dict[str, str]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
