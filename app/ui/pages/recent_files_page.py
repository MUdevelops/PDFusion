from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea

from app.database.repositories import RecentFilesRepository
from app.ui.widgets.cards import RecentFileRow
from app.ui.widgets.empty_state import EmptyState
from app.utils.file_utils import human_size


class RecentFilesPage(QWidget):
    openFile = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = RecentFilesRepository()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)

        header = QHBoxLayout()
        title = QLabel("Recent Files")
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

        files = self._repo.list_recent(limit=100)
        if not files:
            self._layout.addWidget(
                EmptyState("🕓", "No recent files", "Files you open or process will appear here.")
            )
            return

        for rf in files:
            meta = human_size(rf.file_size)
            if rf.page_count:
                meta += f" • {rf.page_count} pages"
            meta += f" • {rf.last_opened_at[:19].replace('T', ' ')}"
            row = RecentFileRow(rf.file_name, meta, rf.file_path)
            row.openRequested.connect(self.openFile.emit)
            self._layout.addWidget(row)
        self._layout.addStretch()

    def _clear_all(self) -> None:
        self._repo.clear()
        self.refresh()
