from __future__ import annotations

from pathlib import Path

from app.core.cropper import CropMargins, crop_pdf
from app.workers.pdf_worker import PdfWorker


class CropWorker(PdfWorker):
    def __init__(
        self, source: Path, margins: CropMargins, output_path: Path,
        page_indices: list[int] | None, parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.margins = margins
        self.output_path = output_path
        self.page_indices = page_indices

    def run_job(self) -> Path:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        return crop_pdf(self.source, self.margins, self.output_path, self.page_indices, progress)
