"""Higher-recall retrieval helpers for engineering norm-control audits."""
from __future__ import annotations

import re
from typing import Any, Callable


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def build_audit_queries(candidate: dict[str, Any]) -> list[str]:
    title = _clean(candidate.get("title"))
    description = _clean(candidate.get("description"))
    evidence = _clean(candidate.get("evidence_text"))
    queries: list[str] = []
    for value in (evidence, f"{title} {description}", title):
        if value and value not in queries:
            queries.append(value[:1200])
    # A short engineering query often retrieves the actual normative clause
    # better than a long VL description containing incidental words.
    compact = " ".join(x for x in (title, evidence) if x)
    if compact and compact not in queries:
        queries.append(compact[:800])
    return queries[:4]


def _text(result: dict[str, Any]) -> str:
    content = result.get("content", {})
    return _clean(content.get("text", "") if isinstance(content, dict) else content)


def retrieve_audit_context(retrievers: list[tuple[dict[str, Any], dict[str, Any], Any]], candidate: dict[str, Any], top_k: int = 6) -> list[dict[str, Any]]:
    """Run several focused searches across all active normative versions.

    Results are deduplicated by normative document/version/page/text and get a
    small multi-query consensus bonus. This improves recall without asking the
    LLM to reason over a large unrelated context.
    """
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
                key = (number, str(version.get("id") or ""), str(result.get("page", "")), text[:500])
                if not text:
                    continue
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
        item["score"] = item["best_score"] + min(0.18, max(0, item["query_hits"] - 1) * 0.06)
    ranked.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)
    return ranked[:top_k]
