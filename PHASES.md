# PDFusion Build Roadmap

- [x] **Phase 1 — Application shell**
      Dashboard, sidebar, theme (dark/light), PDF viewer, drag & drop,
      SQLite-backed recent files / favorites / history, settings,
      dependency detection, logging & error handling.
- [ ] **Phase 2 — Organize**
      Merge, Split, Rotate, Organize (reorder/delete/duplicate/insert/replace
      pages), Extract.
- [ ] **Phase 3 — Convert & basic optimize**
      Compress, Image↔PDF, PDF→JPG/PNG, Metadata, Watermark, Page numbers.
- [ ] **Phase 4 — Security & markup**
      Protect, Unlock, Signature, Annotate, Redact, Crop.
- [ ] **Phase 5 — OCR & office conversion**
      OCR PDF/Image, Searchable PDF, DOCX/XLSX/PPTX conversion, advanced
      optimization.
- [ ] **Phase 6 — Batch, packaging, and polish**
      Batch processing queue, performance passes, full test suite,
      PyInstaller build + Windows installer.

Each phase ends with real functional verification against actual sample
files before moving to the next (see spec section 47 — no feature is
marked done on the strength of the UI alone).
