"""Skill-routed, value-aware retrieval helpers for engineering norm-control audits."""
from __future__ import annotations

import re
from typing import Any

from app.checking.engineering_values import normalize_engineering_value
from app.rag.normative_router import filter_retrievers, route_candidate


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
    normalized = normalize_engineering_value(project_value, parameter)
    machine_value = ""
    if normalized.value is not None:
        machine_value = f"{normalized.kind} {normalized.value:g} {normalized.unit}".strip()
    # The first query is deliberately rich enough to retrieve the requirement in
    # one embedding request. A fallback query is used only when the first pass
    # produces no usable normative requirement. This avoids multiplying LM
    # Studio embedding calls for every page/candidate.
    primary = _clean(f"{parameter} {project_value} {machine_value} {evidence} {context}")
    fallback = _clean(f"{parameter} {title} {description} {context}")
    queries: list[str] = []
    for value in (primary, fallback):
        if value and value not in queries:
            queries.append(value[:1400])
    return queries


def _text(result: dict[str, Any]) -> str:
    content = result.get("content", {})
    return _clean(content.get("text", "") if isinstance(content, dict) else content)


def _value_relevance(candidate: dict[str, Any], text: str) -> float:
    parameter = _clean(candidate.get("parameter"))
    raw = _clean(candidate.get("project_value") or candidate.get("evidence_text"))
    normalized = normalize_engineering_value(raw, parameter)
    query = " ".join(_clean(candidate.get(x)) for x in ("parameter", "title", "evidence_text", "source_context"))
    qwords, twords = _keywords(query), _keywords(text)
    keyword_score = min(0.22, len(qwords & twords) * 0.025)
    qnums = _numbers(raw)
    if normalized.value is not None:
        qnums.add(f"{normalized.value:g}")
    tnums = _numbers(text)
    numeric_score = 0.10 if qnums and qnums & tnums else 0.0
    unit = normalized.unit.lower()
    unit_score = 0.08 if unit and unit in text.lower() else 0.0
    kind_terms = {"diameter": ("диаметр", "условный проход", "dn"), "slope": ("уклон",), "flow": ("расход",), "pressure": ("давление",), "length": ("длина",), "count": ("количество", "число")}
    kind_score = 0.05 if any(term in text.lower() for term in kind_terms.get(normalized.kind, ())) else 0.0
    return keyword_score + numeric_score + unit_score + kind_score


def _has_concrete_requirement(result: dict[str, Any]) -> bool:
    """Cheap pre-check used before paying for a second embedding query."""
    text = _text(result)
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    clause = any(re.search(r"\d+(?:\.\d+)+", str(metadata.get(key) or "")) for key in ("clause", "paragraph", "point", "section"))
    clause = clause or bool(re.search(r"(?:пункт|п\.)\s*\d+(?:\.\d+)+", text, re.IGNORECASE))
    return clause


def retrieve_audit_context(
    retrievers: list[tuple[dict[str, Any], dict[str, Any], Any]],
    candidate: dict[str, Any],
    top_k: int = 6,
    skill_id: str = "vk_wastewater",
) -> list[dict[str, Any]]:
    """Retrieve only from normative documents allowed by the selected skill and route."""
    route = route_candidate(candidate, skill_id)
    scoped_retrievers = filter_retrievers(retrievers, route)
    if not scoped_retrievers:
        return []
    candidate["normative_route"] = route
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    queries = build_audit_queries(candidate)

    def run_query(query: str) -> None:
        for document, version, retriever in scoped_retrievers:
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

    if queries:
        run_query(queries[0])

    # Only pay for the fallback embedding query when the first retrieval did not
    # expose any chunk carrying a concrete clause. This is the main performance
    # guard for full-document audits.
    if queries and not any(_has_concrete_requirement(item) for item in merged.values()):
        run_query(queries[1])

    ranked = list(merged.values())
    for item in ranked:
        value_bonus = _value_relevance(candidate, _text(item))
        item["value_relevance"] = value_bonus
        item["route_scope"] = route["scope"]
        item["route_reason"] = route["reason"]
        item["score"] = item["best_score"] + min(0.20, max(0, item["query_hits"] - 1) * 0.05) + value_bonus
    ranked.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)
    return ranked[:top_k]
