"""Organize PDF — a single-document workspace that lets the user stage
reorder / delete / duplicate / rotate / insert / replace edits, then
apply everything atomically on Save.

``OrganizeSession`` holds the *plan* (a list of ``PageRef``, one per
page that will exist in the output) and applies it only when
``save()`` is called — nothing touches disk before that. All reads are
read-only opens of the original and any inserted source documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter

from app.core.pdf_engine import open_reader
from app.utils.errors import FileValidationError
from app.utils.file_utils import atomic_write
from app.utils.logger import get_logger
from app.utils.validators import validate_pdf_header

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


@dataclass
class PageRef:
    """One page in the pending output — a pointer into a source document
    plus a rotation delta, never the page bytes themselves."""

    doc_key: str          # str(path) of the source document
    page_index: int       # 0-based page index within that document
    rotation: int = 0     # additional clockwise rotation in degrees

    def label(self) -> str:
        rot = f"  •  {self.rotation}\u00b0" if self.rotation else ""
        return f"{Path(self.doc_key).name} — page {self.page_index + 1}{rot}"


class OrganizeSession:
    """Editable in-memory plan for a single document, backed by pypdf
    readers opened lazily and kept alive for the session's lifetime."""

    def __init__(self, path: Path):
        self.original_path = Path(path)
        validate_pdf_header(self.original_path)
        self._readers: dict[str, PdfReader] = {}
        reader = self._reader_for(str(self.original_path))
        self.pages: list[PageRef] = [
            PageRef(str(self.original_path), i) for i in range(len(reader.pages))
        ]

    # -- source document management -------------------------------------
    def _reader_for(self, doc_key: str) -> PdfReader:
        reader = self._readers.get(doc_key)
        if reader is None:
            reader = open_reader(Path(doc_key))
            self._readers[doc_key] = reader
        return reader

    def register_source(self, path: Path) -> str:
        """Open an external PDF for insert/replace and return its key."""
        validate_pdf_header(Path(path))
        key = str(Path(path))
        self._reader_for(key)
        return key

    def page_count_of(self, doc_key: str) -> int:
        return len(self._reader_for(doc_key).pages)

    # -- edits (all operate on ``self.pages`` only; nothing touches disk) --
    def move(self, from_index: int, to_index: int) -> None:
        self._check_index(from_index)
        item = self.pages.pop(from_index)
        to_index = max(0, min(to_index, len(self.pages)))
        self.pages.insert(to_index, item)

    def delete(self, index: int) -> None:
        self._check_index(index)
        if len(self.pages) <= 1:
            raise FileValidationError("A document must have at least one page.")
        del self.pages[index]

    def delete_many(self, indices: list[int]) -> None:
        if len(self.pages) - len(indices) < 1:
            raise FileValidationError("A document must have at least one page.")
        for i in sorted(set(indices), reverse=True):
            self._check_index(i)
            del self.pages[i]

    def duplicate(self, index: int) -> None:
        self._check_index(index)
        ref = self.pages[index]
        self.pages.insert(index + 1, PageRef(ref.doc_key, ref.page_index, ref.rotation))

    def rotate(self, index: int, degrees: int) -> None:
        self._check_index(index)
        self.pages[index].rotation = (self.pages[index].rotation + degrees) % 360

    def rotate_many(self, indices: list[int], degrees: int) -> None:
        for i in indices:
            self.rotate(i, degrees)

    def insert_from(self, source_path: Path, source_page_indices: list[int], position: int) -> None:
        """Insert pages from another PDF at ``position`` (0-based, before
        the current item at that index; use len(self.pages) to append)."""
        key = self.register_source(source_path)
        max_page = self.page_count_of(key)
        for idx in source_page_indices:
            if not (0 <= idx < max_page):
                raise FileValidationError(f"Page {idx + 1} does not exist in the inserted file.")
        position = max(0, min(position, len(self.pages)))
        new_refs = [PageRef(key, idx) for idx in source_page_indices]
        self.pages[position:position] = new_refs

    def replace(self, index: int, source_path: Path, source_page_index: int) -> None:
        """Replace the page at ``index`` with a page from another PDF."""
        self._check_index(index)
        key = self.register_source(source_path)
        max_page = self.page_count_of(key)
        if not (0 <= source_page_index < max_page):
            raise FileValidationError("Selected replacement page does not exist in that file.")
        self.pages[index] = PageRef(key, source_page_index)

    def keep_only(self, indices: list[int]) -> None:
        """Extract a subset in-session: drop every page not in ``indices``."""
        if not indices:
            raise FileValidationError("Select at least one page to keep.")
        keep = sorted(set(indices))
        self.pages = [self.pages[i] for i in keep]

    def _check_index(self, index: int) -> None:
        if not (0 <= index < len(self.pages)):
            raise FileValidationError("That page no longer exists in the current plan.")

    # -- apply -------------------------------------------------------------
    def save(self, output_path: Path, progress_cb: ProgressCallback | None = None) -> Path:
        if not self.pages:
            raise FileValidationError("The document has no pages to save.")
        writer = PdfWriter()
        total = len(self.pages)
        for i, ref in enumerate(self.pages):
            reader = self._reader_for(ref.doc_key)
            new_page = writer.add_page(reader.pages[ref.page_index])
            if ref.rotation:
                new_page.rotate(ref.rotation)
            if progress_cb:
                progress_cb(int((i + 1) / total * 90), f"Assembling page {i + 1} of {total}…")

        def _write(tmp_path: Path) -> None:
            with open(tmp_path, "wb") as fh:
                writer.write(fh)

        if progress_cb:
            progress_cb(95, "Writing file…")
        atomic_write(output_path, _write)
        if progress_cb:
            progress_cb(100, "Done")
        logger.info("Organize session saved %d page(s) -> %s", total, output_path)
        return output_path

    def close(self) -> None:
        self._readers.clear()
