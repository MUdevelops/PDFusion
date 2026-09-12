"""User-facing error dialog.

Rule (spec section 32): never show a raw Python traceback. Always show
a short human message, with "Technical details" collapsed behind a
toggle, plus "Copy error" and "Open log" actions.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QApplication, QMessageBox,
)
from PySide6.QtCore import Qt
import os
import subprocess
import sys

from app.utils.logger import current_log_path


class ErrorDialog(QDialog):
    def __init__(self, message: str, technical_detail: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDFusion — Something went wrong")
        self.setMinimumWidth(440)
        self._technical_detail = technical_detail

        layout = QVBoxLayout(self)

        icon_and_msg = QHBoxLayout()
        icon_label = QLabel("⚠")
        icon_label.setStyleSheet("font-size: 28px;")
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        icon_and_msg.addWidget(icon_label)
        icon_and_msg.addWidget(msg_label, 1)
        layout.addLayout(icon_and_msg)

        self.details_box = QPlainTextEdit(technical_detail)
        self.details_box.setReadOnly(True)
        self.details_box.setFixedHeight(120)
        self.details_box.setVisible(False)
        layout.addWidget(self.details_box)

        toggle_row = QHBoxLayout()
        self.toggle_btn = QPushButton("Show technical details")
        self.toggle_btn.setProperty("class", "Secondary")
        self.toggle_btn.clicked.connect(self._toggle_details)
        toggle_row.addWidget(self.toggle_btn)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        button_row = QHBoxLayout()
        copy_btn = QPushButton("Copy Error")
        copy_btn.setProperty("class", "Secondary")
        copy_btn.clicked.connect(self._copy_error)

        open_log_btn = QPushButton("Open Log")
        open_log_btn.setProperty("class", "Secondary")
        open_log_btn.clicked.connect(self._open_log)

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "Primary")
        close_btn.clicked.connect(self.accept)

        button_row.addWidget(copy_btn)
        button_row.addWidget(open_log_btn)
        button_row.addStretch()
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

    def _toggle_details(self) -> None:
        visible = not self.details_box.isVisible()
        self.details_box.setVisible(visible)
        self.toggle_btn.setText("Hide technical details" if visible else "Show technical details")

    def _copy_error(self) -> None:
        QApplication.clipboard().setText(self._technical_detail or "No technical details available.")

    def _open_log(self) -> None:
        log_path = current_log_path()
        try:
            if sys.platform == "win32":
                os.startfile(log_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(log_path)])
            else:
                subprocess.run(["xdg-open", str(log_path)])
        except Exception:
            QMessageBox.information(self, "Log file", f"Log file location:\n{log_path}")


def show_error(parent, message: str, technical_detail: str = "") -> None:
    dialog = ErrorDialog(message, technical_detail, parent)
    dialog.exec()
