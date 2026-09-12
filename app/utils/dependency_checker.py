"""Detects optional runtime dependencies so the app never crashes because
one is missing — instead each tool can check `DependencyStatus.available`
and show a clear "Feature unavailable because X is not installed" message
with a configuration button pointing at Settings > Advanced.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DependencyStatus:
    name: str
    available: bool
    path: str | None = None
    version: str | None = None
    install_hint: str = ""


def _probe_binary(candidates: list[str], version_arg: str = "--version") -> tuple[str | None, str | None]:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            version = None
            try:
                result = subprocess.run(
                    [found, version_arg],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                version = (result.stdout or result.stderr).splitlines()[0].strip()
            except Exception:  # pragma: no cover - best effort only
                pass
            return found, version
    return None, None


def check_tesseract(custom_path: str | None = None) -> DependencyStatus:
    candidates = [custom_path] if custom_path else []
    candidates += ["tesseract", "tesseract.exe"]
    path, version = _probe_binary([c for c in candidates if c])
    return DependencyStatus(
        name="Tesseract OCR",
        available=path is not None,
        path=path,
        version=version,
        install_hint=(
            "Install from https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
            "or `apt install tesseract-ocr` (Linux), then set the path in "
            "Settings > Advanced if it isn't auto-detected."
        ),
    )


def check_libreoffice(custom_path: str | None = None) -> DependencyStatus:
    candidates = [custom_path] if custom_path else []
    candidates += ["soffice", "libreoffice", "soffice.exe"]
    path, version = _probe_binary([c for c in candidates if c])
    return DependencyStatus(
        name="LibreOffice",
        available=path is not None,
        path=path,
        version=version,
        install_hint=(
            "Install from https://www.libreoffice.org/download/ — required for "
            "Office-to-PDF conversion. Set the path in Settings > Advanced if "
            "it isn't auto-detected."
        ),
    )


def check_ghostscript(custom_path: str | None = None) -> DependencyStatus:
    candidates = [custom_path] if custom_path else []
    candidates += ["gs", "gswin64c", "gswin32c", "gswin64c.exe"]
    path, version = _probe_binary([c for c in candidates if c])
    return DependencyStatus(
        name="Ghostscript",
        available=path is not None,
        path=path,
        version=version,
        install_hint=(
            "Install from https://ghostscript.com/releases/ — improves high-"
            "compression PDF optimization. Optional; PyMuPDF-based compression "
            "still works without it."
        ),
    )


def check_pymupdf() -> DependencyStatus:
    try:
        import fitz  # noqa: F401

        return DependencyStatus(name="PyMuPDF (fitz)", available=True, version=fitz.__doc__)
    except ImportError:
        return DependencyStatus(
            name="PyMuPDF (fitz)",
            available=False,
            install_hint="Install with `pip install PyMuPDF`. Required for page "
            "rendering, thumbnails, and redaction.",
        )


def check_pytesseract_binding() -> DependencyStatus:
    try:
        import pytesseract  # noqa: F401

        return DependencyStatus(name="pytesseract", available=True)
    except ImportError:
        return DependencyStatus(
            name="pytesseract",
            available=False,
            install_hint="Install with `pip install pytesseract`.",
        )


@dataclass
class DependencyReport:
    tesseract: DependencyStatus
    libreoffice: DependencyStatus
    ghostscript: DependencyStatus
    pymupdf: DependencyStatus
    pytesseract_binding: DependencyStatus
    all_statuses: list[DependencyStatus] = field(default_factory=list)

    def __post_init__(self):
        self.all_statuses = [
            self.pymupdf,
            self.pytesseract_binding,
            self.tesseract,
            self.libreoffice,
            self.ghostscript,
        ]


def run_dependency_scan(
    tesseract_path: str | None = None,
    libreoffice_path: str | None = None,
    ghostscript_path: str | None = None,
) -> DependencyReport:
    report = DependencyReport(
        tesseract=check_tesseract(tesseract_path),
        libreoffice=check_libreoffice(libreoffice_path),
        ghostscript=check_ghostscript(ghostscript_path),
        pymupdf=check_pymupdf(),
        pytesseract_binding=check_pytesseract_binding(),
    )
    for status in report.all_statuses:
        symbol = "OK" if status.available else "MISSING"
        logger.info("Dependency %-18s [%s] %s", status.name, symbol, status.path or "")
    return report
