"""Merge PDF — select multiple files, drag to reorder, remove, rotate
individual pages per file, then merge into one output.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QAbstractItemView, QLineEdit, QFileDialog,
)

from app.config import AppConfig
from app.constants import ToolId
from app.core.merger import MergeItem
from app.core.pdf_engine import page_count_only
from app.ui.dialogs.page_rotate_dialog import PageRotateDialog
from app.ui.tools.common import ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError
from app.utils.file_utils import unique_output_path
from app.utils.validators import PDF_SUFFIXES


class MergePage(ToolPageBase):
    def __init__(self, parent=None):
        self._items: dict[str, MergeItem] = {}  # str(path) -> MergeItem
        super().__init__(ToolId.MERGE, "Merge PDF", parent)

    # -- Select ---------------------------------------------------------
    def _build_select_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop = DropZone(
            title="Drop 2 or more PDFs here",
            subtitle="or click Browse to select files — order is set in the next step",
            accepted_suffixes=PDF_SUFFIXES,
            allow_multiple=True,
        )
        drop.filesDropped.connect(self._add_files)
        layout.addWidget(drop)
        return w

    # -- Configure --------------------------------------------------------
    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        hint = QLabel("Drag rows to reorder. Select a file to remove it or rotate its pages.")
        hint.setProperty("class", "MutedLabel")
        layout.addWidget(hint)

        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.file_list, 1)

        row_actions = QHBoxLayout()
        add_btn = QPushButton("Add More Files")
        add_btn.setProperty("class", "Secondary")
        add_btn.clicked.connect(self._browse_add)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setProperty("class", "Secondary")
        remove_btn.clicked.connect(self._remove_selected)
        rotate_btn = QPushButton("Rotate Pages…")
        rotate_btn.setProperty("class", "Secondary")
        rotate_btn.clicked.connect(self._rotate_selected)
        row_actions.addWidget(add_btn)
        row_actions.addWidget(remove_btn)
        row_actions.addWidget(rotate_btn)
        row_actions.addStretch()
        layout.addLayout(row_actions)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output file:"))
        self.output_name_edit = QLineEdit("merged.pdf")
        out_row.addWidget(self.output_name_edit, 1)
        browse_out_btn = QPushButton("Choose Folder…")
        browse_out_btn.setProperty("class", "Secondary")
        browse_out_btn.clicked.connect(self._browse_output_folder)
        out_row.addWidget(browse_out_btn)
        layout.addLayout(out_row)

        self.output_folder_label = QLabel(self._output_folder_text())
        self.output_folder_label.setProperty("class", "MutedLabel")
        layout.addWidget(self.output_folder_label)

        merge_btn = QPushButton("Merge PDFs")
        merge_btn.setProperty("class", "Primary")
        merge_btn.clicked.connect(self._start_merge)
        layout.addWidget(merge_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._output_dir = Path(AppConfig.load().default_output_folder)
        return w

    def _output_folder_text(self) -> str:
        cfg = AppConfig.load()
        return f"Saving to: {cfg.default_output_folder}"

    # -- file management ------------------------------------------------
    def _add_files(self, paths: list[str]) -> None:
        added = 0
        for raw in paths:
            path = Path(raw)
            key = str(path)
            if key in self._items:
                continue
            try:
                count = page_count_only(path)
            except FileValidationError as exc:
                show_toast(self.window(), exc.message, kind="error")
                continue
            self._items[key] = MergeItem(path)
            item = QListWidgetItem(f"{path.name}  •  {count} page(s)")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.file_list.addItem(item)
            added += 1
        if added:
            self.go_to_configure()

    def _browse_add(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Add PDFs", "", "PDF Files (*.pdf)")
        if files:
            self._add_files(files)

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            key = item.data(Qt.ItemDataRole.UserRole)
            self._items.pop(key, None)
            self.file_list.takeItem(self.file_list.row(item))

    def _rotate_selected(self) -> None:
        selected = self.file_list.selectedItems()
        if not selected:
            show_toast(self.window(), "Select a file first.", kind="info")
            return
        item = selected[0]
        key = item.data(Qt.ItemDataRole.UserRole)
        merge_item = self._items[key]
        dialog = PageRotateDialog(merge_item.path, merge_item.page_rotations, self)
        if dialog.exec():
            merge_item.page_rotations = dialog.rotations()

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self._output_dir))
        if folder:
            self._output_dir = Path(folder)
            self.output_folder_label.setText(f"Saving to: {folder}")

    # -- processing -----------------------------------------------------
    def _ordered_items(self) -> list[MergeItem]:
        ordered = []
        for i in range(self.file_list.count()):
            key = self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            ordered.append(self._items[key])
        return ordered

    def _start_merge(self) -> None:
        if self.file_list.count() < 2:
            show_toast(self.window(), "Add at least two PDFs to merge.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.merge_worker import MergeWorker

        name = self.output_name_edit.text().strip() or "merged.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        output_path = unique_output_path(self._output_dir / name)
        return MergeWorker(self._ordered_items(), output_path)

    def _input_summary(self) -> str:
        return f"{self.file_list.count()} file(s)"

    def _on_reset(self) -> None:
        self._items.clear()
        if hasattr(self, "file_list"):
            self.file_list.clear()
        if hasattr(self, "output_name_edit"):
            self.output_name_edit.setText("merged.pdf")
        self._output_dir = Path(AppConfig.load().default_output_folder)
        if hasattr(self, "output_folder_label"):
            self.output_folder_label.setText(self._output_folder_text())
