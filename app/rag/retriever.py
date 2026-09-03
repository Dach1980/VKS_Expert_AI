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

DEFAULT_DOCUMENT_NUMBER = "СП 30.13330.2020"
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


def lexical_tokens(text: str) -> list[str]:
    """Return meaningful Cyrillic/Latin/numeric tokens for lexical retrieval."""
    return [token for token in re.findall(r"[\w№]+", str(text or "").lower()) if len(token) >= 3]


def lexical_score(query: str, item: dict) -> float:
    """Small lexical signal to recover exact normative terms missed by embeddings."""
    content = item.get("content", {})
    text = content.get("text", "") if isinstance(content, dict) else content
    query_tokens = set(lexical_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(lexical_tokens(text))
    overlap = query_tokens & text_tokens
    if not overlap:
        return 0.0
    coverage = len(overlap) / len(query_tokens)
    score = 0.22 * coverage
    normalized_query = " ".join(lexical_tokens(query))
    normalized_text = " ".join(lexical_tokens(text))
    if normalized_query and normalized_query in normalized_text:
        score += 0.16
    return min(score, 0.38)


class Retriever:
    """FAISS retrieval against the registry-selected normative version."""

    def __init__(self, document_id: str | None = None, version_id: str | None = None, storage: KnowledgeStorage | None = None):
        self.storage = storage or KnowledgeStorage()
        self.document_id = self._resolve_document_id(document_id)
        self.version_id = version_id or self.storage.get_current_version(self.document_id).get("id")
        self.paths = self.storage.paths(self.document_id, self.version_id)
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

    def _resolve_document_id(self, document_id: str | None) -> str:
        if document_id and self.storage.registry.get_document(document_id) is not None:
            return document_id
        target = self._number_group(document_id or DEFAULT_DOCUMENT_NUMBER)
        candidates = [
            document for document in self.storage.registry.get_all_documents()
            if self._number_group(document.get("number", "")) == target
        ]
        if not candidates:
            raise ValueError(f"Нормативный документ не найден в реестре: {document_id or DEFAULT_DOCUMENT_NUMBER}")
        candidates.sort(key=lambda item: len(item.get("versions", [])), reverse=True)
        return str(candidates[0].get("id"))

    @staticmethod
    def _number_group(value: str) -> str:
        normalized = re.sub(r"\s+", " ", str(value or "")).strip().lower()
        match = re.search(r"(?:сп|гост(?: р)?|снип|тр|фз)\s*[0-9]+\.[0-9]+", normalized, re.IGNORECASE)
        return re.sub(r"\s+", " ", match.group(0)).strip() if match else normalized

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        vector = np.asarray([self.client.embed(query)], dtype="float32")
        faiss.normalize_L2(vector)
        candidate_k = min(max(top_k * 4, 20), self.index.ntotal)
        scores, ids = self.index.search(vector, candidate_k)
        merged = {}
        formula_mode = is_formula_query(query)
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = self.metadata[idx]
            final_score = float(score) + lexical_score(query, item)
            if formula_mode and item.get("type") == "formula_context":
                final_score += 0.30
            merged[idx] = {"item": item, "score": final_score, "source": "faiss"}

        # Also inspect metadata outside the FAISS shortlist. This catches exact
        # normative terms (e.g. "диаметр", "условный проход") when the semantic
        # embedding ranks introductory/adjacent text above the actual clause.
        lexical_candidates = []
        for idx, item in enumerate(self.metadata):
            score = lexical_score(query, item)
            if score > 0:
                lexical_candidates.append((score, idx, item))
        lexical_candidates.sort(key=lambda row: row[0], reverse=True)
        for score, idx, item in lexical_candidates[: max(top_k * 3, 20)]:
            current = merged.get(idx)
            candidate = {"item": item, "score": score + 0.35, "source": "lexical"}
            if current is None or candidate["score"] > current["score"]:
                merged[idx] = candidate

        if formula_mode:
            for idx, item in enumerate(self.metadata):
                score = formula_score(query, item)
                if score > 0:
                    candidate = {"item": item, "score": score + 0.35, "source": "formula"}
                    current = merged.get(idx)
                    if current is None or candidate["score"] > current["score"]:
                        merged[idx] = candidate
        ranked = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        return [{
            "document": r["item"].get("document", self.document_id),
            "version": self.version_id,
            "page": r["item"].get("page", 0),
            "type": r["item"].get("type", "text"),
            "source": r["source"],
            "score": r["score"],
            "content": r["item"].get("content", ""),
            "metadata": r["item"].get("metadata", {}),
            "chunk_id": r["item"].get("chunk_id"),
        } for r in ranked[:top_k]]


def load_index(document_id: str | None = None, version_id: str | None = None):
    return Retriever(document_id, version_id).index


def load_metadata(document_id: str | None = None, version_id: str | None = None):
    return Retriever(document_id, version_id).metadata


def main():
    query = input("\nSEARCH QUERY:\n\n")
    retriever = Retriever()
    print(f"DOCUMENT: {retriever.document_id}")
    print(f"VERSION: {retriever.version_id}")
    for i, result in enumerate(retriever.search(query), 1):
        content = result.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        print(f"\nRESULT #{i} | page={result.get('page')} | score={result.get('score', 0):.5f}")
        print(text)
        if isinstance(content, dict) and content.get("formula"):
            print("FORMULA:", normalize_formula(content["formula"]))


if __name__ == "__main__":
    main()