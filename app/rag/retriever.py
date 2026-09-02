"""Project Expert AI — version-aware FAISS retriever."""
from __future__ import annotations

import json
import os
import re
import shutil

import faiss
import numpy as np

from app.knowledge.storage import KnowledgeStorage
from app.rag.embedding_client import EmbeddingClient

DEFAULT_DOCUMENT = "SP_30.13330"
TOP_K = 10


def normalize_formula(formula: str) -> str:
    return re.sub(r"\s+", " ", str(formula or "").replace("\\,", " ").replace("\\;", " ").replace("\\cdot", "*").replace("\\alpha", "α")).strip()


def is_formula_query(query: str) -> bool:
    keywords = ("формул", "определяется", "определить", "следует определять", "расчет", "расчетный", "значение", "коэффициент", "принимается", "вычисляется")
    return sum(1 for word in keywords if word in query.lower()) >= 2


def formula_score(query: str, item: dict) -> float:
    if item.get("type") != "formula_context":
        return 0.0
    content = item.get("content", {})
    text = str(content.get("text", "") if isinstance(content, dict) else content).lower()
    score = sum(0.05 for word in query.lower().split() if len(word) > 3 and word in text)
    if "максимальный" in query.lower() and "максимальный" in text:
        score += 0.25
    if "расчетный" in query.lower() and "расчетный" in text:
        score += 0.25
    if "формула" in query.lower():
        score += 0.2
    return min(score, 0.5)


class Retriever:
    """FAISS retrieval against a concrete indexed normative version."""

    def __init__(self, document_id: str = DEFAULT_DOCUMENT, version_id: str | None = None, storage: KnowledgeStorage | None = None):
        self.storage = storage or KnowledgeStorage()
        self.document_id = document_id
        self.version_id = version_id or self.storage.get_current_version(document_id).get("id")
        self.paths = self.storage.paths(document_id, self.version_id)
        self.index_file = self.paths.embeddings / "index.faiss"
        self.metadata_file = self.paths.embeddings / "metadata.json"
        if not self.index_file.exists():
            raise FileNotFoundError(f"Индекс нормативной версии не найден: {self.index_file}")
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Метаданные нормативного индекса не найдены: {self.metadata_file}")

        temp_index_file = self.storage.project_root / f".faiss_read_{os.getpid()}_{id(self)}.index"
        try:
            shutil.copy2(self.index_file, temp_index_file)
            self.index = faiss.read_index(str(temp_index_file))
        finally:
            temp_index_file.unlink(missing_ok=True)

        self.metadata = json.loads(self.metadata_file.read_text(encoding="utf-8-sig"))
        self.client = EmbeddingClient()

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        vector = np.asarray([self.client.embed(query)], dtype="float32")
        faiss.normalize_L2(vector)
        scores, ids = self.index.search(vector, min(top_k, self.index.ntotal))
        merged = []
        formula_mode = is_formula_query(query)
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = self.metadata[idx]
            final_score = float(score)
            if formula_mode and item.get("type") == "formula_context":
                final_score += 0.30
            merged.append({"item": item, "score": final_score, "source": "faiss"})
        if formula_mode:
            for item in self.metadata:
                score = formula_score(query, item)
                if score > 0:
                    merged.append({"item": item, "score": score + 0.35, "source": "formula"})
        merged.sort(key=lambda x: x["score"], reverse=True)
        return [{
            "document": r["item"].get("document", self.document_id),
            "version": self.version_id,
            "page": r["item"].get("page", 0),
            "type": r["item"].get("type", "text"),
            "source": r["source"],
            "score": r["score"],
            "content": r["item"].get("content", ""),
            # Keep parser metadata available to the normative requirement layer.
            # It may contain the clause/section when the text chunk itself does not.
            "metadata": r["item"].get("metadata", {}),
            "chunk_id": r["item"].get("chunk_id"),
        } for r in merged[:top_k]]


def load_index(document_id: str = DEFAULT_DOCUMENT, version_id: str | None = None):
    return Retriever(document_id, version_id).index


def load_metadata(document_id: str = DEFAULT_DOCUMENT, version_id: str | None = None):
    return Retriever(document_id, version_id).metadata


def main():
    query = input("\nSEARCH QUERY:\n\n")
    for i, result in enumerate(Retriever().search(query), 1):
        content = result.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        print(f"\nRESULT #{i} | page={result.get('page')} | score={result.get('score', 0):.5f}")
        print(text)
        if isinstance(content, dict) and content.get("formula"):
            print("FORMULA:", normalize_formula(content["formula"]))


if __name__ == "__main__":
    main()
