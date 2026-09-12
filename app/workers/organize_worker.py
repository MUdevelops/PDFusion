from __future__ import annotations

from pathlib import Path

from app.core.organizer import OrganizeSession
from app.workers.pdf_worker import PdfWorker


class OrganizeWorker(PdfWorker):
    def __init__(self, session: OrganizeSession, output_path: Path, parent=None):
        super().__init__(parent)
        self.session = session
        self.output_path = output_path

    def run_job(self) -> Path:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        return self.session.save(self.output_path, progress_cb=progress)
