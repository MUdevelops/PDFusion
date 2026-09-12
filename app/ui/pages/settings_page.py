from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QLineEdit, QPushButton, QSpinBox, QScrollArea, QFrame, QFileDialog, QMessageBox,
)

from app.config import AppConfig
from app.database.repositories import HistoryRepository, RecentFilesRepository
from app.utils.dependency_checker import run_dependency_scan
from app.utils.file_utils import clean_temp_files


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setProperty("class", "SectionLabel")
    return lbl


class SettingsPage(QWidget):
    themeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AppConfig.load()

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setProperty("class", "TitleLabel")
        layout.addWidget(title)

        # -------- General --------
        layout.addWidget(_section("General"))
        card = QFrame(); card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.config.theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addStretch()
        theme_row.addWidget(self.theme_combo)
        card_layout.addLayout(theme_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Default output folder"))
        self.output_edit = QLineEdit(self.config.default_output_folder)
        browse_btn = QPushButton("Browse")
        browse_btn.setProperty("class", "Secondary")
        browse_btn.clicked.connect(self._browse_output_folder)
        out_row.addWidget(self.output_edit, 1)
        out_row.addWidget(browse_btn)
        card_layout.addLayout(out_row)

        self.auto_open_check = QCheckBox("Automatically open output after processing")
        self.auto_open_check.setChecked(self.config.auto_open_output)
        card_layout.addWidget(self.auto_open_check)

        self.confirm_overwrite_check = QCheckBox("Confirm before overwriting files")
        self.confirm_overwrite_check.setChecked(self.config.confirm_overwrite)
        card_layout.addWidget(self.confirm_overwrite_check)
        layout.addWidget(card)

        # -------- Performance --------
        layout.addWidget(_section("Performance"))
        perf_card = QFrame(); perf_card.setProperty("class", "Card")
        perf_layout = QVBoxLayout(perf_card)

        threads_row = QHBoxLayout()
        threads_row.addWidget(QLabel("Worker threads"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 32)
        self.threads_spin.setValue(self.config.worker_threads)
        threads_row.addStretch()
        threads_row.addWidget(self.threads_spin)
        perf_layout.addLayout(threads_row)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Rendering quality"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["fast", "balanced", "high"])
        self.quality_combo.setCurrentText(self.config.render_quality)
        quality_row.addStretch()
        quality_row.addWidget(self.quality_combo)
        perf_layout.addLayout(quality_row)
        layout.addWidget(perf_card)

        # -------- PDF defaults --------
        layout.addWidget(_section("PDF"))
        pdf_card = QFrame(); pdf_card.setProperty("class", "Card")
        pdf_layout = QVBoxLayout(pdf_card)

        comp_row = QHBoxLayout()
        comp_row.addWidget(QLabel("Default compression"))
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["low", "medium", "high", "custom"])
        self.compression_combo.setCurrentText(self.config.default_compression)
        comp_row.addStretch()
        comp_row.addWidget(self.compression_combo)
        pdf_layout.addLayout(comp_row)

        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("Default DPI"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(self.config.default_dpi)
        dpi_row.addStretch()
        dpi_row.addWidget(self.dpi_spin)
        pdf_layout.addLayout(dpi_row)

        quality_img_row = QHBoxLayout()
        quality_img_row.addWidget(QLabel("Default image quality"))
        self.image_quality_spin = QSpinBox()
        self.image_quality_spin.setRange(10, 100)
        self.image_quality_spin.setValue(self.config.default_image_quality)
        quality_img_row.addStretch()
        quality_img_row.addWidget(self.image_quality_spin)
        pdf_layout.addLayout(quality_img_row)
        layout.addWidget(pdf_card)

        # -------- Security / Privacy --------
        layout.addWidget(_section("Security"))
        sec_card = QFrame(); sec_card.setProperty("class", "Card")
        sec_layout = QVBoxLayout(sec_card)

        self.local_only_check = QCheckBox("Local-only processing (disable all network features)")
        self.local_only_check.setChecked(self.config.local_only_processing)
        sec_layout.addWidget(self.local_only_check)

        btn_row = QHBoxLayout()
        clear_temp_btn = QPushButton("Clear Temporary Files")
        clear_temp_btn.setProperty("class", "Secondary")
        clear_temp_btn.clicked.connect(self._clear_temp)
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.setProperty("class", "Secondary")
        clear_history_btn.clicked.connect(self._clear_history)
        btn_row.addWidget(clear_temp_btn)
        btn_row.addWidget(clear_history_btn)
        btn_row.addStretch()
        sec_layout.addLayout(btn_row)
        layout.addWidget(sec_card)

        # -------- Advanced --------
        layout.addWidget(_section("Advanced"))
        adv_card = QFrame(); adv_card.setProperty("class", "Card")
        adv_layout = QVBoxLayout(adv_card)

        self.tesseract_edit = self._path_row(adv_layout, "Tesseract path", self.config.tesseract_path)
        self.libreoffice_edit = self._path_row(adv_layout, "LibreOffice path", self.config.libreoffice_path)
        self.ghostscript_edit = self._path_row(adv_layout, "Ghostscript path", self.config.ghostscript_path)

        scan_btn = QPushButton("Re-scan Dependencies")
        scan_btn.setProperty("class", "Secondary")
        scan_btn.clicked.connect(self._rescan)
        adv_layout.addWidget(scan_btn)
        layout.addWidget(adv_card)

        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("class", "Primary")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()

    def _path_row(self, parent_layout: QVBoxLayout, label: str, value: str) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit(value)
        edit.setPlaceholderText("Auto-detected if empty")
        browse = QPushButton("...")
        browse.setFixedWidth(32)
        browse.clicked.connect(lambda: self._browse_path(edit))
        row.addWidget(edit, 1)
        row.addWidget(browse)
        parent_layout.addLayout(row)
        return edit

    def _browse_path(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select executable")
        if path:
            edit.setText(path)

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def _on_theme_changed(self, theme: str) -> None:
        self.themeChanged.emit(theme)

    def _clear_temp(self) -> None:
        n = clean_temp_files(older_than_seconds=0)
        QMessageBox.information(self, "Temporary files", f"Removed {n} temporary file(s).")

    def _clear_history(self) -> None:
        HistoryRepository().clear()
        RecentFilesRepository().clear()
        QMessageBox.information(self, "History cleared", "Processing history and recent files were cleared.")

    def _rescan(self) -> None:
        report = run_dependency_scan(
            self.tesseract_edit.text() or None,
            self.libreoffice_edit.text() or None,
            self.ghostscript_edit.text() or None,
        )
        lines = [f"{s.name}: {'Installed' if s.available else 'Not installed'}" for s in report.all_statuses]
        QMessageBox.information(self, "Dependency scan", "\n".join(lines))

    def _save(self) -> None:
        self.config.theme = self.theme_combo.currentText()
        self.config.default_output_folder = self.output_edit.text()
        self.config.auto_open_output = self.auto_open_check.isChecked()
        self.config.confirm_overwrite = self.confirm_overwrite_check.isChecked()
        self.config.worker_threads = self.threads_spin.value()
        self.config.render_quality = self.quality_combo.currentText()
        self.config.default_compression = self.compression_combo.currentText()
        self.config.default_dpi = self.dpi_spin.value()
        self.config.default_image_quality = self.image_quality_spin.value()
        self.config.local_only_processing = self.local_only_check.isChecked()
        self.config.tesseract_path = self.tesseract_edit.text()
        self.config.libreoffice_path = self.libreoffice_edit.text()
        self.config.ghostscript_path = self.ghostscript_edit.text()
        self.config.save()
        QMessageBox.information(self, "Settings", "Settings saved.")
