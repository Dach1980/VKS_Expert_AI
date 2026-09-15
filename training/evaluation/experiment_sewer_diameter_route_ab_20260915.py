"""Minimal deterministic A/B experiment for the saved sewer_diameter routing bug.

This is an experiment harness only. It does not modify production routing or the
Qwen prompt. It compares current routing with an experiment-only corrected rule
on the exact saved production candidate and verifies the normative-document gate.
"""
from __future__ import annotations

import json


CANDIDATE = {
    "parameter": "диаметр выпуска",
    "title": "Диаметры",
    "description": "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
    "source_context": (
        "Бытовые стоки отводятся системой внутренней самотечной бытовой "
        "канализации по пяти выпускам Ø110мм в внутриплощадочную сеть "
        "бытовой канализации Ø160 мм."
    ),
    "evidence_text": (
        "Бытовые стоки отводятся системой внутренней самотечной бытовой "
        "канализации по пяти выпускам Ø110мм в внутриплощадочную сеть "
        "бытовой канализации Ø160 мм."
    ),
    "project_value": "Ø110мм",
}

ROUTE_DOCS = {
    "internal_wastewater": ["СП 30.13330.2020"],
    "external_wastewater": ["СП 32.13330.2018"],
}

FALSE_REQUIREMENT = {
    "norm": "СП 32.13330.2018",
    "clause": "6.3.5",
    "text": "Размеры в плане колодцев на сети водоотведения поверхностного стока ... 1000 мм",
}


def _candidate_text(candidate: dict[str, str]) -> str:
    return " ".join(
        str(candidate.get(key) or "").strip().lower()
        for key in (
            "parameter",
            "title",
            "description",
            "source_context",
            "evidence_text",
            "project_value",
        )
    )


def current_external(candidate: dict[str, str]) -> bool:
    """Exact current production rule copied for the A side of the experiment."""
    text = _candidate_text(candidate)
    external_terms = (
        "наружн",
        "внутриплощад",
        "колодец",
        "от колодца",
        "до точки подключения",
        "сети нк",
        "сети нв",
    )
    return any(term in text for term in external_terms)


def corrected_external(candidate: dict[str, str]) -> bool:
    """Experiment-only guard: explicit internal wastewater evidence wins.

    The purpose is deliberately narrow: demonstrate the effect of removing the
    false external classification for this saved candidate. This function is not
    imported by production code.
    """
    text = _candidate_text(candidate)
    explicit_internal = "внутренн" in text and "канализац" in text
    external = current_external(candidate)
    return external and not explicit_internal


def route(external: bool) -> dict[str, object]:
    scope = "external_wastewater" if external else "internal_wastewater"
    return {
        "scope": scope,
        "segment": "external" if external else "internal",
        "normative_documents": ROUTE_DOCS[scope],
    }


def main() -> None:
    before = route(current_external(CANDIDATE))
    after = route(corrected_external(CANDIDATE))

    result = {
        "experiment": "sewer_diameter_route_ab",
        "date": "2026-09-15",
        "production_code_changed": False,
        "qwen_prompt_changed": False,
        "candidate": CANDIDATE,
        "before": before,
        "after": after,
        "checks": {
            "before_scope_is_external_wastewater": before["scope"] == "external_wastewater",
            "after_scope_is_internal_wastewater": after["scope"] == "internal_wastewater",
            "sp32_6_3_5_allowed_before": FALSE_REQUIREMENT["norm"] in before["normative_documents"],
            "sp32_6_3_5_excluded_after": FALSE_REQUIREMENT["norm"] not in after["normative_documents"],
        },
        "qwen_input_gate": {
            "before": {
                "sp32_6_3_5_can_enter": True,
                "reason": "The saved production finding selected СП 32.13330.2018 §6.3.5 after external_wastewater routing.",
            },
            "after": {
                "sp32_6_3_5_can_enter": False,
                "reason": "The corrected route scopes the candidate to СП 30.13330.2020; СП 32.13330.2018 is outside the scoped retrievers.",
            },
        },
    }
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
