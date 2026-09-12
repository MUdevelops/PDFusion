"""Generates the application QSS stylesheet for the 'dark' or 'light'
theme from the shared Palette, so colors stay in one place
(app/constants.py) instead of being duplicated across .qss files.
"""
from __future__ import annotations

from app.constants import Palette

_TEMPLATE = """
QWidget {{
    background-color: {bg_primary};
    color: {text_primary};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ---------------- Sidebar ---------------- */
#Sidebar {{
    background-color: {bg_secondary};
    border-right: 1px solid {border};
}}

#SidebarBrand {{
    font-size: 17px;
    font-weight: 600;
    color: {text_primary};
    padding: 18px 16px 4px 16px;
}}

#SidebarTagline {{
    font-size: 11px;
    color: {text_muted};
    padding: 0px 16px 14px 16px;
}}

QPushButton#SidebarItem {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    margin: 2px 10px;
    color: {text_secondary};
    background: transparent;
    font-size: 13px;
}}

QPushButton#SidebarItem:hover {{
    background-color: {bg_elevated};
    color: {text_primary};
}}

QPushButton#SidebarItem:checked {{
    background-color: {accent};
    color: white;
    font-weight: 600;
}}

/* ---------------- Cards ---------------- */
QFrame.Card {{
    background-color: {bg_card};
    border: 1px solid {border};
    border-radius: 14px;
}}

QFrame.Card:hover {{
    border: 1px solid {accent};
}}

/* ---------------- Buttons ---------------- */
QPushButton.Primary {{
    background-color: {accent};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton.Primary:hover {{ background-color: {accent_hover}; }}
QPushButton.Primary:pressed {{ background-color: {accent_pressed}; }}
QPushButton.Primary:disabled {{ background-color: {border}; color: {text_muted}; }}

QPushButton.Secondary {{
    background-color: transparent;
    color: {text_primary};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 500;
}}
QPushButton.Secondary:hover {{ border-color: {accent}; color: {accent}; }}

QPushButton.Danger {{
    background-color: {danger};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
}}

/* ---------------- Toolbar ---------------- */
#TopToolbar {{
    background-color: {bg_secondary};
    border-bottom: 1px solid {border};
}}

/* ---------------- Drop zone ---------------- */
#DropZone {{
    border: 2px dashed {border};
    border-radius: 16px;
    background-color: {bg_card};
}}
#DropZone[dragActive="true"] {{
    border: 2px dashed {accent};
    background-color: {bg_elevated};
}}

/* ---------------- Inputs ---------------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {bg_card};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 10px;
    color: {text_primary};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}

QProgressBar {{
    border: none;
    border-radius: 6px;
    background-color: {bg_elevated};
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 6px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {text_muted}; }}

QToolTip {{
    background-color: {bg_elevated};
    color: {text_primary};
    border: 1px solid {border};
    padding: 6px 8px;
    border-radius: 6px;
}}

#StatusFooter {{
    color: {text_muted};
    font-size: 11px;
    padding: 6px 12px;
    border-top: 1px solid {border};
}}

.MutedLabel {{ color: {text_secondary}; }}
.TitleLabel {{ font-size: 20px; font-weight: 700; color: {text_primary}; }}
.SectionLabel {{ font-size: 15px; font-weight: 600; color: {text_primary}; }}
"""


def build_stylesheet(theme: str = "dark") -> str:
    if theme == "light":
        return _TEMPLATE.format(
            bg_primary=Palette.LIGHT_BG_PRIMARY,
            bg_secondary=Palette.LIGHT_BG_SECONDARY,
            bg_card=Palette.LIGHT_BG_CARD,
            bg_elevated=Palette.LIGHT_BG_ELEVATED,
            border=Palette.LIGHT_BORDER,
            text_primary=Palette.LIGHT_TEXT_PRIMARY,
            text_secondary=Palette.LIGHT_TEXT_SECONDARY,
            text_muted=Palette.LIGHT_TEXT_MUTED,
            accent=Palette.ACCENT_PRIMARY,
            accent_hover=Palette.ACCENT_PRIMARY_HOVER,
            accent_pressed=Palette.ACCENT_PRIMARY_PRESSED,
            danger=Palette.DANGER,
        )
    return _TEMPLATE.format(
        bg_primary=Palette.DARK_BG_PRIMARY,
        bg_secondary=Palette.DARK_BG_SECONDARY,
        bg_card=Palette.DARK_BG_CARD,
        bg_elevated=Palette.DARK_BG_ELEVATED,
        border=Palette.DARK_BORDER,
        text_primary=Palette.DARK_TEXT_PRIMARY,
        text_secondary=Palette.DARK_TEXT_SECONDARY,
        text_muted=Palette.DARK_TEXT_MUTED,
        accent=Palette.ACCENT_PRIMARY,
        accent_hover=Palette.ACCENT_PRIMARY_HOVER,
        accent_pressed=Palette.ACCENT_PRIMARY_PRESSED,
        danger=Palette.DANGER,
    )
