"""Shared PDF document abstraction.

Design:
    * Structural metadata (page count, encryption state, basic metadata)
      is read with ``pypdf`` — pure Python, always available.
    * Rendering (thumbnails, page images) uses ``PyMuPDF`` (fitz) when
      installed, since it is dramatically faster and higher quality.
      If fitz is missing, viewing/rendering features degrade gracefully
      with a clear "install PyMuPDF" message rather than crashing.

Every other core module (merger, splitter, organizer, ...) builds on
top of ``PdfDocument`` so there is exactly one place that opens files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.utils.errors import PasswordRequiredError, PdfCorruptedError, FileValidationError
from app.utils.logger import get_logger
from app.utils.validators import validate_pdf_header

logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised on machines without PyMuPDF
    fitz = None  # type: ignore
    FITZ_AVAILABLE = False


@dataclass
class PdfInfo:
    path: Path
    page_count: int
    is_encrypted: bool
    title: str | None
    author: str | None
    file_size: int


def open_reader(path: Path, password: str | None = None) -> PdfReader:
    """Open a PDF with pypdf, raising friendly errors instead of raw ones."""
    validate_pdf_header(path)
    try:
        reader = PdfReader(str(path))
    except PdfReadError as exc:
        raise PdfCorruptedError(
            f"'{path.name}' could not be parsed. It may be corrupted — try "
            "the Repair PDF tool.",
            technical_detail=str(exc),
        ) from exc

    if reader.is_encrypted:
        pwd = password or ""
        result = reader.decrypt(pwd)
        # pypdf returns 0 for fail, 1 for user password, 2 for owner password
        if result == 0:
            raise PasswordRequiredError(
                f"'{path.name}' is password-protected. Enter the correct password."
            )
    return reader


def get_pdf_info(path: Path, password: str | None = None) -> PdfInfo:
    path = Path(path)
    validate_pdf_header(path)
    reader_for_meta = PdfReader(str(path))
    encrypted = reader_for_meta.is_encrypted

    page_count = 0
    title = author = None
    if encrypted and not password:
        # Still report basic facts without decrypting.
        try:
            page_count = len(reader_for_meta.pages)
        except Exception:
            page_count = 0
    else:
        reader = open_reader(path, password)
        page_count = len(reader.pages)
        meta = reader.metadata or {}
        title = getattr(meta, "title", None)
        author = getattr(meta, "author", None)

    return PdfInfo(
        path=path,
        page_count=page_count,
        is_encrypted=encrypted,
        title=title,
        author=author,
        file_size=path.stat().st_size,
    )


def require_fitz() -> None:
    if not FITZ_AVAILABLE:
        from app.utils.errors import DependencyMissingError

        raise DependencyMissingError(
            "PyMuPDF",
            install_hint="Install with `pip install PyMuPDF` to enable page "
            "rendering, thumbnails, redaction, and page-level cropping.",
        )


def page_count_only(path: Path) -> int:
    """Fast page count without full parsing overhead where possible."""
    validate_pdf_header(path)
    if FITZ_AVAILABLE:
        with fitz.open(str(path)) as doc:  # type: ignore[union-attr]
            return doc.page_count
    reader = PdfReader(str(path))
    return len(reader.pages)
