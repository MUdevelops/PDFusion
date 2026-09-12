"""Application exception hierarchy.

Every user-facing failure should surface as one of these, carrying a
short, non-technical ``message`` plus the original exception in
``__cause__`` / ``.technical_detail`` for the "Technical details" /
"Copy error" affordances in the error dialog. Raw tracebacks must never
reach the UI directly — see app.ui.dialogs.error_dialog.
"""
from __future__ import annotations


class PDFusionError(Exception):
    """Base class for all application-raised errors."""

    def __init__(self, message: str, technical_detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.technical_detail = technical_detail or ""


class DependencyMissingError(PDFusionError):
    """Raised when an optional external tool is required but absent."""

    def __init__(self, dependency_name: str, install_hint: str = ""):
        msg = f"Feature unavailable because {dependency_name} is not installed."
        super().__init__(msg, technical_detail=install_hint)
        self.dependency_name = dependency_name
        self.install_hint = install_hint


class FileValidationError(PDFusionError):
    """Raised when an input file is missing, unreadable, or the wrong type."""


class PdfCorruptedError(PDFusionError):
    """Raised when a PDF cannot be parsed even after repair attempts."""


class PasswordRequiredError(PDFusionError):
    """Raised when a PDF is encrypted and no/incorrect password was given."""


class OperationCancelledError(PDFusionError):
    """Raised when a user cancels a running batch/worker operation."""

    def __init__(self):
        super().__init__("Operation cancelled by user.")


class InsufficientDiskSpaceError(PDFusionError):
    """Raised when there isn't enough free space to complete a save."""
