"""Left navigation sidebar for the currently implemented PDF tools."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QButtonGroup, QFrame

from app.constants import APP_NAME, APP_TAGLINE

NAV_ITEMS: list[tuple[str, str, str]] = [
    # (page_id, label, icon glyph)
    ("home", "Home", "🏠"),
    ("all_tools", "All Tools", "🧰"),
    ("organize", "Organize PDF", "🗂"),
    ("recent", "Recent Files", "🕓"),
    ("history", "History", "📜"),
]

FOOTER_ITEMS: list[tuple[str, str, str]] = [
    ("settings", "Settings", "⚙️"),
    ("about", "About", "ℹ️"),
]


class Sidebar(QWidget):
    navigate = Signal(str)  # emits page_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(232)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        brand = QLabel(APP_NAME)
        brand.setObjectName("SidebarBrand")
        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("SidebarTagline")
        layout.addWidget(brand)
        layout.addWidget(tagline)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for page_id, label, icon in NAV_ITEMS:
            btn = self._make_button(page_id, label, icon)
            layout.addWidget(btn)

        layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #243352;")
        layout.addWidget(divider)

        for page_id, label, icon in FOOTER_ITEMS:
            btn = self._make_button(page_id, label, icon)
            layout.addWidget(btn)

        self.set_active("home")

    def _make_button(self, page_id: str, label: str, icon: str) -> QPushButton:
        btn = QPushButton(f"  {icon}   {label}")
        btn.setObjectName("SidebarItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.navigate.emit(page_id))
        self._group.addButton(btn)
        self._buttons[page_id] = btn
        return btn

    def set_active(self, page_id: str) -> None:
        btn = self._buttons.get(page_id)
        if btn:
            btn.setChecked(True)
