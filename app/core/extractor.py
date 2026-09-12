"""Extract Pages — pull an explicit subset of pages (by 0-based index)
out of a PDF into a brand-new file. The source is opened read-only and
is never modified.
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


def extract_pages(
    source: Path,
    page_indices: list[int],
    output_path: Path,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    if not page_indices:
        raise FileValidationError("Select at least one page to extract.")

    validate_pdf_header(source)
    reader = open_reader(source)
    page_count = len(reader.pages)
    for i in page_indices:
        if not (0 <= i < page_count):
            raise FileValidationError(f"Page {i + 1} is out of bounds for a {page_count}-page document.")

    writer = PdfWriter()
    total = len(page_indices)
    for n, i in enumerate(page_indices, start=1):
        writer.add_page(reader.pages[i])
        if progress_cb:
            progress_cb(int(n / total * 90), f"Extracting page {i + 1} ({n} of {total})…")

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "wb") as fh:
            writer.write(fh)

    if progress_cb:
        progress_cb(95, "Writing file…")
    atomic_write(output_path, _write)
    if progress_cb:
        progress_cb(100, "Done")
    logger.info("Extracted %d page(s) -> %s", total, output_path)
    return output_path
