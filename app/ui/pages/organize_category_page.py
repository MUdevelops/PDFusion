from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.constants import ToolId
from app.ui.widgets.cards import QuickActionCard


class OrganizeCategoryPage(QWidget):
    toolRequested = Signal(str)

    _TOOLS = (
        (ToolId.MERGE, "Merge PDF", "🧩"),
        (ToolId.SPLIT, "Split PDF", "✂️"),
        (ToolId.ORGANIZE, "Organize PDF", "🗂"),
        (ToolId.ROTATE, "Rotate PDF", "🔄"),
        (ToolId.CROP, "Crop PDF", "🔲"),
        (ToolId.EXTRACT, "Extract Pages", "📤"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)
        title = QLabel("Organize PDF")
        title.setProperty("class", "TitleLabel")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(14)
        for index, (tool_id, label, icon) in enumerate(self._TOOLS):
            card = QuickActionCard(tool_id, label, icon)
            card.clicked.connect(self.toolRequested.emit)
            grid.addWidget(card, index // 6, index % 6)
        layout.addLayout(grid)
        layout.addStretch()
