"""Base worker running on a QThread so heavy PDF operations never
block the GUI event loop.

Every tool-specific worker (merge, split, compress, ocr, ...) should
subclass ``PdfWorker`` and implement ``run_job()``. The base class
gives every worker the same signal contract, cancellation support, and
translation of raised exceptions into the PDFusionError hierarchy so
the UI can show a friendly message.
"""
from __future__ import annotations

import time
import traceback
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from app.utils.errors import PDFusionError, OperationCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkerSignals(QObject):
    started = Signal()
    progress = Signal(int, str)          # percentage 0-100, status text
    finished = Signal(object)            # arbitrary result payload
    failed = Signal(str, str)            # user message, technical detail
    cancelled = Signal()


class PdfWorker(QThread):
    """Run ``run_job()`` off the GUI thread.

    Subclasses call ``self.check_cancelled()`` periodically inside
    long loops (e.g. per-page, per-file in a batch) so Cancel actually
    stops work promptly instead of only preventing the *next* job.
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._cancel_requested = False
        self._start_time: float = 0.0

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def check_cancelled(self) -> None:
        if self._cancel_requested:
            raise OperationCancelledError()

    def report_progress(self, percent: int, message: str = "") -> None:
        self.signals.progress.emit(max(0, min(100, percent)), message)

    def run(self) -> None:  # QThread entry point
        self._start_time = time.time()
        self.signals.started.emit()
        try:
            result = self.run_job()
        except OperationCancelledError:
            logger.info("%s cancelled by user", self.__class__.__name__)
            self.signals.cancelled.emit()
        except PDFusionError as exc:
            logger.warning("%s failed: %s", self.__class__.__name__, exc.message)
            self.signals.failed.emit(exc.message, exc.technical_detail)
        except Exception as exc:  # noqa: BLE001 - last line of defense
            tb = traceback.format_exc()
            logger.error("%s crashed: %s\n%s", self.__class__.__name__, exc, tb)
            self.signals.failed.emit(
                "Unable to process this file. Please try again.", tb
            )
        else:
            elapsed = time.time() - self._start_time
            logger.info("%s finished in %.2fs", self.__class__.__name__, elapsed)
            self.signals.finished.emit(result)

    def run_job(self) -> Any:
        raise NotImplementedError("Subclasses must implement run_job()")
