"""Project Expert AI — PDF Page Processor v3.

Извлекает страницы PDF и формирует parsed JSON. Процессор сохраняет
совместимость с нормативным SPIndexBuilder и дополнительно умеет работать
в standalone-режиме для проектной документации.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf

from app.knowledge.storage import KnowledgeStorage


class PDFPageProcessor:
    """Извлекает страницы PDF и сохраняет parsed representation."""

    def __init__(
        self,
        document_id="SP_30.13330",
        version_id=None,
        storage=None,
        pdf_path: Path | str | None = None,
        output_dir: Path | str | None = None,
        parsed_path: Path | str | None = None,
        document_meta: dict[str, Any] | None = None,
    ):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.standalone = pdf_path is not None
        self.document_meta = document_meta or {}

        if self.standalone:
            self.pdf_path = Path(pdf_path).resolve()
            self.output_dir = Path(output_dir).resolve()
            self.parsed_path = Path(parsed_path).resolve()
        else:
            self.paths = self.storage.paths(document_id, version_id)
            self.pdf_path = self.paths.pdf
            self.output_dir = self.paths.pages
            self.parsed_path = self.paths.parsed

    def _document_number(self) -> str:
        if self.document_meta.get("number"):
            return str(self.document_meta["number"])
        return self.storage.get_document(self.document_id)["number"]

    def _document_title(self) -> str:
        if self.document_meta.get("title"):
            return str(self.document_meta["title"])
        return self.storage.get_document(self.document_id).get("title", "")

    def _version_id(self) -> str | None:
        if self.document_meta.get("version_id"):
            return str(self.document_meta["version_id"])
        if self.version_id is None:
            return None
        return self.storage.get_version(self.document_id, self.version_id).get("id")

    def open_pdf(self):
        print("Opening PDF...")
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        doc = pymupdf.open(self.pdf_path)
        print("Pages:", len(doc))
        return doc

    def extract_page(self, page, number):
        rect = page.rect
        blocks = []
        for index, block in enumerate(page.get_text("blocks")):
            x0, y0, x1, y1, text, *_ = block
            if not text.strip():
                continue
            blocks.append({
                "index": index,
                "bbox": [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
                "text": text.strip(),
            })

        return {
            "document": {
                "number": self._document_number(),
                "title": self._document_title(),
                "source_file": str(self.pdf_path),
                "pages": 0,
            },
            "document_id": self.document_id,
            "version": self._version_id(),
            "page": number,
            "geometry": {"width": rect.width, "height": rect.height},
            "source": {"pdf": str(self.pdf_path), "pipeline": ["PyMuPDF", "PDFPageProcessor"]},
            "created": datetime.now().isoformat(),
            "blocks": blocks,
            "formulas": [],
        }

    def save_page(self, data):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self.output_dir / f"page_{data['page']:03}.json"
        with filename.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return filename

    def save_parsed(self, pages, total):
        self.parsed_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": "1.0",
            "document": {
                "number": self._document_number(),
                "title": self._document_title(),
                "source_file": str(self.pdf_path),
                "pages": total,
            },
            "document_id": self.document_id,
            "version": self._version_id(),
            "pages": pages,
            "created": datetime.now().isoformat(),
        }
        with self.parsed_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print("Parsed:", self.parsed_path)
        return self.parsed_path

    def run(self):
        if not self.standalone:
            self.storage.ensure_version_dirs(self.document_id, self.version_id)

        doc = self.open_pdf()
        pages = []
        try:
            total = len(doc)
            for index in range(total):
                page_number = index + 1
                print(f"Processing page {page_number}/{total}")
                data = self.extract_page(doc[index], page_number)
                data["document"]["pages"] = total
                self.save_page(data)
                pages.append(data)
                print(f"Saved: page_{page_number:03}.json")
        finally:
            doc.close()

        self.save_parsed(pages, total)
        print("\nPDF processing completed")
        return pages


def main():
    PDFPageProcessor().run()


if __name__ == "__main__":
    main()
