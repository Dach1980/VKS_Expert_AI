"""Project Expert AI — version-aware FAISS + lexical normative retriever."""
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
    """Return normalized tokens, including simple Russian inflection normalization."""
    tokens = [token for token in re.findall(r"[\w№]+", str(text or "").lower()) if len(token) >= 3]
    normalized = []
    for token in tokens:
        if token.startswith("№"):
            normalized.append(token)
            continue
        for suffix in ("иями", "ами", "ями", "ого", "ему", "ому", "ими", "ыми", "ее", "ие", "ые", "ое", "ей", "ий", "ый", "ой", "ем", "им", "ым", "ом", "ам", "ям", "ах", "ях", "ов", "ев", "ы", "и", "а", "я", "у", "ю", "е", "о"):
            if len(token) - len(suffix) >= 4 and token.endswith(suffix):
                token = token[:-len(suffix)]
                break
        normalized.append(token)
    return normalized


def _query_text(query: str) -> str:
    """Extract the user's actual question from an enhanced RAG query."""
    match = re.search(r"(?:^|\n)Запрос:\s*\n?(.*?)(?:\n\s*$|\Z)", str(query or ""), re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else str(query or "").strip()


def _norm_term_set(query: str) -> set[str]:
    """Build high-value normalized search terms from the actual user question."""
    text = _query_text(query).lower()
    terms = set(lexical_tokens(text))
    if any(phrase in text for phrase in ("диаметр труб", "диаметр трубы", "внутренний диаметр", "наружный диаметр", "условный проход", "минимальный диаметр", "принимать диаметр")):
        terms.update(lexical_tokens("диаметр трубы условный проход"))
    if any(term in text for term in ("диаметр", "диаметру", "диаметры")):
        terms.update({"диаметр", "труб", "трубопровод", "условный", "проход", "ду", "dn"})
    return terms


def lexical_score(query: str, item: dict) -> float:
    """Rank exact normative terminology above generic semantic similarity."""
    content = item.get("content", {})
    text = content.get("text", "") if isinstance(content, dict) else content
    query_terms = _norm_term_set(query)
    text_terms = set(lexical_tokens(text))
    overlap = query_terms & text_terms
    if not overlap:
        return 0.0
    score = 0.34 * (len(overlap) / max(len(query_terms), 1))
    question = _query_text(query).lower()
    text_lower = str(text).lower()
    if any(phrase in question for phrase in ("диаметр труб", "диаметр трубы", "диаметру труб")):
        if "диаметр" in text_lower:
            score += 0.34
        if any(term in text_lower for term in ("условный проход", "ду", "dn")):
            score += 0.18
        if any(phrase in text_lower for phrase in ("диаметр труб", "диаметры труб", "диаметр трубопровода", "принимать диаметр")):
            score += 0.24
    normalized_query = " ".join(lexical_tokens(question))
    normalized_text = " ".join(lexical_tokens(text_lower))
    if normalized_query and normalized_query in normalized_text:
        score += 0.16
    return min(score, 1.0)


class Retriever:
    """FAISS retrieval against the registry-selected normative version."""

    def __init__(self, document_id: str | None = None, version_id: str | None = None, storage: KnowledgeStorage | None = None):
        self.storage = storage or KnowledgeStorage()
        self.document_id = self._resolve_document_id(document_id)
        self.version = self._resolve_version(version_id)
        self.version_id = str(self.version.get("id") or version_id or "")
        self.version_label = self._version_label(self.version)
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
        candidates = [document for document in self.storage.registry.get_all_documents() if self._number_group(document.get("number", "")) == target]
        if not candidates:
            raise ValueError(f"Нормативный документ не найден в реестре: {document_id or DEFAULT_DOCUMENT_NUMBER}")
        candidates.sort(key=lambda item: len(item.get("versions", [])), reverse=True)
        return str(candidates[0].get("id"))

    def _resolve_version(self, version_id: str | None) -> dict:
        document = self.storage.registry.get_document(self.document_id)
        versions = document.get("versions", []) if document else []
        if version_id:
            version = next((item for item in versions if item.get("id") == version_id), None)
            if version is not None:
                return version
        return self.storage.get_current_version(self.document_id)

    @staticmethod
    def _version_label(version: dict) -> str:
        """Build a stable human-readable version label from registry metadata."""
        change_number = version.get("change_number")
        if change_number not in (None, "", 0, "0"):
            value = str(change_number).strip()
            match = re.search(r"\d+", value)
            if match:
                return f"Изменение №{match.group(0)}"
        filename = str(version.get("file") or "")
        match = re.search(r"(?:изм|изменени[ея])\s*\.?\s*№?\s*(\d+)", filename, re.IGNORECASE)
        if match:
            return f"Изменение №{match.group(1)}"
        return "Без изменений"

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
        lexical_candidates = []
        for idx, item in enumerate(self.metadata):
            score = lexical_score(query, item)
            if score > 0:
                lexical_candidates.append((score, idx, item))
        lexical_candidates.sort(key=lambda row: row[0], reverse=True)
        for score, idx, item in lexical_candidates[: max(top_k * 5, 30)]:
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
            "version_label": self.version_label,
            "document_display_name": f"{r['item'].get('document', self.document_id)} — {self.version_label}",
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
    print(f"VERSION LABEL: {retriever.version_label}")
    for i, result in enumerate(retriever.search(query), 1):
        content = result.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        print(f"\nRESULT #{i} | page={result.get('page')} | score={result.get('score', 0):.5f} | source={result.get('source')}")
        print(text)
        if isinstance(content, dict) and content.get("formula"):
            print("FORMULA:", normalize_formula(content["formula"]))


if __name__ == "__main__":
    main()
