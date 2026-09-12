"""Phase 2 functional tests — exercise the real Organize-category core
modules (merge, split, organize, rotate, crop, extract) against actual
PDFs generated with ReportLab. No mocked PDF operations.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import app.database.database as db_module

    db_module._instance = None
    import app.utils.logger as logger_module

    logger_module._CONFIGURED = False
    yield


def _make_pdf(path: Path, n: int, prefix: str = "Page") -> Path:
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    for i in range(n):
        c.setFont("Helvetica", 24)
        c.drawString(100, 700, f"{prefix} {i + 1}")
        c.showPage()
    c.save()
    return path


@pytest.fixture
def pdf_a(tmp_path) -> Path:
    return _make_pdf(tmp_path / "a.pdf", 5, "A")


@pytest.fixture
def pdf_b(tmp_path) -> Path:
    return _make_pdf(tmp_path / "b.pdf", 3, "B")


# -- Merge ------------------------------------------------------------------
def test_merge_preserves_order_and_rotation(pdf_a, pdf_b, tmp_path):
    from pypdf import PdfReader

    from app.core.merger import MergeItem, merge_pdfs

    orig_a, orig_b = pdf_a.read_bytes(), pdf_b.read_bytes()
    out = tmp_path / "merged.pdf"
    items = [MergeItem(pdf_a, page_rotations={0: 90}), MergeItem(pdf_b, page_rotations={2: 180})]
    merge_pdfs(items, out)

    r = PdfReader(str(out))
    assert len(r.pages) == 8
    assert [p.extract_text().strip() for p in r.pages] == [
        "A 1", "A 2", "A 3", "A 4", "A 5", "B 1", "B 2", "B 3",
    ]
    assert r.pages[0].get("/Rotate") == 90
    assert r.pages[7].get("/Rotate") == 180
    assert pdf_a.read_bytes() == orig_a
    assert pdf_b.read_bytes() == orig_b


def test_merge_requires_at_least_one_file(tmp_path):
    from app.core.merger import merge_pdfs
    from app.utils.errors import FileValidationError

    with pytest.raises(FileValidationError):
        merge_pdfs([], tmp_path / "out.pdf")


# -- Split --------------------------------------------------------------
def test_split_range(pdf_a, tmp_path):
    from pypdf import PdfReader

    from app.core import splitter

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = splitter.split_range(pdf_a, 2, 4, out_dir / "range.pdf")
    r = PdfReader(str(result))
    assert [p.extract_text().strip() for p in r.pages] == ["A 2", "A 3", "A 4"]


def test_split_every_n(tmp_path):
    from pypdf import PdfReader

    from app.core import splitter

    src = _make_pdf(tmp_path / "src.pdf", 10, "P")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    outs = splitter.split_every_n(src, 3, out_dir, "part")
    counts = [len(PdfReader(str(o)).pages) for o in outs]
    assert counts == [3, 3, 3, 1]


def test_split_by_explicit_ranges(tmp_path):
    from pypdf import PdfReader

    from app.core import splitter

    src = _make_pdf(tmp_path / "src.pdf", 10, "P")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    outs = splitter.split_by_ranges(src, [(1, 2), (5, 7)], out_dir, "range")
    counts = [len(PdfReader(str(o)).pages) for o in outs]
    assert counts == [2, 3]


def test_split_odd_even(tmp_path):
    from pypdf import PdfReader

    from app.core import splitter

    src = _make_pdf(tmp_path / "src.pdf", 6, "P")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    odd = splitter.split_odd(src, out_dir / "odd.pdf")
    even = splitter.split_even(src, out_dir / "even.pdf")
    assert [p.extract_text().strip() for p in PdfReader(str(odd)).pages] == ["P 1", "P 3", "P 5"]
    assert [p.extract_text().strip() for p in PdfReader(str(even)).pages] == ["P 2", "P 4", "P 6"]


def test_split_to_single_pages_and_no_overwrite(tmp_path):
    from app.core import splitter

    src = _make_pdf(tmp_path / "src.pdf", 4, "P")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    outs = splitter.split_to_single_pages(src, out_dir, "single")
    assert len(outs) == 4

    # Running split_range twice with the same target name must never overwrite.
    r1 = splitter.split_range(src, 1, 2, out_dir / "dup.pdf")
    r2 = splitter.split_range(src, 1, 2, out_dir / "dup.pdf")
    assert r1 != r2
    assert r1.exists() and r2.exists()


# -- Organize -------------------------------------------------------------
def test_organize_reorder_delete_duplicate_rotate_insert_replace(pdf_a, tmp_path):
    from pypdf import PdfReader

    from app.core.organizer import OrganizeSession

    extra = _make_pdf(tmp_path / "extra.pdf", 2, "X")
    orig_a, orig_extra = pdf_a.read_bytes(), extra.read_bytes()

    sess = OrganizeSession(pdf_a)
    assert len(sess.pages) == 5

    sess.move(0, 4)                       # [1,2,3,4,0]
    sess.delete(0)                        # [2,3,4,0]
    sess.duplicate(0)                     # [2,2,3,4,0]
    sess.rotate(0, 90)
    sess.insert_from(extra, [0, 1], 2)    # insert X1,X2 at position 2
    sess.replace(0, extra, 1)             # replace first item with X2

    out = tmp_path / "organized.pdf"
    sess.save(out)
    r = PdfReader(str(out))
    assert len(r.pages) == 7
    assert pdf_a.read_bytes() == orig_a
    assert extra.read_bytes() == orig_extra


def test_organize_keep_only_extracts_subset(pdf_a, tmp_path):
    from pypdf import PdfReader

    from app.core.organizer import OrganizeSession

    sess = OrganizeSession(pdf_a)
    sess.keep_only([1, 3])
    out = tmp_path / "kept.pdf"
    sess.save(out)
    r = PdfReader(str(out))
    assert [p.extract_text().strip() for p in r.pages] == ["A 2", "A 4"]


def test_organize_cannot_delete_last_page(pdf_a, tmp_path):
    from app.core.organizer import OrganizeSession
    from app.utils.errors import FileValidationError

    sess = OrganizeSession(pdf_a)
    sess.keep_only([0])
    with pytest.raises(FileValidationError):
        sess.delete(0)


# -- Rotate -----------------------------------------------------------------
def test_rotate_scoped_pages_only(tmp_path):
    from pypdf import PdfReader

    from app.core.rotator import rotate_pdf

    src = _make_pdf(tmp_path / "src.pdf", 4, "P")
    orig = src.read_bytes()
    out = tmp_path / "rot.pdf"
    rotate_pdf(src, 90, out, page_indices=[0, 2])
    r = PdfReader(str(out))
    assert [p.get("/Rotate") for p in r.pages] == [90, 0, 90, 0]
    assert src.read_bytes() == orig


def test_rotate_all_pages_when_no_scope_given(tmp_path):
    from pypdf import PdfReader

    from app.core.rotator import rotate_pdf

    src = _make_pdf(tmp_path / "src.pdf", 3, "P")
    out = tmp_path / "rot_all.pdf"
    rotate_pdf(src, 180, out)
    r = PdfReader(str(out))
    assert all(p.get("/Rotate") == 180 for p in r.pages)


def test_rotate_rejects_invalid_angle(tmp_path):
    from app.core.rotator import rotate_pdf
    from app.utils.errors import FileValidationError

    src = _make_pdf(tmp_path / "src.pdf", 2, "P")
    with pytest.raises(FileValidationError):
        rotate_pdf(src, 45, tmp_path / "out.pdf")


# -- Crop -------------------------------------------------------------------
def test_crop_scoped_page_only(tmp_path):
    from pypdf import PdfReader

    from app.core.cropper import CropMargins, crop_pdf

    src = _make_pdf(tmp_path / "src.pdf", 2, "P")
    orig = src.read_bytes()
    out = tmp_path / "crop.pdf"
    crop_pdf(src, CropMargins(left=10, bottom=10, right=10, top=10), out, page_indices=[1])
    r = PdfReader(str(out))
    assert tuple(r.pages[0].cropbox.lower_left) == tuple(r.pages[0].mediabox.lower_left)
    assert tuple(r.pages[1].cropbox.lower_left) == (10, 10)
    assert src.read_bytes() == orig


def test_crop_rejects_margins_that_consume_whole_page(tmp_path):
    from app.core.cropper import CropMargins, crop_pdf
    from app.utils.errors import FileValidationError

    src = _make_pdf(tmp_path / "src.pdf", 1, "P")
    with pytest.raises(FileValidationError):
        crop_pdf(src, CropMargins(left=1000, bottom=1000, right=1000, top=1000), tmp_path / "out.pdf")


# -- Extract ------------------------------------------------------------
def test_extract_pages_subset(tmp_path):
    from pypdf import PdfReader

    from app.core.extractor import extract_pages

    src = _make_pdf(tmp_path / "src.pdf", 5, "P")
    orig = src.read_bytes()
    out = tmp_path / "extracted.pdf"
    extract_pages(src, [0, 4], out)
    r = PdfReader(str(out))
    assert [p.extract_text().strip() for p in r.pages] == ["P 1", "P 5"]
    assert src.read_bytes() == orig


def test_extract_rejects_out_of_bounds(tmp_path):
    from app.core.extractor import extract_pages
    from app.utils.errors import FileValidationError

    src = _make_pdf(tmp_path / "src.pdf", 3, "P")
    with pytest.raises(FileValidationError):
        extract_pages(src, [0, 10], tmp_path / "out.pdf")
