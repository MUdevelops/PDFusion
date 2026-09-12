"""Rotate PDF — rotate by 90/180/270 degrees, scoped to a single page,
an explicit set of pages, or the whole document.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pypdf import PdfWriter

from app.core.pdf_engine import open_reader
from app.utils.errors import FileValidationError
from app.utils.file_utils import atomic_write
from app.utils.logger import get_logger
from app.utils.validators import validate_pdf_header

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]

VALID_ANGLES = {90, 180, 270}


def rotate_pdf(
    source: Path,
    degrees: int,
    output_path: Path,
    page_indices: list[int] | None = None,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Rotate pages of ``source`` and write the result to ``output_path``.

    ``page_indices`` is 0-based; ``None`` means every page.
    """
    if degrees not in VALID_ANGLES:
        raise FileValidationError("Rotation must be 90, 180, or 270 degrees.")

    validate_pdf_header(source)
    reader = open_reader(source)
    page_count = len(reader.pages)
    target = set(page_indices) if page_indices is not None else set(range(page_count))
    for i in target:
        if not (0 <= i < page_count):
            raise FileValidationError(f"Page {i + 1} is out of bounds for a {page_count}-page document.")

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        new_page = writer.add_page(page)
        if i in target:
            new_page.rotate(degrees)
        if progress_cb:
            progress_cb(int((i + 1) / max(page_count, 1) * 90), f"Processing page {i + 1} of {page_count}…")

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "wb") as fh:
            writer.write(fh)

    if progress_cb:
        progress_cb(95, "Writing file…")
    atomic_write(output_path, _write)
    if progress_cb:
        progress_cb(100, "Done")
    logger.info("Rotated %d page(s) by %d\u00b0 -> %s", len(target), degrees, output_path)
    return output_path
