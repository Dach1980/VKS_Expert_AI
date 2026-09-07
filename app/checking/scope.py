"""Helpers for explicit page-scope selection in document checks."""
from __future__ import annotations

import re
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None


_RANGE_RE = re.compile(r"^(\d+)(?:\s*-\s*(\d+))?$")


def get_pdf_page_count(pdf_path: str | Path) -> int:
    if fitz is None:
        raise RuntimeError("PyMuPDF is required for PDF page counting")
    path = Path(pdf_path)
    doc = fitz.open(path)
    try:
        return len(doc)
    finally:
        doc.close()


def parse_page_ranges(value: str, total_pages: int) -> list[int]:
    """Parse 1-based ranges such as ``1-3, 7, 12-15`` into sorted unique pages."""
    if total_pages < 1:
        raise ValueError("Документ не содержит страниц")
    text = str(value or "").strip()
    if not text:
        raise ValueError("Укажите номера страниц или выберите проверку всего документа")
    pages: set[int] = set()
    for raw_part in text.split(","):
        part = raw_part.strip()
        match = _RANGE_RE.fullmatch(part)
        if not match:
            raise ValueError(f"Некорректный диапазон страниц: «{part}». Используйте формат 1-3, 7, 12-15")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start > end:
            raise ValueError(f"Некорректный диапазон страниц: «{part}»")
        if start < 1 or end > total_pages:
            raise ValueError(f"Страницы должны быть в диапазоне от 1 до {total_pages}")
        pages.update(range(start, end + 1))
    return sorted(pages)


def normalize_page_scope(total_pages: int, whole_document: bool, page_ranges: str = "") -> list[int]:
    if whole_document:
        return list(range(1, total_pages + 1))
    return parse_page_ranges(page_ranges, total_pages)
