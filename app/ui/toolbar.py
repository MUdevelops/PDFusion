"""Top toolbar: breadcrumb/title, search box, local-first status pill,
theme toggle."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton


class TopToolbar(QWidget):
    searchChanged = Signal(str)
    themeToggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopToolbar")
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        self.title_label = QLabel("Home")
        self.title_label.setProperty("class", "SectionLabel")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tools or files…  (Ctrl+F)")
        self.search_box.setFixedWidth(280)
        self.search_box.textChanged.connect(self.searchChanged.emit)
        layout.addWidget(self.search_box)

        self.local_pill = QLabel("🔒  Your files stay on this computer")
        self.local_pill.setStyleSheet(
            "background-color: rgba(47,191,113,0.15); color: #2FBF71; "
            "border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self.local_pill)

        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.themeToggled.emit)
        layout.addWidget(self.theme_btn)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_theme_icon(self, theme: str) -> None:
        self.theme_btn.setText("☀️" if theme == "dark" else "🌙")
