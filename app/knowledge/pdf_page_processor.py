"""Project Expert AI — PDF Page Processor v2.

Извлекает страницы PDF и одновременно формирует агрегированный
parsed JSON, необходимый существующему SPIndexBuilder.
"""

import json
from datetime import datetime

import pymupdf

from app.knowledge.storage import KnowledgeStorage


class PDFPageProcessor:
    """Извлекает страницы PDF и сохраняет parsed representation."""

    def __init__(self, document_id="SP_30.13330", version_id=None, storage=None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.paths = self.storage.paths(document_id, version_id)
        self.pdf_path = self.paths.pdf
        self.output_dir = self.paths.pages
        self.parsed_path = self.paths.parsed

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
                "number": self.storage.get_document(self.document_id)["number"],
                "title": self.storage.get_document(self.document_id).get("title", ""),
                "source_file": str(self.pdf_path),
                "pages": 0,
            },
            "document_id": self.document_id,
            "version": self.storage.get_version(self.document_id, self.version_id).get("id"),
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
        """Собрать страницы в формат, который ожидает Structure Parser."""
        self.parsed_path.parent.mkdir(parents=True, exist_ok=True)
        document = self.storage.get_document(self.document_id)
        data = {
            "schema_version": "1.0",
            "document": {
                "number": document.get("number"),
                "title": document.get("title"),
                "source_file": str(self.pdf_path),
                "pages": total,
            },
            "document_id": self.document_id,
            "version": self.storage.get_version(self.document_id, self.version_id).get("id"),
            "pages": pages,
            "created": datetime.now().isoformat(),
        }
        with self.parsed_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print("Parsed:", self.parsed_path)
        return self.parsed_path

    def run(self):
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
