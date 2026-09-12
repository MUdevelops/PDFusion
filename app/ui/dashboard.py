"""Home dashboard: welcome header, quick actions grid, drag & drop
zone, recent files, and lightweight processing stats."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QSizePolicy,
)

from app.constants import APP_NAME, QUICK_ACTIONS
from app.database.repositories import RecentFilesRepository, HistoryRepository
from app.ui.widgets.cards import QuickActionCard, StatCard, RecentFileRow
from app.ui.widgets.drop_zone import DropZone
from app.ui.widgets.empty_state import EmptyState
from app.utils.file_utils import human_size
from app.utils.validators import PDF_SUFFIXES

_TOOL_ICONS = {
    "merge": "🧩", "split": "✂️", "compress": "🗜️", "pdf_to_word": "📝",
    "pdf_to_image": "🖼️", "image_to_pdf": "📷", "rotate": "🔄",
    "protect": "🔐", "unlock": "🔓", "ocr_pdf": "🔎", "edit": "✏️",
}


class Dashboard(QWidget):
    toolRequested = Signal(str)          # tool_id
    filesDropped = Signal(list)          # list[str] paths
    openRecentFile = Signal(str)         # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_repo = RecentFilesRepository()
        self._history_repo = HistoryRepository()

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        welcome = QLabel(f"Welcome to {APP_NAME}")
        welcome.setProperty("class", "TitleLabel")
        layout.addWidget(welcome)

        subtitle = QLabel("Drop a file below, or jump straight into a tool.")
        subtitle.setProperty("class", "MutedLabel")
        layout.addWidget(subtitle)

        self.drop_zone = DropZone(
            title="Drop PDFs or images here",
            subtitle="Files are processed locally — nothing leaves this computer",
            accepted_suffixes=PDF_SUFFIXES | {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"},
        )
        self.drop_zone.filesDropped.connect(self.filesDropped.emit)
        layout.addWidget(self.drop_zone)

        quick_label = QLabel("Quick Actions")
        quick_label.setProperty("class", "SectionLabel")
        layout.addWidget(quick_label)

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (tool_id, label) in enumerate(QUICK_ACTIONS):
            card = QuickActionCard(tool_id, label, _TOOL_ICONS.get(tool_id, "📄"))
            card.clicked.connect(self.toolRequested.emit)
            grid.addWidget(card, i // 6, i % 6)
        layout.addLayout(grid)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.stat_files = StatCard("Files processed", "0")
        self.stat_recent = StatCard("Recent files", "0")
        self.stat_storage = StatCard("Output folder size", "0 B")
        for card in (self.stat_files, self.stat_recent, self.stat_storage):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        recent_label = QLabel("Recent Files")
        recent_label.setProperty("class", "SectionLabel")
        layout.addWidget(recent_label)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(8)
        layout.addLayout(self.recent_container)

        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        # Clear existing recent-file rows
        while self.recent_container.count():
            item = self.recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recents = self._recent_repo.list_recent(limit=6)
        if not recents:
            self.recent_container.addWidget(
                EmptyState("🗂", "No recent files yet", "Files you open or process will show up here.")
            )
        else:
            for rf in recents:
                meta = f"{human_size(rf.file_size)}"
                if rf.page_count:
                    meta += f" • {rf.page_count} pages"
                if rf.last_operation:
                    meta += f" • {rf.last_operation}"
                row = RecentFileRow(rf.file_name, meta, rf.file_path)
                row.openRequested.connect(self.openRecentFile.emit)
                self.recent_container.addWidget(row)

        history = self._history_repo.list_recent(limit=1000)
        succeeded = [h for h in history if h.status == "success"]
        self.stat_files.set_value(str(len(succeeded)))
        self.stat_recent.set_value(str(len(recents)))

        from app.config import AppConfig
        cfg = AppConfig.load()
        out_dir = Path(cfg.default_output_folder)
        total = 0
        if out_dir.exists():
            for p in out_dir.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        self.stat_storage.set_value(human_size(total))
