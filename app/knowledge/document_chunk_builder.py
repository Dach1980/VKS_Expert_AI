"""VKS Expert AI — Document Chunk Builder v8."""

import json
from datetime import datetime

from app.knowledge.storage import KnowledgeStorage


class DocumentChunkBuilder:
    def __init__(self, document_id="SP_30.13330", version_id=None, storage=None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.paths = self.storage.paths(document_id, version_id)
        self.document = self.storage.get_document(document_id)["number"]
        self.version = self.storage.get_version(document_id, version_id).get("id")

    def load_page(self, file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_text_chunk(self, page, block, index):
        text = str(block.get("text", "")).strip()
        if not text:
            return None
        return {
            "chunk_id": f"{self.document}-page-{page:03}-text-{index:03}",
            "type": "text",
            "document": self.document,
            "document_id": self.document_id,
            "version": self.version,
            "page": page,
            "location": {"page": page, "bbox": block.get("bbox"), "pdf": str(self.paths.pdf)},
            "content": {"text": text},
            "embedding_text": f"Документ: {self.document}. Версия: {self.version}. Страница: {page}. Тип: нормативный текст. Текст: {text}",
            "metadata": {"source": self.document_id, "created": datetime.now().isoformat()},
        }

    def find_nearest_text(self, formula, blocks):
        formula_y = formula.get("bbox", [0, 0, 0, 0])[1]
        before, after = [], []
        for block in blocks:
            text = str(block.get("text", "")).strip()
            if not text:
                continue
            y = block.get("bbox", [0, 0, 0, 0])[3]
            (before if y <= formula_y else after).append((y, text))
        before.sort(key=lambda x: x[0], reverse=True)
        after.sort(key=lambda x: x[0])
        return " ".join(x[1] for x in before[:3]), " ".join(x[1] for x in after[:2])

    def build_formula_context_chunk(self, page, formula, blocks, index):
        recognition = formula.get("recognition", {})
        latex = str(recognition.get("latex", formula.get("latex", "")) or "").strip()
        if not latex:
            return None
        before, after = self.find_nearest_text(formula, blocks)
        text = f"{before}\n\nФормула: {latex}\n\n{after}".strip()
        embedding_text = (
            f"Документ: {self.document}. Версия: {self.version}. Страница: {page}. "
            f"Тип: нормативная формула. Область: ВК. Система: внутренний водопровод. "
            f"Тема: гидравлический расчет. Нормативное описание: {before}. "
            f"Формула: {latex}. Дополнительный текст: {after}"
        )
        return {
            "chunk_id": f"{self.document}-page-{page:03}-formula-context-{index:03}",
            "type": "formula_context",
            "document": self.document,
            "document_id": self.document_id,
            "version": self.version,
            "page": page,
            "location": {"page": page, "bbox": formula.get("bbox"), "pdf": str(self.paths.pdf)},
            "content": {
                "text": text, "formula": latex, "before": before, "after": after,
                "engineering_context": {
                    "discipline": "ВК", "system": "Внутренний водопровод",
                    "purpose": before, "calculation_type": "Гидравлический расчет",
                },
            },
            "embedding_text": embedding_text,
            "metadata": {
                "source": self.document_id, "formula": True, "discipline": "ВК",
                "system": "internal_water_supply", "topic": "hydraulic_calculation",
                "created": datetime.now().isoformat(),
            },
        }

    def process_page(self, data):
        page = data["page"]
        blocks = data.get("text_blocks", data.get("blocks", []))
        chunks = []
        for i, block in enumerate(blocks, start=1):
            chunk = self.build_text_chunk(page, block, i)
            if chunk:
                chunks.append(chunk)
        for i, formula in enumerate(data.get("formulas", []), start=1):
            chunk = self.build_formula_context_chunk(page, formula, blocks, i)
            if chunk:
                chunks.append(chunk)
        return chunks

    def process_all_pages(self):
        input_dir = self.paths.enriched
        files = sorted(input_dir.glob("page_*_enriched.json")) if input_dir.exists() else []
        print("Pages found:", len(files))
        result = []
        for file in files:
            print("Processing:", file.name)
            result.extend(self.process_page(self.load_page(file)))
        return result

    def save(self, chunks):
        output = self.paths.chunks
        output.mkdir(parents=True, exist_ok=True)
        file = output / "all_chunks.json"
        with file.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print("Saved:", file)
        print("Total chunks:", len(chunks))
        return file


def main():
    builder = DocumentChunkBuilder()
    builder.save(builder.process_all_pages())


if __name__ == "__main__":
    main()
