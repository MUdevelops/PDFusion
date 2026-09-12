from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QScrollArea

from app.constants import TOOL_CATEGORIES
from app.ui.widgets.cards import QuickActionCard

_TOOL_ICONS = {
    "merge": "🧩", "split": "✂️", "organize": "🗂", "rotate": "🔄", "crop": "🔲",
    "extract": "📤", "pdf_to_word": "📝", "pdf_to_image": "🖼️", "image_to_pdf": "📷",
    "office_to_pdf": "📎", "pdf_to_text": "📃", "compress": "🗜️", "optimize": "⚡",
    "repair": "🛠️", "edit": "✏️", "annotate": "🖊️", "watermark": "💧",
    "page_numbers": "🔢", "signature": "✍️", "redact": "⬛", "protect": "🔐",
    "unlock": "🔓", "metadata": "🏷️", "ocr_pdf": "🔎", "ocr_image": "🖼️🔎",
    "searchable_pdf": "📚",
}


class AllToolsPage(QWidget):
    toolRequested = Signal(str)

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

        title = QLabel("All Tools")
        title.setProperty("class", "TitleLabel")
        layout.addWidget(title)

        for category, tools in TOOL_CATEGORIES.items():
            cat_label = QLabel(category)
            cat_label.setProperty("class", "SectionLabel")
            layout.addWidget(cat_label)

            grid = QGridLayout()
            grid.setSpacing(14)
            for i, (tool_id, label) in enumerate(tools):
                card = QuickActionCard(tool_id, label, _TOOL_ICONS.get(tool_id, "📄"))
                card.clicked.connect(self.toolRequested.emit)
                grid.addWidget(card, i // 6, i % 6)
            layout.addLayout(grid)

        layout.addStretch()


class PendingToolPage(QWidget):
    """Shown for tools not yet implemented in the current build phase.

    This is intentionally NOT a fake "Coming Soon" button dead-end —
    it names the tool, states plainly it lands in a later phase per
    the build roadmap, and links back to a working tool.
    """

    def __init__(self, tool_label: str, phase_note: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("🚧")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 40px;")
        title = QLabel(f"{tool_label}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("class", "SectionLabel")
        note = QLabel(phase_note)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setProperty("class", "MutedLabel")
        note.setWordWrap(True)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(note)
