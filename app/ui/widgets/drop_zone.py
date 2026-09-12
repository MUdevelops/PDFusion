"""A reusable drag & drop target used on the Dashboard and inside every
tool screen (Merge, Split, Image-to-PDF, OCR, Compress, ...).

Emits ``filesDropped(list[str])`` with absolute paths. Filtering by
extension is the caller's job (pass ``accepted_suffixes``).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QFileDialog


class DropZone(QFrame):
    filesDropped = Signal(list)

    def __init__(
        self,
        title: str = "Drop files here",
        subtitle: str = "or click Browse to select files",
        accepted_suffixes: set[str] | None = None,
        allow_multiple: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setProperty("dragActive", False)
        self.setAcceptDrops(True)
        self.accepted_suffixes = accepted_suffixes
        self.allow_multiple = allow_multiple

        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.icon_label = QLabel("📄")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 40px;")

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setProperty("class", "SectionLabel")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setProperty("class", "MutedLabel")

        self.browse_button = QPushButton("Browse Files")
        self.browse_button.setProperty("class", "Primary")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.setFixedWidth(160)
        self.browse_button.clicked.connect(self._browse)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)

    # -- drag & drop ---------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._set_active(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_active(False)
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        paths = self._filter(paths)
        if paths:
            self.filesDropped.emit([str(p) for p in paths])
        event.acceptProposedAction()

    def _set_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _filter(self, paths: list[Path]) -> list[Path]:
        if self.accepted_suffixes:
            paths = [p for p in paths if p.suffix.lower() in self.accepted_suffixes]
        if not self.allow_multiple:
            paths = paths[:1]
        return paths

    # -- browse dialog ---------------------------------------------------
    def _browse(self) -> None:
        name_filter = "All Files (*)"
        if self.accepted_suffixes:
            exts = " ".join(f"*{s}" for s in sorted(self.accepted_suffixes))
            name_filter = f"Supported Files ({exts})"

        if self.allow_multiple:
            files, _ = QFileDialog.getOpenFileNames(self, "Select files", "", name_filter)
        else:
            single, _ = QFileDialog.getOpenFileName(self, "Select file", "", name_filter)
            files = [single] if single else []

        files = [f for f in files if f]
        if files:
            self.filesDropped.emit(files)
