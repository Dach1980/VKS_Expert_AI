"""Higher-recall, value-aware retrieval helpers for engineering norm-control audits."""
from __future__ import annotations
import re
from typing import Any


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _numbers(value: str) -> set[str]:
    text = value.replace("×", "x").replace(",", ".")
    return {x.rstrip(".") for x in re.findall(r"(?<![A-Za-zА-Яа-я])\d+(?:\.\d+)?", text)}


def _keywords(value: str) -> set[str]:
    stop = {"что", "как", "для", "при", "если", "или", "это", "из", "по", "на", "и", "в", "с", "не", "до", "от"}
    return {x for x in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{4,}", value.lower()) if x not in stop}


def build_audit_queries(candidate: dict[str, Any]) -> list[str]:
    title = _clean(candidate.get("title"))
    description = _clean(candidate.get("description"))
    evidence = _clean(candidate.get("evidence_text"))
    parameter = _clean(candidate.get("parameter"))
    project_value = _clean(candidate.get("project_value"))
    context = _clean(candidate.get("source_context"))
    queries: list[str] = []
    for value in (
        f"{parameter} {project_value} {evidence}",
        f"{parameter} {title} {description}",
        f"{parameter} {context}",
        title,
    ):
        value = _clean(value)
        if value and value not in queries:
            queries.append(value[:1200])
    return queries[:5]


def _text(result: dict[str, Any]) -> str:
    content = result.get("content", {})
    return _clean(content.get("text", "") if isinstance(content, dict) else content)


def _value_relevance(candidate: dict[str, Any], text: str) -> float:
    """Prefer clauses that discuss the same parameter and, when useful, units/numbers.

    Numeric equality is only a retrieval signal. The final LLM decision still
    determines whether the project value actually violates the requirement.
    """
    query = " ".join(_clean(candidate.get(x)) for x in ("parameter", "title", "evidence_text", "source_context"))
    qwords, twords = _keywords(query), _keywords(text)
    keyword_score = min(0.22, len(qwords & twords) * 0.025)
    qnums = _numbers(_clean(candidate.get("project_value") or candidate.get("evidence_text")))
    tnums = _numbers(text)
    numeric_score = 0.10 if qnums and qnums & tnums else 0.0
    unit_score = 0.08 if any(u in query.lower() and u in text.lower() for u in ("мм", "м3/ч", "м³/ч", "л/с", "%", "кпа", "м", "i=")) else 0.0
    return keyword_score + numeric_score + unit_score


def retrieve_audit_context(retrievers: list[tuple[dict[str, Any], dict[str, Any], Any]], candidate: dict[str, Any], top_k: int = 6) -> list[dict[str, Any]]:
    """Retrieve several queries across all active norms, then rerank by evidence relevance."""
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    queries = build_audit_queries(candidate)
    for query_index, query in enumerate(queries):
        for document, version, retriever in retrievers:
            number = str(document.get("number") or document.get("id") or "")
            title = str(document.get("title") or "")
            try:
                results = retriever.search(query, top_k=top_k)
            except Exception:
                continue
            for result in results:
                text = _text(result)
                if not text:
                    continue
                key = (number, str(version.get("id") or ""), str(result.get("page", "")), text[:500])
                item = merged.get(key)
                if item is None:
                    item = dict(result)
                    item["norm_number"] = number
                    item["norm_title"] = title
                    item["version"] = str(version.get("id") or result.get("version") or "")
                    item["query_hits"] = 0
                    item["best_score"] = float(result.get("score", 0) or 0)
                    merged[key] = item
                item["query_hits"] += 1
                item["best_score"] = max(item["best_score"], float(result.get("score", 0) or 0))
    ranked = list(merged.values())
    for item in ranked:
        text = _text(item)
        value_bonus = _value_relevance(candidate, text)
        item["value_relevance"] = value_bonus
        item["score"] = item["best_score"] + min(0.20, max(0, item["query_hits"] - 1) * 0.05) + value_bonus
    ranked.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)
    return ranked[:top_k]
