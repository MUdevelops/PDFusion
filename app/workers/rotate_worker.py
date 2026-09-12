from __future__ import annotations

from pathlib import Path

from app.core.rotator import rotate_pdf
from app.workers.pdf_worker import PdfWorker


class RotateWorker(PdfWorker):
    def __init__(self, source: Path, degrees: int, output_path: Path, page_indices: list[int] | None, parent=None):
        super().__init__(parent)
        self.source = source
        self.degrees = degrees
        self.output_path = output_path
        self.page_indices = page_indices

    def run_job(self) -> Path:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        return rotate_pdf(self.source, self.degrees, self.output_path, self.page_indices, progress)
