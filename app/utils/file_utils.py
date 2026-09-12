"""Filesystem helpers implementing the safety rules in the spec:

- never silently overwrite originals
- atomic saves via temp-file + rename
- disk space / permission / lock checks before writing
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

from app.constants import temp_dir
from app.utils.errors import InsufficientDiskSpaceError, PDFusionError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def unique_output_path(desired: Path) -> Path:
    """Never overwrite an existing file: append ' (1)', ' (2)', ... instead."""
    if not desired.exists():
        return desired
    stem, suffix, parent = desired.stem, desired.suffix, desired.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def check_disk_space(target_dir: Path, required_bytes: int, safety_margin: float = 1.2) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    needed = int(required_bytes * safety_margin)
    if usage.free < needed:
        raise InsufficientDiskSpaceError(
            f"Not enough free disk space. Need ~{needed / 1_048_576:.1f} MB, "
            f"only {usage.free / 1_048_576:.1f} MB available."
        )


def is_file_locked(path: Path) -> bool:
    """Best-effort check for a file locked by another process (Windows-safe)."""
    if not path.exists():
        return False
    try:
        with open(path, "a+b"):
            pass
        return False
    except OSError:
        return True


def new_temp_path(suffix: str = ".tmp") -> Path:
    fd, name = tempfile.mkstemp(suffix=suffix, dir=str(temp_dir()))
    os.close(fd)
    return Path(name)


def atomic_write(final_path: Path, writer_fn) -> Path:
    """Write to a temp file in the same directory, then atomically replace.

    ``writer_fn`` receives a Path to write to and must produce the final
    bytes there. Guarantees the destination is never left half-written.
    """
    ensure_parent_dir(final_path)
    check_disk_space(final_path.parent, required_bytes=1_048_576)  # baseline check

    if is_file_locked(final_path):
        raise PDFusionError(
            f"'{final_path.name}' appears to be open in another program. "
            "Close it and try again."
        )

    tmp_path = final_path.with_name(f".{final_path.stem}.{int(time.time()*1000)}.tmp{final_path.suffix}")
    try:
        writer_fn(tmp_path)
        os.replace(tmp_path, final_path)
        logger.info("Atomically wrote %s", final_path)
        return final_path
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def clean_temp_files(older_than_seconds: int = 24 * 3600) -> int:
    """Remove stale temp files. Returns count removed."""
    removed = 0
    now = time.time()
    for p in temp_dir().glob("*"):
        try:
            if p.is_file() and (now - p.stat().st_mtime) > older_than_seconds:
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"
