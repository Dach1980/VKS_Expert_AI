"""Deterministic routing from a project fact to applicable normative SPs."""
from __future__ import annotations

import re
from typing import Any

from app.skills.registry import get_skill


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_external(candidate: dict[str, Any]) -> bool:
    text = " ".join(_text(candidate.get(key)) for key in ("parameter", "title", "description", "source_context", "evidence_text", "project_value"))
    external_terms = ("наружн", "внутриплощад", "колодец", "от колодца", "до точки подключения", "сети нк", "сети нв")
    return any(term in text for term in external_terms)


def _is_water(candidate: dict[str, Any]) -> bool:
    text = " ".join(_text(candidate.get(key)) for key in ("parameter", "title", "description", "source_context", "evidence_text"))
    water_terms = ("водопровод", "водоснабж", "водомер", "поливоч", "вода", "ввод вод")
    wastewater_terms = ("канализац", "сточн", "выпуск к", "стояк к", "к1", "к2", "дождев")
    water_hits = sum(term in text for term in water_terms)
    wastewater_hits = sum(term in text for term in wastewater_terms)
    return water_hits > wastewater_hits


def route_candidate(candidate: dict[str, Any], skill_id: str = "vk_wastewater") -> dict[str, Any]:
    """Return the allowed SP set and routing reason for one project fact.

    Routing is intentionally conservative: it never invents a normative source.
    If the fact is ambiguous, the skill's cross-boundary sources are returned and
    the downstream requirement selector must prove applicability.
    """
    skill = get_skill(skill_id)
    routing = skill.get("routing", {})
    external = _is_external(candidate)
    water = _is_water(candidate)
    if water and external:
        key = "external_water"
    elif water:
        key = "internal_water"
    elif external:
        key = "external_wastewater"
    else:
        key = "internal_wastewater"
    norms = list(routing.get(key) or routing.get("cross_boundary") or skill["normative_documents"])
    return {
        "skill_id": skill["id"],
        "scope": key,
        "segment": "external" if external else "internal",
        "system": "water" if water else "wastewater",
        "normative_documents": norms,
        "reason": f"{skill['name']}: {'наружный' if external else 'внутренний'} {'водопровод' if water else 'водоотвод'}",
        "confidence": 0.9 if (external or water) else 0.65,
    }


def filter_retrievers(retrievers: list[tuple[dict[str, Any], dict[str, Any], Any]], route: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any], Any]]:
    allowed = {str(value).strip().lower() for value in route.get("normative_documents", [])}
    result = []
    for item in retrievers:
        document, version, _ = item
        number = str(document.get("number") or document.get("id") or "").strip().lower()
        title = str(document.get("title") or "").strip().lower()
        if number in allowed or any(number and number in value for value in allowed) or any(value and value in title for value in allowed):
            result.append(item)
    return result
