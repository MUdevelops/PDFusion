"""Crop a PDF by margins, with an optional PyMuPDF preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QDoubleSpinBox, QHBoxLayout, QLabel, QRadioButton, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget, QPushButton,
)

from app.config import AppConfig
from app.constants import ToolId
from app.core import pdf_engine
from app.core.cropper import CropMargins, preview_cropbox
from app.core.pdf_engine import page_count_only
from app.core.renderer import PageRenderer
from app.ui.tools.common import PagePickerWidget, ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError
from app.utils.file_utils import unique_output_path
from app.utils.validators import PDF_SUFFIXES


class _CropPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._box: tuple[float, float, float, float] | None = None
        self._page_size = (1.0, 1.0)
        self.setMinimumSize(260, 220)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_preview(self, data: bytes, box: tuple[float, float, float, float], page_size: tuple[float, float]) -> None:
        self._pixmap.loadFromData(data)
        self._box = box
        self._page_size = page_size
        self.update()

    def clear_preview(self) -> None:
        self._pixmap = QPixmap()
        self._box = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._pixmap.isNull() or self._box is None:
            return
        painter = QPainter(self)
        image = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        left = (self.width() - image.width()) / 2
        top = (self.height() - image.height()) / 2
        painter.drawPixmap(int(left), int(top), image)
        page_w, page_h = self._page_size
        x0, y0, x1, y1 = self._box
        rect = image.rect()
        overlay = rect.adjusted(
            int((x0 / page_w) * rect.width()),
            int(((page_h - y1) / page_h) * rect.height()),
            -int(((page_w - x1) / page_w) * rect.width()),
            -int((y0 / page_h) * rect.height()),
        )
        overlay.translate(int(left), int(top))
        painter.setPen(QPen(QColor("#2FBF71"), 3))
        painter.drawRect(overlay)
        painter.end()


class CropPage(ToolPageBase):
    def __init__(self, parent=None):
        self._source: Path | None = None
        self._page_count = 0
        super().__init__(ToolId.CROP, "Crop PDF", parent)

    def _build_select_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop = DropZone("Drop a PDF here", "or click Browse to select a file", PDF_SUFFIXES)
        drop.filesDropped.connect(self._set_source)
        layout.addWidget(drop)
        return w

    def _set_source(self, paths: list[str]) -> None:
        if not paths:
            return
        path = Path(paths[0])
        try:
            self._page_count = page_count_only(path)
        except FileValidationError as exc:
            show_toast(self.window(), exc.message, kind="error")
            return
        self._source = path
        self.source_label.setText(f"{path.name}  •  {self._page_count} pages")
        self.current_page.setMaximum(self._page_count)
        self.current_page.setValue(1)
        self._replace_picker()
        self._update_preview()
        self.go_to_configure()

    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.source_label = QLabel("No file selected")
        self.source_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.source_label)

        margins = QHBoxLayout()
        self.margin_spins: dict[str, QDoubleSpinBox] = {}
        for name in ("top", "bottom", "left", "right"):
            margins.addWidget(QLabel(f"{name.title()} (pt)"))
            spin = QDoubleSpinBox()
            spin.setRange(0, 10000)
            spin.setDecimals(1)
            spin.valueChanged.connect(self._update_preview)
            self.margin_spins[name] = spin
            margins.addWidget(spin)
        layout.addLayout(margins)

        layout.addWidget(QLabel("Scope"))
        self.scope_group = QButtonGroup(self)
        self.scope_stack = QStackedWidget()
        current = QWidget()
        current_row = QHBoxLayout(current)
        current_row.addWidget(QLabel("Current page:"))
        self.current_page = QSpinBox()
        self.current_page.setMinimum(1)
        self.current_page.valueChanged.connect(self._update_preview)
        current_row.addWidget(self.current_page)
        current_row.addStretch()
        selected = QWidget()
        self.selected_layout = QVBoxLayout(selected)
        self.selected_layout.setContentsMargins(0, 0, 0, 0)
        self.page_picker: PagePickerWidget | None = None
        self.scope_stack.addWidget(current)
        self.scope_stack.addWidget(selected)
        self.scope_stack.addWidget(QWidget())
        for index, (value, label) in enumerate((("current", "Current page"), ("selected", "Selected pages"), ("all", "All pages"))):
            radio = QRadioButton(label)
            radio.setProperty("scope", value)
            self.scope_group.addButton(radio, index)
            radio.toggled.connect(lambda checked, i=index: self.scope_stack.setCurrentIndex(i) if checked else None)
            layout.addWidget(radio)
        self.scope_group.button(0).setChecked(True)
        layout.addWidget(self.scope_stack)

        self.preview_note = QLabel("")
        self.preview_note.setProperty("class", "MutedLabel")
        layout.addWidget(self.preview_note)
        self.preview = _CropPreview()
        layout.addWidget(self.preview, 1)
        process = QPushButton("Crop PDF")
        process.setProperty("class", "Primary")
        process.clicked.connect(self._start_crop)
        layout.addWidget(process, alignment=Qt.AlignmentFlag.AlignRight)
        return w

    def _replace_picker(self) -> None:
        while self.selected_layout.count():
            item = self.selected_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.page_picker = PagePickerWidget(self._page_count)
        self.selected_layout.addWidget(self.page_picker)

    def _scope(self) -> list[int] | None:
        value = self.scope_group.checkedButton().property("scope")
        if value == "all":
            return None
        if value == "current":
            return [self.current_page.value() - 1]
        if self.page_picker is None or not self.page_picker.selected_indices():
            raise FileValidationError("Select at least one page.")
        return self.page_picker.selected_indices()

    def _margins(self) -> CropMargins:
        return CropMargins(**{name: spin.value() for name, spin in self.margin_spins.items()})

    def _update_preview(self) -> None:
        if self._source is None or not pdf_engine.FITZ_AVAILABLE:
            if hasattr(self, "preview_note"):
                self.preview_note.setText("Live preview requires PyMuPDF." if not pdf_engine.FITZ_AVAILABLE else "Select a PDF to preview.")
            if hasattr(self, "preview"):
                self.preview.clear_preview()
            return
        try:
            page_index = self.current_page.value() - 1
            margins = self._margins()
            box = preview_cropbox(self._source, page_index, margins)
            renderer = PageRenderer(self._source)
            data = renderer.render_page_png(page_index)
            size = renderer.page_size(page_index)
            renderer.close()
            self.preview.set_preview(data, box, size)
            self.preview_note.setText("Previewing the current page.")
        except FileValidationError as exc:
            self.preview.clear_preview()
            self.preview_note.setText(exc.message)

    def _start_crop(self) -> None:
        if self._source is None:
            show_toast(self.window(), "Select a PDF first.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.crop_worker import CropWorker

        output = unique_output_path(Path(AppConfig.load().default_output_folder) / "cropped.pdf")
        return CropWorker(self._source, self._margins(), output, self._scope())

    def _input_summary(self) -> str:
        return self._source.name if self._source else ""

    def _on_reset(self) -> None:
        self._source = None
        self._page_count = 0
        if hasattr(self, "source_label"):
            self.source_label.setText("No file selected")
        if hasattr(self, "preview"):
            self.preview.clear_preview()
