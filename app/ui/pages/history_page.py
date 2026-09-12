from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame,
)

from app.database.repositories import HistoryRepository
from app.ui.widgets.empty_state import EmptyState

_STATUS_COLORS = {
    "success": "#2FBF71",
    "failed": "#EF4B5F",
    "cancelled": "#F2A93B",
    "running": "#2F9BED",
}


class HistoryRow(QFrame):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        layout = QHBoxLayout(self)

        color = _STATUS_COLORS.get(entry.status, "#5E6C8A")
        badge = QLabel(entry.status.upper())
        badge.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")
        badge.setFixedWidth(70)

        text_col = QVBoxLayout()
        title = QLabel(f"{entry.tool_label} — {entry.input_summary}")
        title.setStyleSheet("font-weight: 600; background: transparent; border: none;")
        meta = QLabel(
            f"{entry.started_at[:19].replace('T', ' ')}"
            + (f" • {entry.duration_ms} ms" if entry.duration_ms else "")
            + (f" • {entry.detail}" if entry.detail else "")
        )
        meta.setProperty("class", "MutedLabel")
        meta.setStyleSheet("background: transparent; border: none;")
        text_col.addWidget(title)
        text_col.addWidget(meta)

        layout.addWidget(badge)
        layout.addLayout(text_col, 1)


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = HistoryRepository()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)

        header = QHBoxLayout()
        title = QLabel("Processing History")
        title.setProperty("class", "TitleLabel")
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton("Clear History")
        clear_btn.setProperty("class", "Secondary")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setSpacing(8)
        scroll.setWidget(self._content)

        self.refresh()

    def refresh(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._repo.list_recent(limit=200)
        if not entries:
            self._layout.addWidget(
                EmptyState("📜", "No processing history yet", "Every tool run — success or failure — will be logged here.")
            )
            return

        for entry in entries:
            self._layout.addWidget(HistoryRow(entry))
        self._layout.addStretch()

    def _clear_all(self) -> None:
        self._repo.clear()
        self.refresh()
