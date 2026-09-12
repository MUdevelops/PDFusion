"""Application-wide constants: branding, palette, and static paths.

Nothing in this module performs I/O — it is safe to import from anywhere,
including worker threads, without side effects.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Branding
# --------------------------------------------------------------------------
APP_NAME = "PDFusion"
APP_TAGLINE = "All-in-One PDF Workspace"
APP_VERSION = "0.1.0"
APP_ORG = "PDFusion"
APP_DESCRIPTION = "Built for fast, private, local document processing."

# --------------------------------------------------------------------------
# Filesystem layout
# --------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = APP_ROOT / "app" / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"


def user_data_dir() -> Path:
    """Return (and ensure) the per-user application data directory.

    Windows:  %APPDATA%/PDFusion
    macOS:    ~/Library/Application Support/PDFusion
    Linux:    ~/.local/share/PDFusion
    """
    import os
    import sys

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def logs_dir() -> Path:
    d = user_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def temp_dir() -> Path:
    d = user_data_dir() / "temp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def database_path() -> Path:
    return user_data_dir() / "pdfusion.sqlite3"


# --------------------------------------------------------------------------
# Palette — Deep navy / electric blue / white / subtle violet accent
# --------------------------------------------------------------------------
class Palette:
    # Dark theme
    DARK_BG_PRIMARY = "#0B1220"
    DARK_BG_SECONDARY = "#111A2E"
    DARK_BG_CARD = "#16213A"
    DARK_BG_ELEVATED = "#1C2A47"
    DARK_BORDER = "#243352"
    DARK_TEXT_PRIMARY = "#F2F5FA"
    DARK_TEXT_SECONDARY = "#93A1BE"
    DARK_TEXT_MUTED = "#5E6C8A"

    # Light theme
    LIGHT_BG_PRIMARY = "#F5F7FB"
    LIGHT_BG_SECONDARY = "#FFFFFF"
    LIGHT_BG_CARD = "#FFFFFF"
    LIGHT_BG_ELEVATED = "#EEF1F8"
    LIGHT_BORDER = "#DCE2EE"
    LIGHT_TEXT_PRIMARY = "#101526"
    LIGHT_TEXT_SECONDARY = "#4B5674"
    LIGHT_TEXT_MUTED = "#8592AD"

    # Shared accents
    ACCENT_PRIMARY = "#2F6FED"      # electric blue
    ACCENT_PRIMARY_HOVER = "#4A83F0"
    ACCENT_PRIMARY_PRESSED = "#1F55C4"
    ACCENT_VIOLET = "#7C6BF0"       # subtle violet accent
    SUCCESS = "#2FBF71"
    WARNING = "#F2A93B"
    DANGER = "#EF4B5F"
    INFO = "#2F9BED"


# --------------------------------------------------------------------------
# Tool identifiers (used for routing, favorites, history, shortcuts)
# --------------------------------------------------------------------------
class ToolId:
    MERGE = "merge"
    SPLIT = "split"
    ORGANIZE = "organize"
    ROTATE = "rotate"
    CROP = "crop"
    EXTRACT = "extract"

    PDF_TO_WORD = "pdf_to_word"
    PDF_TO_IMAGE = "pdf_to_image"
    IMAGE_TO_PDF = "image_to_pdf"
    OFFICE_TO_PDF = "office_to_pdf"
    PDF_TO_TEXT = "pdf_to_text"

    COMPRESS = "compress"
    OPTIMIZE = "optimize"
    REPAIR = "repair"

    EDIT = "edit"
    ANNOTATE = "annotate"
    WATERMARK = "watermark"
    PAGE_NUMBERS = "page_numbers"
    SIGNATURE = "signature"
    REDACT = "redact"

    PROTECT = "protect"
    UNLOCK = "unlock"
    METADATA = "metadata"

    OCR_PDF = "ocr_pdf"
    OCR_IMAGE = "ocr_image"
    SEARCHABLE_PDF = "searchable_pdf"


TOOL_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "Organize": [
        (ToolId.MERGE, "Merge PDF"),
        (ToolId.SPLIT, "Split PDF"),
        (ToolId.ORGANIZE, "Organize PDF"),
        (ToolId.ROTATE, "Rotate PDF"),
        (ToolId.CROP, "Crop PDF"),
        (ToolId.EXTRACT, "Extract Pages"),
    ],
}

QUICK_ACTIONS: list[tuple[str, str]] = [
    (ToolId.MERGE, "Merge PDF"),
    (ToolId.SPLIT, "Split PDF"),
    (ToolId.ORGANIZE, "Organize PDF"),
    (ToolId.ROTATE, "Rotate PDF"),
    (ToolId.CROP, "Crop PDF"),
    (ToolId.EXTRACT, "Extract Pages"),
]
