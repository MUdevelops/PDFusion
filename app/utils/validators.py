"""Input validation shared by every tool before it touches a real file."""
from __future__ import annotations

from pathlib import Path

from app.utils.errors import FileValidationError

PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx"}


def validate_exists_and_readable(path: Path) -> None:
    if not path.exists():
        raise FileValidationError(f"'{path.name}' could not be found.")
    if not path.is_file():
        raise FileValidationError(f"'{path.name}' is not a file.")
    try:
        with open(path, "rb") as fh:
            fh.read(4)
    except PermissionError as exc:
        raise FileValidationError(
            f"'{path.name}' could not be opened (permission denied)."
        ) from exc
    except OSError as exc:
        raise FileValidationError(f"'{path.name}' could not be read.") from exc


def validate_suffix(path: Path, allowed: set[str], kind: str) -> None:
    if path.suffix.lower() not in allowed:
        raise FileValidationError(
            f"'{path.name}' is not a supported {kind} file "
            f"({', '.join(sorted(allowed))})."
        )


def validate_pdf_header(path: Path) -> None:
    """Cheap sanity check: real PDFs start with %PDF-."""
    validate_exists_and_readable(path)
    validate_suffix(path, PDF_SUFFIXES, "PDF")
    with open(path, "rb") as fh:
        header = fh.read(5)
    if header != b"%PDF-":
        raise FileValidationError(
            f"'{path.name}' does not look like a valid PDF file."
        )


def validate_image(path: Path) -> None:
    validate_exists_and_readable(path)
    validate_suffix(path, IMAGE_SUFFIXES, "image")


def validate_office(path: Path) -> None:
    validate_exists_and_readable(path)
    validate_suffix(path, OFFICE_SUFFIXES, "Office")


def parse_page_range(spec: str, page_count: int) -> list[int]:
    """Parse a user page-range string like '1-3,5,8-10' into 0-based indices.

    Raises FileValidationError on anything out of bounds or malformed.
    """
    if not spec.strip():
        raise FileValidationError("Page range cannot be empty.")

    indices: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            parts = chunk.split("-")
            if len(parts) != 2:
                raise FileValidationError(f"Invalid page range segment: '{chunk}'.")
            start_s, end_s = parts
            try:
                start, end = int(start_s), int(end_s)
            except ValueError as exc:
                raise FileValidationError(f"Invalid page range segment: '{chunk}'.") from exc
            if start < 1 or end > page_count or start > end:
                raise FileValidationError(
                    f"Page range '{chunk}' is out of bounds for a {page_count}-page document."
                )
            indices.extend(range(start - 1, end))
        else:
            try:
                page = int(chunk)
            except ValueError as exc:
                raise FileValidationError(f"Invalid page number: '{chunk}'.") from exc
            if page < 1 or page > page_count:
                raise FileValidationError(
                    f"Page {page} is out of bounds for a {page_count}-page document."
                )
            indices.append(page - 1)
    # de-dupe while preserving order
    seen: set[int] = set()
    ordered = []
    for i in indices:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered
