"""Shared building blocks for tool screens.

Every Organize tool follows the same shape: Select -> Configure ->
(Preview, where applicable) -> Process -> Results. ``ToolPageBase``
implements the parts that don't vary — the QStackedWidget of steps,
a progress panel with a real Cancel button wired to the worker, a
results panel with Open / Open Folder / Do Another, and logging the
run to Processing History (spec section: "every operation is logged").

Subclasses only need to build their own Select/Configure widgets and
supply a factory that creates the ``PdfWorker`` for the current
configuration.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QStackedWidget, QListWidget, QListWidgetItem, QCheckBox, QScrollArea,
    QFrame,
)

from app.database.repositories import HistoryRepository, RecentFilesRepository
from app.ui.dialogs.error_dialog import show_error
from app.ui.widgets.toast import show_toast
from app.utils.logger import get_logger
from app.workers.pdf_worker import PdfWorker

logger = get_logger(__name__)

STEP_SELECT = 0
STEP_CONFIGURE = 1
STEP_PROGRESS = 2
STEP_RESULTS = 3


class StepHeader(QWidget):
    """A tiny '1 Select -> 2 Configure -> 3 Process -> 4 Results' breadcrumb."""

    _LABELS = ["Select", "Configure", "Process", "Results"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._dots: list[QLabel] = []
        for i, label in enumerate(self._LABELS):
            dot = QLabel(f"{i + 1}. {label}")
            dot.setProperty("class", "MutedLabel")
            layout.addWidget(dot)
            self._dots.append(dot)
            if i < len(self._LABELS) - 1:
                arrow = QLabel("›")
                arrow.setProperty("class", "MutedLabel")
                layout.addWidget(arrow)
        layout.addStretch()

    def set_active(self, step_index: int) -> None:
        # STEP_PROGRESS and STEP_RESULTS both map onto breadcrumb slots 3/4.
        mapped = min(step_index, len(self._dots) - 1)
        for i, dot in enumerate(self._dots):
            dot.setStyleSheet("font-weight: 700;" if i == mapped else "")


class ProgressPanel(QWidget):
    """Progress bar + status text + Cancel, wired to a running ``PdfWorker``."""

    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        self.title_label = QLabel("Processing…")
        self.title_label.setProperty("class", "SectionLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setFixedWidth(360)

        self.status_label = QLabel("")
        self.status_label.setProperty("class", "MutedLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedWidth(360)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "Secondary")
        self.cancel_btn.clicked.connect(self.cancelled.emit)

        layout.addWidget(self.title_label)
        layout.addWidget(self.bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def reset(self, title: str = "Processing…") -> None:
        self.title_label.setText(title)
        self.bar.setValue(0)
        self.status_label.setText("")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Cancel")

    def update_progress(self, percent: int, message: str) -> None:
        self.bar.setValue(percent)
        if message:
            self.status_label.setText(message)

    def set_cancelling(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling…")


class ResultsPanel(QWidget):
    """Success/failure/cancelled summary with Open / Open Folder / Do Another."""

    openRequested = Signal(str)
    openFolderRequested = Signal(str)
    doAnotherRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_paths: list[Path] = []

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self.icon_label = QLabel("✅")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 40px;")

        self.message_label = QLabel("")
        self.message_label.setProperty("class", "SectionLabel")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFixedWidth(420)

        self.file_list = QListWidget()
        self.file_list.setFixedHeight(120)
        self.file_list.setFixedWidth(420)
        self.file_list.setVisible(False)

        button_row = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.setProperty("class", "Primary")
        self.open_btn.clicked.connect(self._open_first)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setProperty("class", "Secondary")
        self.open_folder_btn.clicked.connect(self._open_folder)

        self.do_another_btn = QPushButton("Do Another")
        self.do_another_btn.setProperty("class", "Secondary")
        self.do_another_btn.clicked.connect(self.doAnotherRequested.emit)

        button_row.addWidget(self.open_btn)
        button_row.addWidget(self.open_folder_btn)
        button_row.addWidget(self.do_another_btn)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label)
        layout.addWidget(self.file_list, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(button_row)

    def show_success(self, message: str, output_paths: list[Path]) -> None:
        self._output_paths = output_paths
        self.icon_label.setText("✅")
        self.message_label.setText(message)
        self.open_btn.setEnabled(bool(output_paths))
        self.open_folder_btn.setEnabled(bool(output_paths))

        self.file_list.clear()
        if len(output_paths) > 1:
            self.file_list.setVisible(True)
            for p in output_paths:
                self.file_list.addItem(QListWidgetItem(p.name))
        else:
            self.file_list.setVisible(False)

    def show_failure(self, message: str) -> None:
        self._output_paths = []
        self.icon_label.setText("⚠")
        self.message_label.setText(message)
        self.file_list.setVisible(False)
        self.open_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

    def show_cancelled(self) -> None:
        self._output_paths = []
        self.icon_label.setText("⏹")
        self.message_label.setText("Cancelled — no output file was written.")
        self.file_list.setVisible(False)
        self.open_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

    def _open_first(self) -> None:
        if self._output_paths:
            self.openRequested.emit(str(self._output_paths[0]))

    def _open_folder(self) -> None:
        if self._output_paths:
            self.openFolderRequested.emit(str(self._output_paths[0]))


class PagePickerWidget(QWidget):
    """Checkable list of pages ('Page 1', 'Page 2', ...) used to build a
    scope (single / selected / all pages) for Rotate and Crop."""

    def __init__(self, page_count: int, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        controls = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.setProperty("class", "Secondary")
        select_all_btn.clicked.connect(lambda: self._set_all(True))
        select_none_btn = QPushButton("Select None")
        select_none_btn.setProperty("class", "Secondary")
        select_none_btn.clicked.connect(lambda: self._set_all(False))
        controls.addWidget(select_all_btn)
        controls.addWidget(select_none_btn)
        controls.addStretch()
        layout.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(160)
        content = QWidget()
        self._checks_layout = QVBoxLayout(content)
        self._checks_layout.setSpacing(2)
        self._checkboxes: list[QCheckBox] = []
        for i in range(page_count):
            cb = QCheckBox(f"Page {i + 1}")
            self._checks_layout.addWidget(cb)
            self._checkboxes.append(cb)
        self._checks_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _set_all(self, checked: bool) -> None:
        for cb in self._checkboxes:
            cb.setChecked(checked)

    def selected_indices(self) -> list[int]:
        return [i for i, cb in enumerate(self._checkboxes) if cb.isChecked()]


def open_path(path: str) -> None:
    """Open a file or folder with the OS default handler."""
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        logger.warning("Could not open %s with the OS file handler", path)


class ToolPageBase(QWidget):
    """Base class for a single-tool screen with the Select -> Configure ->
    Process -> Results flow, a running-worker guard, and History logging.
    """

    def __init__(self, tool_id: str, tool_label: str, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_label = tool_label
        self._recent_repo = RecentFilesRepository()
        self._history_repo = HistoryRepository()
        self._history_entry_id: int | None = None
        self._start_time = 0.0
        self._worker: PdfWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(tool_label)
        title.setProperty("class", "TitleLabel")
        header.addWidget(title)
        header.addStretch()
        self.step_header = StepHeader()
        header.addWidget(self.step_header)
        root.addLayout(header)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.select_widget = self._build_select_step()
        self.configure_widget = self._build_configure_step()
        self.progress_panel = ProgressPanel()
        self.progress_panel.cancelled.connect(self._cancel_worker)
        self.results_panel = ResultsPanel()
        self.results_panel.openRequested.connect(open_path)
        self.results_panel.openFolderRequested.connect(self._open_containing_folder)
        self.results_panel.doAnotherRequested.connect(self.reset)

        self.stack.addWidget(self.select_widget)
        self.stack.addWidget(self.configure_widget)
        self.stack.addWidget(self.progress_panel)
        self.stack.addWidget(self.results_panel)

        self.reset()

    # -- subclass hooks ---------------------------------------------------
    def _build_select_step(self) -> QWidget:
        raise NotImplementedError

    def _build_configure_step(self) -> QWidget:
        raise NotImplementedError

    def _make_worker(self) -> PdfWorker:
        """Build and return the worker for the current configuration."""
        raise NotImplementedError

    def _input_summary(self) -> str:
        return ""

    def _on_reset(self) -> None:
        """Subclass hook: clear per-run selections when starting over."""

    # -- flow ---------------------------------------------------------------
    def reset(self) -> None:
        self._on_reset()
        self._goto(STEP_SELECT)

    def _goto(self, step: int) -> None:
        self.stack.setCurrentIndex(step)
        self.step_header.set_active(step)

    def go_to_configure(self) -> None:
        self._goto(STEP_CONFIGURE)

    def go_to_select(self) -> None:
        self._goto(STEP_SELECT)

    def start_processing(self) -> None:
        try:
            worker = self._make_worker()
        except Exception as exc:  # noqa: BLE001 - validation errors surface here
            from app.utils.errors import DocuForgeError

            if isinstance(exc, DocuForgeError):
                show_error(self, exc.message, exc.technical_detail)
            else:
                logger.exception("Failed to build worker for %s", self.tool_id)
                show_error(self, "Unable to start this operation. Please try again.", str(exc))
            return

        self._worker = worker
        self._start_time = time.time()
        self._history_entry_id = self._history_repo.start(
            self.tool_id, self.tool_label, self._input_summary()
        )
        self.progress_panel.reset(f"{self.tool_label}…")
        self._goto(STEP_PROGRESS)

        worker.signals.progress.connect(self.progress_panel.update_progress)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.failed.connect(self._on_failed)
        worker.signals.cancelled.connect(self._on_cancelled)
        worker.start()

    def _cancel_worker(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()
            self.progress_panel.set_cancelling()

    def _finish_history(self, status: str, output_path: str | None, detail: str) -> None:
        if self._history_entry_id is None:
            return
        duration_ms = int((time.time() - self._start_time) * 1000)
        self._history_repo.finish(self._history_entry_id, status, output_path, detail, duration_ms)
        self._history_entry_id = None

    def _as_path_list(self, result) -> list[Path]:
        if isinstance(result, list):
            return [Path(p) for p in result]
        if result is None:
            return []
        return [Path(result)]

    def _on_finished(self, result) -> None:
        paths = self._as_path_list(result)
        for p in paths:
            try:
                from app.core.pdf_engine import page_count_only

                self._recent_repo.touch(p, page_count=page_count_only(p), last_operation=self.tool_label)
            except Exception:  # noqa: BLE001 - best effort, never blocks success UI
                self._recent_repo.touch(p, last_operation=self.tool_label)

        if len(paths) == 1:
            message = f"{self.tool_label} finished — saved to {paths[0].name}."
        else:
            message = f"{self.tool_label} finished — {len(paths)} files created."
        self.results_panel.show_success(message, paths)
        self._finish_history("success", str(paths[0]) if paths else None, message)
        self._goto(STEP_RESULTS)
        self._worker = None

    def _on_failed(self, message: str, technical_detail: str) -> None:
        self.results_panel.show_failure(message)
        self._finish_history("failed", None, message)
        self._goto(STEP_RESULTS)
        show_toast(self.window(), message, kind="error")
        self._worker = None

    def _on_cancelled(self) -> None:
        self.results_panel.show_cancelled()
        self._finish_history("cancelled", None, "Cancelled by user.")
        self._goto(STEP_RESULTS)
        self._worker = None

    def _open_containing_folder(self, file_path: str) -> None:
        open_path(str(Path(file_path).parent))
