"""Extract an explicit page range from a single PDF."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.config import AppConfig
from app.constants import ToolId
from app.core.pdf_engine import page_count_only
from app.ui.tools.common import ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError
from app.utils.file_utils import unique_output_path
from app.utils.validators import PDF_SUFFIXES, parse_page_range


class ExtractPage(ToolPageBase):
    def __init__(self, parent=None):
        self._source: Path | None = None
        self._page_count = 0
        super().__init__(ToolId.EXTRACT, "Extract Pages", parent)

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
        self.range_edit.setPlaceholderText(f"e.g. 1-3,5 (1-{self._page_count})")
        self.go_to_configure()

    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.source_label = QLabel("No file selected")
        self.source_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.source_label)
        layout.addWidget(QLabel("Pages to extract (for example, 1-3,5):"))
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("e.g. 1-3,5")
        layout.addWidget(self.range_edit)
        process = QPushButton("Extract Pages")
        process.setProperty("class", "Primary")
        process.clicked.connect(self._start_extract)
        layout.addWidget(process, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()
        return w

    def _start_extract(self) -> None:
        if self._source is None:
            show_toast(self.window(), "Select a PDF first.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.extract_worker import ExtractWorker

        indices = parse_page_range(self.range_edit.text(), self._page_count)
        output = unique_output_path(Path(AppConfig.load().default_output_folder) / "extracted.pdf")
        return ExtractWorker(self._source, indices, output)

    def _input_summary(self) -> str:
        return self._source.name if self._source else ""

    def _on_reset(self) -> None:
        self._source = None
        self._page_count = 0
        if hasattr(self, "source_label"):
            self.source_label.setText("No file selected")
        if hasattr(self, "range_edit"):
            self.range_edit.clear()
