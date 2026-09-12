#!/usr/bin/env python3
"""PDFusion — All-in-One PDF Workspace.

Entry point. Run with:  python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.application import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
