from __future__ import annotations

from pathlib import Path

from app.core.extractor import extract_pages
from app.workers.pdf_worker import PdfWorker


class ExtractWorker(PdfWorker):
    def __init__(self, source: Path, page_indices: list[int], output_path: Path, parent=None):
        super().__init__(parent)
        self.source = source
        self.page_indices = page_indices
        self.output_path = output_path

    def run_job(self) -> Path:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        return extract_pages(self.source, self.page_indices, self.output_path, progress)
