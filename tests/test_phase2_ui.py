"""Headless smoke coverage for the Phase 2 tool-page boundaries."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    from reportlab.pdfgen import canvas

    path = tmp_path / "ui-source.pdf"
    document = canvas.Canvas(str(path))
    for page in range(4):
        document.drawString(100, 700, f"UI page {page + 1}")
        document.showPage()
    document.save()
    return path


def test_rotate_page_builds_scoped_worker(qt_app, pdf_file):
    from app.ui.tools.rotate_page import RotatePage
    from app.workers.rotate_worker import RotateWorker

    page = RotatePage()
    page._set_source([str(pdf_file)])
    page.current_page.setValue(3)
    page.angle_group.button(180).setChecked(True)
    worker = page._make_worker()
    assert isinstance(worker, RotateWorker)
    assert worker.page_indices == [2]
    assert pdf_file.exists()


def test_crop_page_keeps_margin_configuration_staged(qt_app, pdf_file):
    from app.ui.tools.crop_page import CropPage
    from app.workers.crop_worker import CropWorker

    page = CropPage()
    page._set_source([str(pdf_file)])
    page.margin_spins["top"].setValue(12.5)
    page.margin_spins["left"].setValue(8)
    worker = page._make_worker()
    assert isinstance(worker, CropWorker)
    assert worker.margins.top == 12.5
    assert worker.margins.left == 8


def test_extract_page_parses_range_into_worker(qt_app, pdf_file):
    from app.ui.tools.extract_page import ExtractPage
    from app.workers.extract_worker import ExtractWorker

    page = ExtractPage()
    page._set_source([str(pdf_file)])
    page.range_edit.setText("1-2,4")
    worker = page._make_worker()
    assert isinstance(worker, ExtractWorker)
    assert worker.page_indices == [0, 1, 3]


def test_organize_page_stages_edits_before_save(qt_app, pdf_file):
    from app.ui.tools.organize_page import OrganizePage
    from app.workers.organize_worker import OrganizeWorker

    page = OrganizePage()
    original = pdf_file.read_bytes()
    page._set_source([str(pdf_file)])
    page.page_list.item(1).setSelected(True)
    page._duplicate()
    assert len(page._session.pages) == 5
    assert pdf_file.read_bytes() == original
    worker = page._make_worker()
    assert isinstance(worker, OrganizeWorker)
