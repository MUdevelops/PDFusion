"""Shows optional-dependency status (Tesseract / LibreOffice / Ghostscript /
PyMuPDF) with install hints — used at startup diagnostics and from a
"Feature unavailable" prompt inside any tool that needs one of these.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

from app.utils.dependency_checker import DependencyReport, run_dependency_scan


class DependencyRow(QFrame):
    def __init__(self, status, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        badge = QLabel("✓ Installed" if status.available else "✕ Not installed")
        badge.setStyleSheet(
            "color: #2FBF71; font-weight: 600;" if status.available
            else "color: #EF4B5F; font-weight: 600;"
        )
        name = QLabel(status.name)
        name.setStyleSheet("font-weight: 600;")
        layout.addWidget(name)
        layout.addStretch()
        layout.addWidget(badge)

        if not status.available and status.install_hint:
            hint_row = QVBoxLayout()  # placeholder to keep structure simple
        self.status = status


class DependencyDialog(QDialog):
    def __init__(self, report: DependencyReport | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDFusion — Dependency Status")
        self.setMinimumWidth(420)
        report = report or run_dependency_scan()

        layout = QVBoxLayout(self)
        title = QLabel("Optional Components")
        title.setProperty("class", "SectionLabel")
        layout.addWidget(title)

        subtitle = QLabel(
            "PDFusion works locally without these, but some features "
            "need them installed."
        )
        subtitle.setProperty("class", "MutedLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        for status in report.all_statuses:
            row = DependencyRow(status)
            layout.addWidget(row)
            if not status.available and status.install_hint:
                hint = QLabel(status.install_hint)
                hint.setWordWrap(True)
                hint.setProperty("class", "MutedLabel")
                hint.setStyleSheet("font-size: 11px; padding-left: 4px;")
                layout.addWidget(hint)

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "Primary")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


def show_dependency_status(parent=None) -> None:
    dialog = DependencyDialog(parent=parent)
    dialog.exec()
