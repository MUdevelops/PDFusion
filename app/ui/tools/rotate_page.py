"""Rotate a single PDF with an explicit page scope."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QRadioButton, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget, QPushButton,
)

from app.config import AppConfig
from app.constants import ToolId
from app.core.pdf_engine import page_count_only
from app.ui.tools.common import PagePickerWidget, ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError
from app.utils.file_utils import unique_output_path
from app.utils.validators import PDF_SUFFIXES


class RotatePage(ToolPageBase):
    def __init__(self, parent=None):
        self._source: Path | None = None
        self._page_count = 0
        super().__init__(ToolId.ROTATE, "Rotate PDF", parent)

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
        self.go_to_configure()

    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.source_label = QLabel("No file selected")
        self.source_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.source_label)
        layout.addWidget(QLabel("Scope"))
        self.scope_group = QButtonGroup(self)
        self.scope_stack = QStackedWidget()
        self.current_panel = QWidget()
        current_row = QHBoxLayout(self.current_panel)
        current_row.addWidget(QLabel("Current page:"))
        self.current_page = QSpinBox()
        self.current_page.setMinimum(1)
        current_row.addWidget(self.current_page)
        current_row.addStretch()
        self.selected_panel = QWidget()
        self.selected_layout = QVBoxLayout(self.selected_panel)
        self.selected_layout.setContentsMargins(0, 0, 0, 0)
        self.page_picker: PagePickerWidget | None = None
        self.scope_stack.addWidget(self.current_panel)
        self.scope_stack.addWidget(self.selected_panel)
        self.scope_stack.addWidget(QWidget())
        for index, (value, label) in enumerate((("current", "Current page"), ("selected", "Selected pages"), ("all", "All pages"))):
            radio = QRadioButton(label)
            radio.setProperty("scope", value)
            self.scope_group.addButton(radio, index)
            radio.toggled.connect(lambda checked, i=index: self.scope_stack.setCurrentIndex(i) if checked else None)
            layout.addWidget(radio)
        self.scope_group.button(0).setChecked(True)
        layout.addWidget(self.scope_stack)
        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Angle:"))
        self.angle_group = QButtonGroup(self)
        for value in (90, 180, 270):
            radio = QRadioButton(f"{value}\u00b0")
            self.angle_group.addButton(radio, value)
            angle_row.addWidget(radio)
        self.angle_group.button(90).setChecked(True)
        angle_row.addStretch()
        layout.addLayout(angle_row)
        process = QPushButton("Rotate PDF")
        process.setProperty("class", "Primary")
        process.clicked.connect(self._start_rotate)
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

    def _start_rotate(self) -> None:
        if self._source is None:
            show_toast(self.window(), "Select a PDF first.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.rotate_worker import RotateWorker

        output = unique_output_path(Path(AppConfig.load().default_output_folder) / "rotated.pdf")
        return RotateWorker(self._source, self.angle_group.checkedId(), output, self._scope())

    def _input_summary(self) -> str:
        return self._source.name if self._source else ""

    def _on_reset(self) -> None:
        self._source = None
        self._page_count = 0
        if hasattr(self, "source_label"):
            self.source_label.setText("No file selected")
