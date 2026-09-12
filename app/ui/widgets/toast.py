"""Lightweight, self-dismissing toast notifications overlaid on a host
widget (typically the MainWindow). No external notification framework
needed — just a floating QFrame with a QTimer.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from app.constants import Palette

_KIND_COLORS = {
    "success": Palette.SUCCESS,
    "error": Palette.DANGER,
    "warning": Palette.WARNING,
    "info": Palette.ACCENT_PRIMARY,
}
_KIND_ICONS = {
    "success": "✓",
    "error": "✕",
    "warning": "⚠",
    "info": "ℹ",
}


class Toast(QFrame):
    def __init__(self, message: str, kind: str = "info", parent: QWidget | None = None, duration_ms: int = 3200):
        super().__init__(parent)
        color = _KIND_COLORS.get(kind, Palette.ACCENT_PRIMARY)
        icon = _KIND_ICONS.get(kind, "ℹ")

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
            }}
            QLabel {{ color: white; background: transparent; font-weight: 600; }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.addWidget(QLabel(icon))
        layout.addWidget(QLabel(message))
        self.adjustSize()

        self._fade = QPropertyAnimation(self, b"windowOpacity")
        QTimer.singleShot(duration_ms, self._start_fade_out)

    def _start_fade_out(self) -> None:
        self._fade.setDuration(400)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.deleteLater)
        self._fade.start()


def show_toast(host: QWidget, message: str, kind: str = "info") -> Toast:
    """Create and position a toast in the bottom-right corner of ``host``."""
    toast = Toast(message, kind, host)
    toast.show()
    margin = 24
    x = host.width() - toast.width() - margin
    y = host.height() - toast.height() - margin
    toast.move(max(0, x), max(0, y))
    toast.raise_()
    return toast
