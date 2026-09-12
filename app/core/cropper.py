"""Crop PDF — shrink each targeted page's crop box by explicit margins
(in points), scoped to a single page, a set of pages, or all pages.

Cropping only ever adjusts the ``/CropBox`` — the page's ``/MediaBox``
(and its content stream) is left untouched, so the operation is
non-destructive and reversible by re-cropping with zero margins.
"""
from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class CropMargins:
    left: float = 0.0
    bottom: float = 0.0
    right: float = 0.0
    top: float = 0.0

    def is_zero(self) -> bool:
        return not any((self.left, self.bottom, self.right, self.top))


def preview_cropbox(source: Path, page_index: int, margins: CropMargins) -> tuple[float, float, float, float]:
    """Return the (left, bottom, right, top) crop box for one page without
    writing anything — used to draw a live preview overlay."""
    validate_pdf_header(source)
    reader = open_reader(source)
    if not (0 <= page_index < len(reader.pages)):
        raise FileValidationError("That page does not exist in this document.")
    box = reader.pages[page_index].mediabox
    left = float(box.left) + margins.left
    bottom = float(box.bottom) + margins.bottom
    right = float(box.right) - margins.right
    top = float(box.top) - margins.top
    return _clamp_box(box, left, bottom, right, top)


def _clamp_box(box, left, bottom, right, top) -> tuple[float, float, float, float]:
    if right <= left or top <= bottom:
        raise FileValidationError("Margins are too large — nothing would remain on the page.")
    return left, bottom, right, top


def crop_pdf(
    source: Path,
    margins: CropMargins,
    output_path: Path,
    page_indices: list[int] | None = None,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Apply ``margins`` (points) to the crop box of the targeted pages."""
    if margins.is_zero():
        raise FileValidationError("Set at least one non-zero margin before cropping.")

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
            box = new_page.mediabox
            left, bottom, right, top = _clamp_box(
                box,
                float(box.left) + margins.left,
                float(box.bottom) + margins.bottom,
                float(box.right) - margins.right,
                float(box.top) - margins.top,
            )
            new_page.cropbox.lower_left = (left, bottom)
            new_page.cropbox.upper_right = (right, top)
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
    logger.info("Cropped %d page(s) -> %s", len(target), output_path)
    return output_path
