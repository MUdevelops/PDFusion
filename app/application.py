"""Application bootstrap: creates the QApplication, loads config,
applies theme, runs the startup dependency scan, and shows MainWindow.
"""
from __future__ import annotations

import sys

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from app.config import AppConfig
from app.constants import APP_NAME, APP_ORG, RESOURCES_DIR
from app.database.database import get_database
from app.ui.main_window import MainWindow
from app.ui.themes.theme_manager import build_stylesheet
from app.utils.dependency_checker import run_dependency_scan
from app.utils.file_utils import clean_temp_files
from app.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


class PDFusionApplication:
    def __init__(self, argv: list[str]):
        configure_logging()
        logger.info("Starting %s", APP_NAME)

        self.qt_app = QApplication(argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setOrganizationName(APP_ORG)

        splash = QSplashScreen(QPixmap(str(RESOURCES_DIR / "images" / "Splash.png")))
        splash.show()
        self.qt_app.processEvents()

        # Ensure the SQLite schema exists before anything reads/writes it.
        get_database()

        self.config = AppConfig.load()
        self.qt_app.setStyleSheet(build_stylesheet(self.config.theme))

        removed = clean_temp_files()
        if removed:
            logger.info("Cleaned %d stale temp file(s)", removed)

        report = run_dependency_scan(
            self.config.tesseract_path or None,
            self.config.libreoffice_path or None,
            self.config.ghostscript_path or None,
        )
        for status in report.all_statuses:
            if not status.available:
                logger.info("Optional future-feature dependency unavailable: %s", status.name)

        self.main_window = MainWindow(self.config)
        splash.finish(self.main_window)

    def run(self) -> int:
        self.main_window.show()
        return self.qt_app.exec()


def main() -> int:
    app = PDFusionApplication(sys.argv)
    return app.run()
