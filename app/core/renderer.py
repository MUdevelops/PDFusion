"""Page rendering for the built-in PDF viewer.

Renders on demand (never the whole document eagerly) and caches the
last N rendered pixmaps per document so scrolling/zooming stays smooth
without re-rendering from scratch. Requires PyMuPDF; callers should
check ``pdf_engine.FITZ_AVAILABLE`` first and show a dependency notice
otherwise (see app.ui.dialogs.dependency_dialog).
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from app.core.pdf_engine import require_fitz, FITZ_AVAILABLE
from app.utils.logger import get_logger

logger = get_logger(__name__)

if FITZ_AVAILABLE:
    import fitz


class PageRenderer:
    """Renders individual pages of a single PDF to PNG bytes, with an
    LRU cache keyed by (page_index, zoom, rotation)."""

    def __init__(self, path: Path, cache_size: int = 24):
        require_fitz()
        self.path = Path(path)
        self._doc = fitz.open(str(self.path))
        self._cache: "OrderedDict[tuple[int, float, int], bytes]" = OrderedDict()
        self._cache_size = cache_size

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def page_size(self, page_index: int) -> tuple[float, float]:
        rect = self._doc[page_index].rect
        return rect.width, rect.height

    def render_page_png(self, page_index: int, zoom: float = 1.5, rotation: int = 0) -> bytes:
        """Return PNG-encoded bytes for a page at the given zoom factor."""
        key = (page_index, zoom, rotation)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        page = self._doc[page_index]
        matrix = fitz.Matrix(zoom, zoom).prerotate(rotation)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        data = pixmap.tobytes("png")

        self._cache[key] = data
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return data

    def render_thumbnail_png(self, page_index: int, max_dim: int = 160) -> bytes:
        w, h = self.page_size(page_index)
        zoom = max_dim / max(w, h)
        return self.render_page_png(page_index, zoom=zoom)

    def extract_text(self, page_index: int) -> str:
        return self._doc[page_index].get_text()

    def search(self, query: str, case_sensitive: bool = False, whole_word: bool = False):
        """Yield (page_index, [fitz.Rect, ...]) for matches across the document."""
        flags = 0
        for i, page in enumerate(self._doc):
            text_instances = page.search_for(query, quads=False)
            if text_instances:
                yield i, text_instances

    def close(self) -> None:
        self._doc.close()
        self._cache.clear()

    def __enter__(self) -> "PageRenderer":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
