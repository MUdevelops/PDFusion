"""Split PDF — six modes, all producing real files in an output folder.

Every mode opens the source once (read-only) and writes brand-new
output files; the source is never modified. Output filenames are run
through ``unique_output_path`` so an existing file in the destination
folder is never silently overwritten.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pypdf import PdfWriter

from app.core.pdf_engine import open_reader
from app.utils.errors import FileValidationError
from app.utils.file_utils import atomic_write, unique_output_path
from app.utils.logger import get_logger
from app.utils.validators import validate_pdf_header

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


def _write_pages(reader, indices: list[int], output_path: Path) -> Path:
    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "wb") as fh:
            writer.write(fh)

    final_path = unique_output_path(output_path)
    atomic_write(final_path, _write)
    return final_path


def _open(source: Path):
    validate_pdf_header(source)
    return open_reader(source)


def split_range(
    source: Path, start: int, end: int, output_path: Path,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Extract pages [start, end] (1-based, inclusive) into one file."""
    reader = _open(source)
    page_count = len(reader.pages)
    if start < 1 or end > page_count or start > end:
        raise FileValidationError(
            f"Page range {start}-{end} is out of bounds for a {page_count}-page document."
        )
    if progress_cb:
        progress_cb(30, f"Extracting pages {start}-{end}…")
    result = _write_pages(reader, list(range(start - 1, end)), output_path)
    if progress_cb:
        progress_cb(100, "Done")
    return result


def split_every_n(
    source: Path, n: int, output_dir: Path, base_name: str,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    """Split into consecutive chunks of ``n`` pages each."""
    if n < 1:
        raise FileValidationError("Pages per file must be at least 1.")
    reader = _open(source)
    page_count = len(reader.pages)
    chunks = [list(range(i, min(i + n, page_count))) for i in range(0, page_count, n)]
    outputs: list[Path] = []
    for idx, chunk in enumerate(chunks, start=1):
        out = output_dir / f"{base_name}_part{idx}.pdf"
        outputs.append(_write_pages(reader, chunk, out))
        if progress_cb:
            progress_cb(int(idx / len(chunks) * 100), f"Writing part {idx} of {len(chunks)}…")
    return outputs


def split_by_ranges(
    source: Path, ranges: list[tuple[int, int]], output_dir: Path, base_name: str,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    """Split into one file per explicit (start, end) 1-based inclusive range."""
    if not ranges:
        raise FileValidationError("Add at least one page range.")
    reader = _open(source)
    page_count = len(reader.pages)
    outputs: list[Path] = []
    for idx, (start, end) in enumerate(ranges, start=1):
        if start < 1 or end > page_count or start > end:
            raise FileValidationError(
                f"Page range {start}-{end} is out of bounds for a {page_count}-page document."
            )
        out = output_dir / f"{base_name}_{start}-{end}.pdf"
        outputs.append(_write_pages(reader, list(range(start - 1, end)), out))
        if progress_cb:
            progress_cb(int(idx / len(ranges) * 100), f"Writing range {start}-{end}…")
    return outputs


def split_odd(
    source: Path, output_path: Path, progress_cb: ProgressCallback | None = None,
) -> Path:
    """Extract odd-numbered pages (1, 3, 5, ...) into one file."""
    reader = _open(source)
    indices = list(range(0, len(reader.pages), 2))
    if progress_cb:
        progress_cb(40, "Collecting odd pages…")
    result = _write_pages(reader, indices, output_path)
    if progress_cb:
        progress_cb(100, "Done")
    return result


def split_even(
    source: Path, output_path: Path, progress_cb: ProgressCallback | None = None,
) -> Path:
    """Extract even-numbered pages (2, 4, 6, ...) into one file."""
    reader = _open(source)
    indices = list(range(1, len(reader.pages), 2))
    if progress_cb:
        progress_cb(40, "Collecting even pages…")
    result = _write_pages(reader, indices, output_path)
    if progress_cb:
        progress_cb(100, "Done")
    return result


def split_to_single_pages(
    source: Path, output_dir: Path, base_name: str,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    """Produce one PDF per page."""
    reader = _open(source)
    page_count = len(reader.pages)
    digits = max(2, len(str(page_count)))
    outputs: list[Path] = []
    for i in range(page_count):
        out = output_dir / f"{base_name}_page{str(i + 1).zfill(digits)}.pdf"
        outputs.append(_write_pages(reader, [i], out))
        if progress_cb:
            progress_cb(int((i + 1) / page_count * 100), f"Writing page {i + 1} of {page_count}…")
    return outputs
