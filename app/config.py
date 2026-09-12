"""Typed, persisted application settings.

Wraps SettingsRepository (SQLite key/value) with typed accessors and
sane defaults so every part of the app reads settings the same way.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

from app.database.repositories import SettingsRepository


def _default_output_dir() -> str:
    downloads = Path.home() / "Downloads" / "PDFusion"
    return str(downloads)


@dataclass
class AppConfig:
    theme: str = "dark"                     # 'dark' | 'light'
    language: str = "en"
    default_output_folder: str = ""         # resolved lazily below
    auto_open_output: bool = True
    confirm_overwrite: bool = True

    worker_threads: int = max(2, (os.cpu_count() or 4) - 1)
    memory_mode: str = "balanced"           # 'low' | 'balanced' | 'performance'
    render_quality: str = "balanced"        # 'fast' | 'balanced' | 'high'

    default_compression: str = "medium"     # 'low' | 'medium' | 'high' | 'custom'
    default_dpi: int = 150
    default_image_quality: int = 85

    local_only_processing: bool = True
    tesseract_path: str = ""
    libreoffice_path: str = ""
    ghostscript_path: str = ""

    def __post_init__(self):
        if not self.default_output_folder:
            self.default_output_folder = _default_output_dir()

    # -- persistence -------------------------------------------------
    _BOOL_FIELDS = {"auto_open_output", "confirm_overwrite", "local_only_processing"}
    _INT_FIELDS = {"worker_threads", "default_dpi", "default_image_quality"}

    @classmethod
    def load(cls, repo: SettingsRepository | None = None) -> "AppConfig":
        repo = repo or SettingsRepository()
        stored = repo.all()
        cfg = cls()
        for f in fields(cls):
            if f.name in stored:
                raw = stored[f.name]
                if f.name in cls._BOOL_FIELDS:
                    setattr(cfg, f.name, raw == "1")
                elif f.name in cls._INT_FIELDS:
                    try:
                        setattr(cfg, f.name, int(raw))
                    except ValueError:
                        pass
                else:
                    setattr(cfg, f.name, raw)
        return cfg

    def save(self, repo: SettingsRepository | None = None) -> None:
        repo = repo or SettingsRepository()
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name in self._BOOL_FIELDS:
                repo.set(f.name, "1" if value else "0")
            else:
                repo.set(f.name, str(value))

    def ensure_output_dir(self) -> Path:
        p = Path(self.default_output_folder)
        p.mkdir(parents=True, exist_ok=True)
        return p
