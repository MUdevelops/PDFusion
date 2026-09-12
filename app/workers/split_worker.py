from __future__ import annotations

from pathlib import Path

from app.core import splitter
from app.workers.pdf_worker import PdfWorker

MODE_RANGE = "range"
MODE_EVERY_N = "every_n"
MODE_RANGES = "ranges"
MODE_ODD = "odd"
MODE_EVEN = "even"
MODE_SINGLE_PAGES = "single_pages"


class SplitWorker(PdfWorker):
    """Runs one of the six split modes and returns a ``list[Path]`` of
    every output file produced (always a list, even for the single-file
    modes, so the UI's Results step has one code path)."""

    def __init__(
        self,
        source: Path,
        mode: str,
        output_dir: Path,
        base_name: str,
        *,
        range_start: int = 1,
        range_end: int = 1,
        every_n: int = 1,
        ranges: list[tuple[int, int]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.mode = mode
        self.output_dir = output_dir
        self.base_name = base_name
        self.range_start = range_start
        self.range_end = range_end
        self.every_n = every_n
        self.ranges = ranges or []

    def run_job(self) -> list[Path]:
        def progress(pct: int, msg: str) -> None:
            self.check_cancelled()
            self.report_progress(pct, msg)

        self.check_cancelled()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == MODE_RANGE:
            out = self.output_dir / f"{self.base_name}_{self.range_start}-{self.range_end}.pdf"
            return [splitter.split_range(self.source, self.range_start, self.range_end, out, progress)]
        if self.mode == MODE_EVERY_N:
            return splitter.split_every_n(self.source, self.every_n, self.output_dir, self.base_name, progress)
        if self.mode == MODE_RANGES:
            return splitter.split_by_ranges(self.source, self.ranges, self.output_dir, self.base_name, progress)
        if self.mode == MODE_ODD:
            out = self.output_dir / f"{self.base_name}_odd.pdf"
            return [splitter.split_odd(self.source, out, progress)]
        if self.mode == MODE_EVEN:
            out = self.output_dir / f"{self.base_name}_even.pdf"
            return [splitter.split_even(self.source, out, progress)]
        if self.mode == MODE_SINGLE_PAGES:
            return splitter.split_to_single_pages(self.source, self.output_dir, self.base_name, progress)

        raise ValueError(f"Unknown split mode: {self.mode}")
