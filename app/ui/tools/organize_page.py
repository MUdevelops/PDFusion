"""Staged single-document PDF organizer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
    QAbstractItemView, QInputDialog,
)

from app.config import AppConfig
from app.constants import ToolId
from app.core.organizer import OrganizeSession
from app.core.pdf_engine import page_count_only
from app.ui.tools.common import ToolPageBase
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.toast import show_toast
from app.utils.errors import FileValidationError, PDFusionError
from app.utils.file_utils import unique_output_path
from app.utils.validators import PDF_SUFFIXES, parse_page_range


class _SourcePagesDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._path: Path | None = None
        self._count = 0
        layout = QVBoxLayout(self)
        self.path_label = QLabel("No PDF selected")
        browse = QPushButton("Choose PDF…")
        browse.clicked.connect(self._browse)
        layout.addWidget(self.path_label)
        layout.addWidget(browse)
        self.form = QFormLayout()
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("e.g. 1-3,5")
        self.form.addRow("Pages:", self.range_edit)
        layout.addLayout(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        raw, _ = QFileDialog.getOpenFileName(self, "Choose source PDF", "", "PDF Files (*.pdf)")
        if not raw:
            return
        try:
            self._path = Path(raw)
            self._count = page_count_only(self._path)
        except FileValidationError as exc:
            show_toast(self, exc.message, kind="error")
            return
        self.path_label.setText(f"{self._path.name}  •  {self._count} pages")
        self.range_edit.setPlaceholderText(f"e.g. 1-3 (1-{self._count})")

    def source(self) -> Path | None:
        return self._path

    def page_range(self) -> list[int]:
        if self._path is None:
            raise FileValidationError("Choose a source PDF first.")
        return parse_page_range(self.range_edit.text(), self._count)


class OrganizePage(ToolPageBase):
    def __init__(self, parent=None):
        self._source: Path | None = None
        self._session: OrganizeSession | None = None
        super().__init__(ToolId.ORGANIZE, "Organize PDF", parent)

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
        try:
            session = OrganizeSession(Path(paths[0]))
        except PDFusionError as exc:
            show_toast(self.window(), exc.message, kind="error")
            return
        self._source = Path(paths[0])
        self._session = session
        self.source_label.setText(f"{self._source.name}  •  {len(session.pages)} pages")
        self._refresh_list()
        self.go_to_configure()

    def _build_configure_step(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.source_label = QLabel("No file selected")
        self.source_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.source_label)
        hint = QLabel("Drag pages to reorder. All changes stay staged until Save.")
        hint.setProperty("class", "MutedLabel")
        layout.addWidget(hint)
        self.page_list = QListWidget()
        self.page_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.page_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.page_list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.page_list, 1)

        actions = QHBoxLayout()
        for label, handler in (("Delete", self._delete), ("Duplicate", self._duplicate), ("Rotate", self._rotate), ("Insert Pages From File…", self._insert), ("Replace Page…", self._replace), ("Keep Only Selected", self._keep_only)):
            button = QPushButton(label)
            button.setProperty("class", "Secondary")
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)
        save = QPushButton("Save Organized PDF")
        save.setProperty("class", "Primary")
        save.clicked.connect(self._start_save)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)
        return w

    def _refresh_list(self) -> None:
        self.page_list.clear()
        if self._session is None:
            return
        for index, ref in enumerate(self._session.pages):
            item = QListWidgetItem(f"Page {index + 1}  •  {ref.rotation}\u00b0")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.page_list.addItem(item)

    def _on_rows_moved(self, *_args) -> None:
        if self._session is None:
            return
        old_pages = list(self._session.pages)
        ordered = []
        for row in range(self.page_list.count()):
            old_index = self.page_list.item(row).data(Qt.ItemDataRole.UserRole)
            ordered.append(old_pages[old_index])
        self._session.pages = ordered
        self._refresh_list()

    def _selected_indices(self) -> list[int]:
        return sorted((self.page_list.row(item) for item in self.page_list.selectedItems()))

    def _delete(self) -> None:
        if self._session is None:
            return
        try:
            indices = self._selected_indices()
            if not indices:
                raise FileValidationError("Select at least one page.")
            self._session.delete_many(indices)
            self._refresh_list()
        except FileValidationError as exc:
            show_toast(self.window(), exc.message, kind="error")

    def _duplicate(self) -> None:
        if self._session is None:
            return
        indices = self._selected_indices()
        if len(indices) != 1:
            show_toast(self.window(), "Select one page to duplicate.", kind="warning")
            return
        self._session.duplicate(indices[0])
        self._refresh_list()

    def _rotate(self) -> None:
        if self._session is None:
            return
        indices = self._selected_indices()
        if not indices:
            show_toast(self.window(), "Select at least one page.", kind="warning")
            return
        angle, ok = QInputDialog.getItem(self, "Rotate pages", "Add rotation:", ["90\u00b0", "180\u00b0", "270\u00b0"], 0, False)
        if ok:
            self._session.rotate_many(indices, int(angle.rstrip("\u00b0")))
            self._refresh_list()

    def _insert(self) -> None:
        if self._session is None:
            return
        dialog = _SourcePagesDialog("Insert pages", self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            indices = dialog.page_range()
            position, ok = QInputDialog.getInt(self, "Insert position", "Insert before page (or end + 1):", 1, 1, len(self._session.pages) + 1)
            if not ok:
                return
            self._session.insert_from(dialog.source(), indices, position - 1)
            self._refresh_list()
        except FileValidationError as exc:
            show_toast(self.window(), exc.message, kind="error")

    def _replace(self) -> None:
        if self._session is None:
            return
        selected = self._selected_indices()
        if len(selected) != 1:
            show_toast(self.window(), "Select one page to replace.", kind="warning")
            return
        dialog = _SourcePagesDialog("Replace page", self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            indices = dialog.page_range()
            if len(indices) != 1:
                raise FileValidationError("Choose exactly one replacement page.")
            self._session.replace(selected[0], dialog.source(), indices[0])
            self._refresh_list()
        except FileValidationError as exc:
            show_toast(self.window(), exc.message, kind="error")

    def _keep_only(self) -> None:
        if self._session is None:
            return
        try:
            self._session.keep_only(self._selected_indices())
            self._refresh_list()
        except FileValidationError as exc:
            show_toast(self.window(), exc.message, kind="error")

    def _start_save(self) -> None:
        if self._session is None:
            show_toast(self.window(), "Select a PDF first.", kind="warning")
            return
        self.start_processing()

    def _make_worker(self):
        from app.workers.organize_worker import OrganizeWorker

        output = unique_output_path(Path(AppConfig.load().default_output_folder) / "organized.pdf")
        return OrganizeWorker(self._session, output)

    def _input_summary(self) -> str:
        return self._source.name if self._source else ""

    def _on_reset(self) -> None:
        if self._session is not None:
            self._session.close()
        self._source = None
        self._session = None
        if hasattr(self, "source_label"):
            self.source_label.setText("No file selected")
        if hasattr(self, "page_list"):
            self.page_list.clear()
