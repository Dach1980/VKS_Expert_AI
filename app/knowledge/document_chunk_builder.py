"""VKS Expert AI — Document Chunk Builder v9."""

import json
from datetime import datetime

from app.knowledge.storage import KnowledgeStorage


class DocumentChunkBuilder:
    def __init__(self, document_id="SP_30.13330", version_id=None, storage=None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.paths = self.storage.paths(document_id, version_id)
        document = self.storage.get_document(document_id)
        version = self.storage.get_version(document_id, version_id)
        self.document = document["number"]
        self.version = version["id"]
        self.normative_metadata = self._build_normative_metadata(document, version)
        self.normative_document = self._load_normative_document()
        self.page_normative_map = self._build_page_normative_map()

    def _build_normative_metadata(self, document, version):
        version_meta = self.storage.get_version_metadata(self.document_id, self.version)
        return {
            "document": {
                "id": self.document_id,
                "number": document.get("number"),
                "title": document.get("title"),
                "document_type": document.get("document_type"),
            },
            "version": {
                "id": version.get("id"),
                "edition": version_meta.get("edition", {}),
            },
            "source": version_meta.get("source", {}),
        }

    def _load_normative_document(self):
        if not self.paths.structured.exists():
            raise RuntimeError(
                "Normative JSON 2.0 не найден. Индексация разрешена только после Validator PASS."
            )
        with self.paths.structured.open("r", encoding="utf-8") as f:
            document = json.load(f)
        if document.get("schema_version") != "2.0":
            raise RuntimeError("Ожидался Normative JSON 2.0.")
        return document

    def _build_page_normative_map(self):
        mapping = {}
        requirements = {
            item.get("requirement_id"): item
            for item in self.normative_document.get("requirements", [])
            if item.get("requirement_id")
        }
        references = {
            item.get("reference_id"): item
            for item in self.normative_document.get("references", [])
            if item.get("reference_id")
        }
        for section in self.normative_document.get("structure", {}).get("sections", []):
            for clause in section.get("clauses", []):
                clause_number = clause.get("number")
                for page in range(int(clause.get("page_start", 1)), int(clause.get("page_end", 1)) + 1):
                    entry = mapping.setdefault(page, {"clauses": [], "requirements": [], "references": []})
                    if clause_number and clause_number not in entry["clauses"]:
                        entry["clauses"].append(clause_number)
                    for req_id in clause.get("requirements", []):
                        if req_id in requirements and req_id not in entry["requirements"]:
                            entry["requirements"].append(req_id)
                    for ref_id in clause.get("references", []):
                        if ref_id in references and ref_id not in entry["references"]:
                            entry["references"].append(ref_id)
        return mapping

    def _normative_page_metadata(self, page):
        entry = self.page_normative_map.get(int(page), {})
        return {
            "clause_ids": list(entry.get("clauses", [])),
            "requirement_ids": list(entry.get("requirements", [])),
            "reference_ids": list(entry.get("references", [])),
        }

    def load_page(self, file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _metadata(self, **extra):
        value = {
            "normative": self.normative_metadata,
            "normative_json": self._normative_page_metadata(extra.pop("page", 0)) if extra.get("page") else {},
            "created": datetime.now().isoformat(),
        }
        value.update(extra)
        return value

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
            "embedding_text": (
                f"Документ: {self.document}. Версия: {self.version}. "
                f"Редакция: {self.normative_metadata['version']['edition'].get('date', '—')}. "
                f"Страница: {page}. Тип: нормативный текст. Текст: {text}"
            ),
            "metadata": self._metadata(page=page),
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
            f"Документ: {self.document}. Версия: {self.version}. "
            f"Редакция: {self.normative_metadata['version']['edition'].get('date', '—')}. "
            f"Страница: {page}. Тип: нормативная формула. "
            f"Область: ВК. Система: внутренний водопровод. "
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
                "text": text,
                "formula": latex,
                "before": before,
                "after": after,
                "engineering_context": {
                    "discipline": "ВК",
                    "system": "Внутренний водопровод",
                    "purpose": before,
                    "calculation_type": "Гидравлический расчет",
                },
            },
            "embedding_text": embedding_text,
            "metadata": self._metadata(
                page=page,
                formula=True,
                discipline="ВК",
                system="internal_water_supply",
                topic="hydraulic_calculation",
            ),
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
