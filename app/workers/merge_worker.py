from __future__ import annotations

from pathlib import Path

from app.core.merger import MergeItem, merge_pdfs
from app.workers.pdf_worker import PdfWorker


class MergeWorker(PdfWorker):
    def __init__(self, items: list[MergeItem], output_path: Path, parent=None):
        super().__init__(parent)
        self.items = items
        self.output_path = output_path

    def run_job(self) -> Path:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        return merge_pdfs(self.items, self.output_path, progress_cb=progress)
