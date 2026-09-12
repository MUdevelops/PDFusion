"""Reusable card widgets for the Dashboard and All Tools pages."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor


def _apply_card_shadow(widget: QFrame) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(24)
    shadow.setXOffset(0)
    shadow.setYOffset(6)
    shadow.setColor(QColor(0, 0, 0, 60))
    widget.setGraphicsEffect(shadow)


class QuickActionCard(QFrame):
    """Clickable card for a single tool (Merge, Split, Compress, ...)."""

    clicked = Signal(str)  # emits tool_id

    def __init__(self, tool_id: str, label: str, icon_glyph: str = "📄", parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.setProperty("class", "Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(148, 108)
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel(icon_glyph)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 26px; background: transparent; border: none;")

        text = QLabel(label)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("font-weight: 600; background: transparent; border: none;")

        layout.addWidget(icon)
        layout.addWidget(text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.clicked.emit(self.tool_id)


class StatCard(QFrame):
    """Small dashboard stat block, e.g. 'Files processed: 128'."""

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setMinimumHeight(88)
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 700; background: transparent; border: none;")
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "MutedLabel")
        self.title_label.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class RecentFileRow(QFrame):
    """A single row in the 'Recent Files' list."""

    openRequested = Signal(str)
    removeRequested = Signal(str)

    def __init__(self, file_name: str, meta_text: str, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setProperty("class", "Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 20px; background: transparent; border: none;")

        text_col = QVBoxLayout()
        name_label = QLabel(file_name)
        name_label.setStyleSheet("font-weight: 600; background: transparent; border: none;")
        meta_label = QLabel(meta_text)
        meta_label.setProperty("class", "MutedLabel")
        meta_label.setStyleSheet("background: transparent; border: none;")
        text_col.addWidget(name_label)
        text_col.addWidget(meta_label)

        layout.addWidget(icon)
        layout.addLayout(text_col)
        layout.addStretch()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.openRequested.emit(self.file_path)
