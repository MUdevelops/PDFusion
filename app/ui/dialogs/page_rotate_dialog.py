"""Dialog to set an individual rotation (0/90/180/270) for each page of
one file. Used by Merge ("rotate individual pages before merge") and
available for reuse anywhere else a per-page rotation map is needed.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QWidget, QDialogButtonBox,
)

from app.core.pdf_engine import page_count_only

_ANGLES = [0, 90, 180, 270]


class PageRotateDialog(QDialog):
    def __init__(self, path: Path, initial_rotations: dict[int, int] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Rotate pages — {path.name}")
        self.setMinimumWidth(360)
        self._combos: dict[int, QComboBox] = {}

        layout = QVBoxLayout(self)
        info = QLabel("Set a rotation for individual pages before merging.")
        info.setProperty("class", "MutedLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(280)
        content = QWidget()
        rows = QVBoxLayout(content)

        initial_rotations = initial_rotations or {}
        try:
            page_count = page_count_only(path)
        except Exception:
            page_count = 0

        for i in range(page_count):
            row = QHBoxLayout()
            label = QLabel(f"Page {i + 1}")
            combo = QComboBox()
            combo.addItems([f"{a}\u00b0" for a in _ANGLES])
            current = initial_rotations.get(i, 0)
            combo.setCurrentIndex(_ANGLES.index(current) if current in _ANGLES else 0)
            row.addWidget(label)
            row.addStretch()
            row.addWidget(combo)
            rows.addLayout(row)
            self._combos[i] = combo

        rows.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def rotations(self) -> dict[int, int]:
        result = {}
        for i, combo in self._combos.items():
            angle = _ANGLES[combo.currentIndex()]
            if angle:
                result[i] = angle
        return result
