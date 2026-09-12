"""Central logging configuration.

Every module gets its logger via ``get_logger(__name__)``. All records
also land in ``logs/app.log`` (rotating) inside the user data directory,
so "Open log" in the error dialog always has something real to show.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    from app.constants import logs_dir

    log_file = logs_dir() / "app.log"

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging initialized -> %s", log_file)


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)


def current_log_path():
    from app.constants import logs_dir

    return logs_dir() / "app.log"
