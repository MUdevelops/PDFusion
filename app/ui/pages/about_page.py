from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from app.constants import APP_NAME, APP_TAGLINE, APP_VERSION, APP_ORG, APP_DESCRIPTION
from app.ui.dialogs.dependency_dialog import show_dependency_status

_LIBRARIES = [
    "PySide6", "PyMuPDF (fitz)", "pypdf", "Pillow", "python-docx",
    "openpyxl", "python-pptx", "ReportLab", "cryptography", "pytesseract",
]


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(6)

        name = QLabel(APP_NAME)
        name.setProperty("class", "TitleLabel")
        tagline = QLabel(APP_TAGLINE)
        tagline.setProperty("class", "SectionLabel")
        version = QLabel(f"Version {APP_VERSION}")
        version.setProperty("class", "MutedLabel")
        developer = QLabel(f"Developer: {APP_ORG}")
        developer.setProperty("class", "MutedLabel")
        license_label = QLabel("License: Proprietary — All rights reserved")
        license_label.setProperty("class", "MutedLabel")
        description = QLabel(APP_DESCRIPTION)
        description.setWordWrap(True)

        layout.addWidget(name)
        layout.addWidget(tagline)
        layout.addSpacing(8)
        layout.addWidget(version)
        layout.addWidget(developer)
        layout.addWidget(license_label)
        layout.addSpacing(12)
        layout.addWidget(description)

        layout.addSpacing(16)
        libs_title = QLabel("Built with")
        libs_title.setProperty("class", "SectionLabel")
        layout.addWidget(libs_title)
        for lib in _LIBRARIES:
            layout.addWidget(QLabel(f"• {lib}"))

        layout.addSpacing(16)
        dep_btn = QPushButton("View Dependency Status")
        dep_btn.setProperty("class", "Secondary")
        dep_btn.setFixedWidth(220)
        dep_btn.clicked.connect(lambda: show_dependency_status(self))
        layout.addWidget(dep_btn)
