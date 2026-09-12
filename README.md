# PDFusion — All-in-One PDF Workspace

A local-first, professional Windows desktop PDF suite built with
PySide6, PyMuPDF, and pypdf. Your files never leave your computer
unless you explicitly enable an online feature.

## Status: Phase 1 complete

This build implements the **application shell**:

- Modern dark/light themed desktop UI (navy / electric blue / violet accent)
- Sidebar navigation, top toolbar, dashboard with quick actions
- Drag-and-drop file intake
- Built-in PDF viewer (thumbnails, zoom, page navigation) — requires PyMuPDF
- SQLite-backed Recent Files, Favorites, and Processing History
- Settings (General / Performance / PDF / Security / Advanced)
- Startup dependency detection for Tesseract, LibreOffice, Ghostscript, PyMuPDF
- Robust error handling — no raw tracebacks ever reach the UI
- Full logging to `%APPDATA%/PDFusion/logs/app.log`

Actual PDF processing tools (Merge, Split, Compress, OCR, Convert, etc.)
are implemented in the phases that follow, per the build roadmap in
`PHASES.md`. Each category page currently explains which phase it lands in
rather than faking a working button.

## Requirements

- **Python 3.11+** (developed and verified against the 3.11 grammar; also
  runs on 3.12)
- Windows 10/11 primary target (Linux/macOS also work for development)
- Optional system tools for full feature coverage later on:
  - [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — for OCR tools
  - [LibreOffice](https://www.libreoffice.org/download/) — for Office↔PDF conversion
  - [Ghostscript](https://ghostscript.com/releases/) — for advanced compression

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

On first launch, PDFusion creates its local data directory
(`%APPDATA%/PDFusion` on Windows) containing:

- `pdfusion.sqlite3` — recent files, favorites, history, settings
- `logs/app.log` — rotating application log
- `temp/` — scratch space, cleaned automatically on startup

Nothing here is ever uploaded anywhere.

## Project layout

See `app/` for the modular source tree: `ui/` (PySide6 views/widgets),
`core/` (PDF engine — rendering, structural ops, security, etc. added
phase by phase), `workers/` (QThread background job base class),
`database/` (SQLite schema + repositories), `utils/` (logging, errors,
validators, dependency detection).

## Testing

```bash
pytest tests/
```

## Packaging (later phase)

`build_windows.bat` + PyInstaller will produce `PDFusion.exe` without
requiring Python on the target machine — added in Phase 6 alongside the
Windows installer.
