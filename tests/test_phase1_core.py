"""Phase 1 functional tests — no mocked PDF operations.

These exercise the real SQLite-backed repositories, config persistence,
and the pypdf-backed side of the PDF engine against an actual PDF
generated with ReportLab. GUI (PySide6) code is exercised separately
via a headless smoke test (see test_gui_smoke.py) since it requires
PySide6 to be installed in the environment running the tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect the app's user-data dir into a pytest tmp_path so tests
    never touch the real %APPDATA%/PDFusion on the developer's machine."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # Reset singletons that cache paths/connections across tests.
    import app.database.database as db_module

    db_module._instance = None
    import app.utils.logger as logger_module

    logger_module._CONFIGURED = False
    yield


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    from reportlab.pdfgen import canvas

    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))
    for i in range(5):
        c.drawString(100, 700, f"PDFusion test page {i + 1}")
        c.showPage()
    c.save()
    return path


def test_pdf_header_validation(sample_pdf):
    from app.utils.validators import validate_pdf_header

    validate_pdf_header(sample_pdf)  # should not raise


def test_pdf_header_rejects_non_pdf(tmp_path):
    from app.utils.errors import FileValidationError
    from app.utils.validators import validate_pdf_header

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(FileValidationError):
        validate_pdf_header(bad)


def test_get_pdf_info_reports_correct_page_count(sample_pdf):
    from app.core.pdf_engine import get_pdf_info

    info = get_pdf_info(sample_pdf)
    assert info.page_count == 5
    assert info.is_encrypted is False
    assert info.file_size == sample_pdf.stat().st_size


def test_page_count_only(sample_pdf):
    from app.core.pdf_engine import page_count_only

    assert page_count_only(sample_pdf) == 5


def test_parse_page_range_basic():
    from app.utils.validators import parse_page_range

    assert parse_page_range("1-3,5", 5) == [0, 1, 2, 4]
    assert parse_page_range("2", 5) == [1]


def test_parse_page_range_out_of_bounds_raises():
    from app.utils.errors import FileValidationError
    from app.utils.validators import parse_page_range

    with pytest.raises(FileValidationError):
        parse_page_range("1-10", 5)


def test_parse_page_range_empty_raises():
    from app.utils.errors import FileValidationError
    from app.utils.validators import parse_page_range

    with pytest.raises(FileValidationError):
        parse_page_range("", 5)


def test_config_roundtrip():
    from app.config import AppConfig

    cfg = AppConfig.load()
    cfg.theme = "light"
    cfg.worker_threads = 7
    cfg.default_dpi = 300
    cfg.save()

    reloaded = AppConfig.load()
    assert reloaded.theme == "light"
    assert reloaded.worker_threads == 7
    assert reloaded.default_dpi == 300


def test_recent_files_repository(sample_pdf):
    from app.database.repositories import RecentFilesRepository

    repo = RecentFilesRepository()
    repo.touch(sample_pdf, page_count=5, last_operation="Opened")
    recents = repo.list_recent()
    assert len(recents) == 1
    assert recents[0].file_name == "sample.pdf"
    assert recents[0].page_count == 5

    repo.set_favorite(str(sample_pdf), True)
    recents = repo.list_recent()
    assert recents[0].is_favorite is True

    repo.remove(str(sample_pdf))
    assert repo.list_recent() == []


def test_history_repository():
    from app.database.repositories import HistoryRepository

    repo = HistoryRepository()
    entry_id = repo.start("merge", "Merge PDF", "a.pdf + b.pdf")
    repo.finish(entry_id, "success", "/tmp/out/merged.pdf", "2 files merged", 500)

    history = repo.list_recent()
    assert len(history) == 1
    assert history[0].status == "success"
    assert history[0].duration_ms == 500


def test_favorites_repository_toggle():
    from app.database.repositories import FavoritesRepository

    repo = FavoritesRepository()
    assert repo.toggle("merge") is True
    assert repo.list_favorites() == ["merge"]
    assert repo.toggle("merge") is False
    assert repo.list_favorites() == []


def test_atomic_write_never_leaves_partial_file(tmp_path):
    from app.utils.file_utils import atomic_write

    target = tmp_path / "output.pdf"

    def writer(p: Path) -> None:
        p.write_bytes(b"%PDF-1.4\ncontent")

    atomic_write(target, writer)
    assert target.exists()
    assert target.read_bytes().startswith(b"%PDF-")
    # no leftover temp files
    leftovers = list(tmp_path.glob(".*.tmp*"))
    assert leftovers == []


def test_unique_output_path_never_overwrites(tmp_path):
    from app.utils.file_utils import unique_output_path

    existing = tmp_path / "result.pdf"
    existing.write_bytes(b"%PDF-1.4")

    new_path = unique_output_path(existing)
    assert new_path != existing
    assert new_path.name == "result (1).pdf"


def test_dependency_scan_does_not_crash():
    from app.utils.dependency_checker import run_dependency_scan

    report = run_dependency_scan()
    names = {s.name for s in report.all_statuses}
    assert "Tesseract OCR" in names
    assert "LibreOffice" in names
    assert "Ghostscript" in names
    assert "PyMuPDF (fitz)" in names
