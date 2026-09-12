"""Built-in PDF viewer: thumbnail rail + main page view, zoom, and
page navigation. Renders on demand via PageRenderer (PyMuPDF) with
caching, never the whole document at once.

If PyMuPDF isn't installed, shows a clear dependency notice instead of
crashing (spec section 31).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QScrollArea, QPushButton, QSpinBox, QSizePolicy,
)

from app.core.pdf_engine import FITZ_AVAILABLE
from app.utils.errors import PDFusionError
from app.utils.logger import get_logger

logger = get_logger(__name__)

if FITZ_AVAILABLE:
    from app.core.renderer import PageRenderer

THUMB_SIZE = 130


class PdfViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer: "PageRenderer | None" = None
        self._current_page = 0
        self._zoom = 1.5

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        if not FITZ_AVAILABLE:
            notice = QLabel(
                "📄  Page preview requires PyMuPDF.\n\n"
                "Install it with:  pip install PyMuPDF\n"
                "then reopen this file."
            )
            notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
            notice.setProperty("class", "MutedLabel")
            root.addWidget(notice)
            return

        body = QHBoxLayout()
        root.addLayout(body, 1)

        # Thumbnail rail
        self.thumb_list = QListWidget()
        self.thumb_list.setFixedWidth(THUMB_SIZE + 40)
        self.thumb_list.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.thumb_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.thumb_list.currentRowChanged.connect(self._on_thumb_selected)
        body.addWidget(self.thumb_list)

        # Main page view
        main_col = QVBoxLayout()
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_scroll.setWidget(self.page_label)
        main_col.addWidget(self.page_scroll, 1)

        controls = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.setProperty("class", "Secondary")
        self.prev_btn.clicked.connect(self.previous_page)
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        self.page_count_label = QLabel("/ 0")
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setProperty("class", "Secondary")
        self.next_btn.clicked.connect(self.next_page)

        zoom_out = QPushButton("−")
        zoom_out.setFixedWidth(32)
        zoom_out.clicked.connect(lambda: self.set_zoom(self._zoom - 0.25))
        zoom_in = QPushButton("+")
        zoom_in.setFixedWidth(32)
        zoom_in.clicked.connect(lambda: self.set_zoom(self._zoom + 0.25))

        controls.addWidget(self.prev_btn)
        controls.addWidget(self.page_spin)
        controls.addWidget(self.page_count_label)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        controls.addWidget(zoom_out)
        controls.addWidget(zoom_in)
        main_col.addLayout(controls)

        body.addLayout(main_col, 1)

    def load(self, path: str | Path) -> None:
        if not FITZ_AVAILABLE:
            return
        try:
            if self._renderer:
                self._renderer.close()
            self._renderer = PageRenderer(Path(path))
        except PDFusionError as exc:
            logger.warning("PDF viewer failed to open %s: %s", path, exc.message)
            self.page_label.setText(exc.message)
            return

        self.thumb_list.clear()
        for i in range(self._renderer.page_count):
            item = QListWidgetItem(f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.thumb_list.addItem(item)

        self.page_spin.setMaximum(max(1, self._renderer.page_count))
        self.page_count_label.setText(f"/ {self._renderer.page_count}")
        self._load_thumbnails()
        self.show_page(0)

    def _load_thumbnails(self) -> None:
        if not self._renderer:
            return
        for i in range(self.thumb_list.count()):
            png_bytes = self._renderer.render_thumbnail_png(i, max_dim=THUMB_SIZE)
            pixmap = QPixmap()
            pixmap.loadFromData(png_bytes, "PNG")
            self.thumb_list.item(i).setIcon(pixmap)

    def show_page(self, index: int) -> None:
        if not self._renderer or not (0 <= index < self._renderer.page_count):
            return
        self._current_page = index
        png_bytes = self._renderer.render_page_png(index, zoom=self._zoom)
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes, "PNG")
        self.page_label.setPixmap(pixmap)

        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(index)
        self.thumb_list.blockSignals(False)

        self.page_spin.blockSignals(True)
        self.page_spin.setValue(index + 1)
        self.page_spin.blockSignals(False)

    def next_page(self) -> None:
        self.show_page(self._current_page + 1)

    def previous_page(self) -> None:
        self.show_page(self._current_page - 1)

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.25, min(4.0, zoom))
        self.show_page(self._current_page)

    def _on_thumb_selected(self, row: int) -> None:
        if row >= 0:
            self.show_page(row)

    def _on_page_spin_changed(self, value: int) -> None:
        self.show_page(value - 1)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._renderer:
            self._renderer.close()
        super().closeEvent(event)
