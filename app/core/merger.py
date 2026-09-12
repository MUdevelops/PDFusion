"""Merge PDF — combine multiple PDFs into one, in a user-chosen order,
with optional per-page rotation applied before merging.

Pure pypdf: reading is non-destructive (the source files are opened
read-only and never modified), and every page added to the output
writer is an independent clone, so rotating one copy never affects
another copy of the same source page (verified: pypdf's
``PdfWriter.add_page`` returns a clone, not the original object).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pypdf import PdfWriter

from app.core.pdf_engine import open_reader
from app.utils.file_utils import atomic_write
from app.utils.logger import get_logger
from app.utils.validators import validate_pdf_header

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


@dataclass
class MergeItem:
    """One input file in the merge list, in the order it will appear."""

    path: Path
    # page_index (0-based, within this file) -> additional clockwise
    # rotation in degrees (0/90/180/270) to apply before merging.
    page_rotations: dict[int, int] = field(default_factory=dict)


def merge_pdfs(
    items: list[MergeItem],
    output_path: Path,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Merge ``items`` in order into a single PDF at ``output_path``.

    Never touches the source files. Writes atomically so a failure or
    cancellation never leaves a half-written output behind.
    """
    if not items:
        from app.utils.errors import FileValidationError

        raise FileValidationError("Add at least one PDF to merge.")

    for item in items:
        validate_pdf_header(item.path)

    readers = [(item, open_reader(item.path)) for item in items]
    total_pages = sum(len(reader.pages) for _, reader in readers)
    total_pages = max(total_pages, 1)

    writer = PdfWriter()
    processed = 0
    for item, reader in readers:
        for page_index, page in enumerate(reader.pages):
            new_page = writer.add_page(page)
            rotation = item.page_rotations.get(page_index, 0)
            if rotation:
                new_page.rotate(rotation)
            processed += 1
            if progress_cb:
                pct = int(processed / total_pages * 100)
                progress_cb(pct, f"Adding {item.path.name} — page {page_index + 1}")

    if progress_cb:
        progress_cb(95, "Writing merged file…")

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "wb") as fh:
            writer.write(fh)

    atomic_write(output_path, _write)
    if progress_cb:
        progress_cb(100, "Done")
    logger.info("Merged %d file(s) -> %s", len(items), output_path)
    return output_path
