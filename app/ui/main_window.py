"""Main application window.

Wires: Sidebar (navigation) + TopToolbar (search/theme) + a
QStackedWidget holding the Dashboard, All Tools, Recent Files,
History, Settings, About pages, and per-category placeholder pages
for tools landing in later build phases.

Also owns: theme application, keyboard shortcuts, and a PDF viewer
dialog opened from Dashboard / Recent Files.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QDialog, QLabel,
)

from app.config import AppConfig
from app.constants import APP_NAME, TOOL_CATEGORIES
from app.core.pdf_engine import get_pdf_info, FITZ_AVAILABLE
from app.database.repositories import RecentFilesRepository
from app.ui.dashboard import Dashboard
from app.ui.pages.about_page import AboutPage
from app.ui.pages.all_tools_page import AllToolsPage
from app.ui.pages.organize_category_page import OrganizeCategoryPage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.recent_files_page import RecentFilesPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.sidebar import Sidebar
from app.ui.themes.theme_manager import build_stylesheet
from app.ui.toolbar import TopToolbar
from app.ui.widgets.pdf_viewer import PdfViewer
from app.ui.widgets.toast import show_toast
from app.ui.tools.merge_page import MergePage
from app.ui.tools.split_page import SplitPage
from app.ui.tools.organize_page import OrganizePage
from app.ui.tools.rotate_page import RotatePage
from app.ui.tools.crop_page import CropPage
from app.ui.tools.extract_page import ExtractPage
from app.utils.errors import PDFusionError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_PAGE_TITLES = {
    "home": "Home",
    "all_tools": "All Tools",
    "organize": "Organize PDF",
    "tool_merge": "Merge PDF",
    "tool_split": "Split PDF",
    "tool_organize": "Organize PDF",
    "tool_rotate": "Rotate PDF",
    "tool_crop": "Crop PDF",
    "tool_extract": "Extract Pages",
    "recent": "Recent Files",
    "history": "History",
    "settings": "Settings",
    "about": "About",
}

# Maps a sidebar category page_id -> the TOOL_CATEGORIES key it should show
_CATEGORY_MAP = {
    "organize": "Organize",
}


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self._recent_repo = RecentFilesRepository()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self._on_navigate)
        root_layout.addWidget(self.sidebar)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        self.toolbar = TopToolbar()
        self.toolbar.themeToggled.connect(self._toggle_theme)
        right_col.addWidget(self.toolbar)

        self.stack = QStackedWidget()
        right_col.addWidget(self.stack, 1)

        self.status_footer = QLabel(self._footer_text())
        self.status_footer.setObjectName("StatusFooter")
        right_col.addWidget(self.status_footer)

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        root_layout.addWidget(right_wrap, 1)

        self._pages: dict[str, QWidget] = {}
        self._build_pages()
        self._setup_shortcuts()
        self._on_navigate("home")
        self.toolbar.set_theme_icon(self.config.theme)

    # -- page construction ---------------------------------------------
    def _build_pages(self) -> None:
        self.dashboard = Dashboard()
        self.dashboard.toolRequested.connect(self._open_tool)
        self.dashboard.filesDropped.connect(self._on_files_dropped)
        self.dashboard.openRecentFile.connect(self._open_pdf_viewer)
        self._register_page("home", self.dashboard)

        self.all_tools_page = AllToolsPage()
        self.all_tools_page.toolRequested.connect(self._open_tool)
        self._register_page("all_tools", self.all_tools_page)

        self.organize_category_page = OrganizeCategoryPage()
        self.organize_category_page.toolRequested.connect(self._open_tool)
        self._register_page("organize", self.organize_category_page)

        tool_pages = {
            "tool_merge": MergePage(),
            "tool_split": SplitPage(),
            "tool_organize": OrganizePage(),
            "tool_rotate": RotatePage(),
            "tool_crop": CropPage(),
            "tool_extract": ExtractPage(),
        }
        for page_id, page in tool_pages.items():
            self._register_page(page_id, page)

        self.recent_page = RecentFilesPage()
        self.recent_page.openFile.connect(self._open_pdf_viewer)
        self._register_page("recent", self.recent_page)

        self.history_page = HistoryPage()
        self._register_page("history", self.history_page)

        self.settings_page = SettingsPage()
        self.settings_page.themeChanged.connect(self._apply_theme)
        self._register_page("settings", self.settings_page)

        self._register_page("about", AboutPage())

    def _register_page(self, page_id: str, widget: QWidget) -> None:
        self._pages[page_id] = widget
        self.stack.addWidget(widget)

    # -- navigation ------------------------------------------------------
    def _on_navigate(self, page_id: str) -> None:
        page = self._pages.get(page_id)
        if page is None:
            return
        self.sidebar.set_active(page_id)
        self.toolbar.set_title(_PAGE_TITLES.get(page_id, page_id.title()))
        previous_page = self.stack.currentWidget()
        self.stack.setCurrentWidget(page)
        if page_id.startswith("tool_") and previous_page is not page:
            page.reset()
        if page_id == "home":
            self.dashboard.refresh()
        elif page_id == "recent":
            self.recent_page.refresh()
        elif page_id == "history":
            self.history_page.refresh()

    def _open_tool(self, tool_id: str) -> None:
        direct_pages = {
            "merge": "tool_merge", "split": "tool_split", "organize": "tool_organize",
            "rotate": "tool_rotate", "crop": "tool_crop", "extract": "tool_extract",
        }
        if tool_id in direct_pages:
            self._on_navigate(direct_pages[tool_id])
            return
        for page_id, category_key in _CATEGORY_MAP.items():
            ids = [t for t, _ in TOOL_CATEGORIES.get(category_key, [])]
            if tool_id in ids:
                self._on_navigate(page_id)
                return
        show_toast(self, f"Tool '{tool_id}' is not available yet.", kind="warning")

    def _on_files_dropped(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if path.suffix.lower() == ".pdf":
                try:
                    info = get_pdf_info(path)
                    self._recent_repo.touch(path, page_count=info.page_count)
                except PDFusionError as exc:
                    show_toast(self, exc.message, kind="error")
                    continue
        self.dashboard.refresh()
        if paths:
            show_toast(self, f"Added {len(paths)} file(s). Choose a tool to continue.", kind="success")

    def _open_pdf_viewer(self, file_path: str) -> None:
        if not FITZ_AVAILABLE:
            show_toast(
                self,
                "Install PyMuPDF (pip install PyMuPDF) to preview PDF pages.",
                kind="warning",
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(Path(file_path).name)
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        viewer = PdfViewer()
        viewer.load(file_path)
        layout.addWidget(viewer)
        self._recent_repo.touch(Path(file_path))
        dialog.exec()

    # -- theme -------------------------------------------------------------
    def _toggle_theme(self) -> None:
        new_theme = "light" if self.config.theme == "dark" else "dark"
        self._apply_theme(new_theme)

    def _apply_theme(self, theme: str) -> None:
        self.config.theme = theme
        self.config.save()
        from PySide6.QtWidgets import QApplication

        QApplication.instance().setStyleSheet(build_stylesheet(theme))
        self.toolbar.set_theme_icon(theme)

    # -- misc ------------------------------------------------------------
    def _footer_text(self) -> str:
        return "Your files stay on this computer.  •  PDFusion is local-first."

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.toolbar.search_box.setFocus())
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._shortcut_open)
        QShortcut(QKeySequence("Esc"), self, activated=self._shortcut_escape)

    def _shortcut_open(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if path:
            self._on_files_dropped([path])
            self._open_pdf_viewer(path)

    def _shortcut_escape(self) -> None:
        # Placeholder hook for cancelling an active worker/dialog.
        pass
