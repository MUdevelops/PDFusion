"""Split PDF — one source file, six split modes."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QButtonGroup, QSpinBox, QLineEdit, QFileDialog, QStackedWidget,
)

from app.config import AppConfig
from app.constants import ToolId
from app.core.pdf_engine import page_count_only
from app.ui.tools.common import ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError
from app.utils.validators import PDF_SUFFIXES, parse_page_range

from app.workers.split_worker import (
    MODE_RANGE, MODE_EVERY_N, MODE_RANGES, MODE_ODD, MODE_EVEN, MODE_SINGLE_PAGES,
)


class SplitPage(ToolPageBase):
    def __init__(self, parent=None):
        self._source: Path | None = None
        self._page_count = 0
        super().__init__(ToolId.SPLIT, "Split PDF", parent)

    # -- Select -------------------------------------------------------------
    def _build_select_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop = DropZone(
            title="Drop a PDF here",
            subtitle="or click Browse to select a file",
            accepted_suffixes=PDF_SUFFIXES,
            allow_multiple=False,
        )
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
        self.range_end_spin.setMaximum(self._page_count)
        self.range_end_spin.setValue(self._page_count)
        self.range_start_spin.setMaximum(self._page_count)
        self.go_to_configure()

    # -- Configure --------------------------------------------------------
    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.source_label = QLabel("No file selected")
        self.source_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.source_label)

        self._mode_group = QButtonGroup(self)
        self._mode_stack = QStackedWidget()
        self._radio_buttons: dict[str, QRadioButton] = {}

        self._add_mode(layout, MODE_RANGE, "Extract a page range", self._build_range_panel())
        self._add_mode(layout, MODE_EVERY_N, "Split every N pages", self._build_every_n_panel())
        self._add_mode(layout, MODE_RANGES, "Split by explicit ranges (e.g. 1-3,4-6,7-10)", self._build_ranges_panel())
        self._add_mode(layout, MODE_ODD, "Extract odd pages", QWidget())
        self._add_mode(layout, MODE_EVEN, "Extract even pages", QWidget())
        self._add_mode(layout, MODE_SINGLE_PAGES, "Split into one PDF per page", QWidget())

        layout.addWidget(self._mode_stack)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output name prefix:"))
        self.base_name_edit = QLineEdit("split")
        out_row.addWidget(self.base_name_edit, 1)
        browse_out_btn = QPushButton("Choose Folder…")
        browse_out_btn.setProperty("class", "Secondary")
        browse_out_btn.clicked.connect(self._browse_output_folder)
        out_row.addWidget(browse_out_btn)
        layout.addLayout(out_row)

        self.output_folder_label = QLabel(self._output_folder_text())
        self.output_folder_label.setProperty("class", "MutedLabel")
        layout.addWidget(self.output_folder_label)

        split_btn = QPushButton("Split PDF")
        split_btn.setProperty("class", "Primary")
        split_btn.clicked.connect(self._start_split)
        layout.addWidget(split_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._output_dir = Path(AppConfig.load().default_output_folder)
        self._radio_buttons[MODE_RANGE].setChecked(True)
        return w

    def _add_mode(self, layout, mode_id: str, label: str, panel: QWidget) -> None:
        radio = QRadioButton(label)
        self._mode_group.addButton(radio)
        self._radio_buttons[mode_id] = radio
        index = self._mode_stack.count()
        radio.toggled.connect(lambda checked, i=index: self._mode_stack.setCurrentIndex(i) if checked else None)
        layout.addWidget(radio)
        self._mode_stack.addWidget(panel)

    def _build_range_panel(self) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.addWidget(QLabel("From page"))
        self.range_start_spin = QSpinBox()
        self.range_start_spin.setMinimum(1)
        row.addWidget(self.range_start_spin)
        row.addWidget(QLabel("to"))
        self.range_end_spin = QSpinBox()
        self.range_end_spin.setMinimum(1)
        row.addWidget(self.range_end_spin)
        row.addStretch()
        return panel

    def _build_every_n_panel(self) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.addWidget(QLabel("Pages per file:"))
        self.every_n_spin = QSpinBox()
        self.every_n_spin.setMinimum(1)
        self.every_n_spin.setMaximum(9999)
        self.every_n_spin.setValue(1)
        row.addWidget(self.every_n_spin)
        row.addStretch()
        return panel

    def _build_ranges_panel(self) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.addWidget(QLabel("Ranges:"))
        self.ranges_edit = QLineEdit()
        self.ranges_edit.setPlaceholderText("e.g. 1-3,4-6,7-10")
        row.addWidget(self.ranges_edit, 1)
        return panel

    def _output_folder_text(self) -> str:
        cfg = AppConfig.load()
        return f"Saving to: {cfg.default_output_folder}"

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self._output_dir))
        if folder:
            self._output_dir = Path(folder)
            self.output_folder_label.setText(f"Saving to: {folder}")

    def _current_mode(self) -> str:
        for mode_id, radio in self._radio_buttons.items():
            if radio.isChecked():
                return mode_id
        return MODE_RANGE

    def _parse_ranges_text(self) -> list[tuple[int, int]]:
        text = self.ranges_edit.text().strip()
        if not text:
            raise FileValidationError("Enter at least one range, e.g. 1-3,4-6.")
        result = []
        for chunk in text.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "-" not in chunk:
                raise FileValidationError(f"'{chunk}' is not a range like '1-3'.")
            a, b = chunk.split("-", 1)
            try:
                result.append((int(a), int(b)))
            except ValueError as exc:
                raise FileValidationError(f"'{chunk}' is not a valid range.") from exc
        return result

    # -- processing -----------------------------------------------------
    def _start_split(self) -> None:
        if self._source is None:
            show_toast(self.window(), "Select a PDF first.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.split_worker import SplitWorker

        mode = self._current_mode()
        base_name = self.base_name_edit.text().strip() or "split"
        kwargs = {}
        if mode == MODE_RANGE:
            kwargs["range_start"] = self.range_start_spin.value()
            kwargs["range_end"] = self.range_end_spin.value()
        elif mode == MODE_EVERY_N:
            kwargs["every_n"] = self.every_n_spin.value()
        elif mode == MODE_RANGES:
            kwargs["ranges"] = self._parse_ranges_text()

        return SplitWorker(self._source, mode, self._output_dir, base_name, **kwargs)

    def _input_summary(self) -> str:
        return self._source.name if self._source else ""

    def _on_reset(self) -> None:
        self._source = None
        self._page_count = 0
        if hasattr(self, "source_label"):
            self.source_label.setText("No file selected")
        if hasattr(self, "base_name_edit"):
            self.base_name_edit.setText("split")
        if hasattr(self, "ranges_edit"):
            self.ranges_edit.clear()
        self._output_dir = Path(AppConfig.load().default_output_folder)
        if hasattr(self, "output_folder_label"):
            self.output_folder_label.setText(self._output_folder_text())
