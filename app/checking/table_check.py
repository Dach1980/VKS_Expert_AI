"""Structured data contract for the engineering checking table."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import re

from app.checking.engineering_values import NormalizedEngineeringValue, normalize_engineering_value


@dataclass
class TableCheckRow:
    parameter: str = ""
    project_value_raw: str = ""
    project_value: float | None = None
    project_unit: str = ""
    project_kind: str = ""
    normative_value_raw: str = ""
    normative_value: float | None = None
    normative_unit: str = ""
    normative_kind: str = ""
    normative_requirement: str = ""
    comparison: str = "не определено"
    result: str = "unchecked"
    norm: str = ""
    clause: str = ""
    page: int | str = ""
    source_row: str = ""
    source_context: str = ""
    evidence_text: str = ""
    confidence: float | None = None
    normative_sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalized(raw: Any, parameter: str, source: str = "") -> NormalizedEngineeringValue:
    return normalize_engineering_value(raw, parameter=parameter, source=source)


def deterministic_numeric_comparison(candidate: dict[str, Any], decision: dict[str, Any], requirements: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Apply only an unambiguous numeric requirement comparison."""
    requirements = requirements or []
    parameter = str(decision.get("parameter") or candidate.get("parameter") or "").strip()
    project_raw = str(decision.get("project_value") or candidate.get("project_value") or "").strip()
    project = _normalized(project_raw, parameter, str(candidate.get("source_row") or candidate.get("evidence_text") or ""))
    if project.value is None or not parameter:
        return decision

    parameter_words = {word.lower() for word in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", parameter)}
    for requirement in requirements:
        normative_value = requirement.get("normative_value")
        operator = str(requirement.get("operator") or "")
        if normative_value is None or operator not in {">=", "<=", "="}:
            continue
        text = str(requirement.get("requirement") or "")
        overlap = sum(word in text.lower() for word in parameter_words)
        if parameter_words and overlap == 0:
            continue
        normative_unit = str(requirement.get("normative_unit") or "")
        requirement_raw = f"{normative_value:g} {normative_unit}".strip()
        norm = _normalized(requirement_raw, parameter, text)
        if norm.value is None:
            continue
        if project.unit and norm.unit and project.unit != norm.unit:
            continue
        if project.kind != norm.kind and not ({project.kind, norm.kind} <= {"number", "length"}):
            continue
        if operator == ">=":
            ok, comparison = project.value >= norm.value, ("в пределах" if project.value >= norm.value else "ниже")
        elif operator == "<=":
            ok, comparison = project.value <= norm.value, ("в пределах" if project.value <= norm.value else "выше")
        else:
            ok = project.value == norm.value
            comparison = "равно" if ok else ("выше" if project.value > norm.value else "ниже")
        updated = dict(decision)
        updated["type"] = "compliant" if ok else "violation"
        updated["norm"] = str(requirement.get("norm") or decision.get("norm") or "")
        updated["clause"] = str(requirement.get("clause") or decision.get("clause") or "")
        updated["normative_requirement"] = text
        updated["normative_value"] = requirement_raw
        updated["normative_unit"] = normative_unit or str(decision.get("normative_unit") or "")
        updated["comparison"] = comparison
        updated["confidence"] = max(float(decision.get("confidence") or 0.0), 0.9)
        if not updated.get("sheet"):
            updated["sheet"] = candidate.get("page") or ""
        if updated["type"] == "violation":
            updated["recommendation"] = str(decision.get("recommendation") or "Привести проектное решение в соответствие с указанным нормативным требованием.")
        return updated
    return decision


def build_table_check_row(candidate: dict[str, Any], decision: dict[str, Any], page: int | str, sources: list[dict[str, Any]] | None = None) -> TableCheckRow:
    parameter = str(decision.get("parameter") or candidate.get("parameter") or "").strip()
    project_raw = str(decision.get("project_value") or candidate.get("project_value") or "").strip()
    project = _normalized(project_raw, parameter, str(candidate.get("source_row") or candidate.get("evidence_text") or ""))
    norm_raw = str(decision.get("normative_value") or "").strip()
    norm = _normalized(norm_raw, parameter)
    confidence = decision.get("confidence", candidate.get("confidence"))
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    return TableCheckRow(
        parameter=parameter,
        project_value_raw=project.raw,
        project_value=project.value,
        project_unit=str(decision.get("project_unit") or project.unit),
        project_kind=project.kind,
        normative_value_raw=norm.raw,
        normative_value=norm.value,
        normative_unit=str(decision.get("normative_unit") or norm.unit),
        normative_kind=norm.kind,
        normative_requirement=str(decision.get("normative_requirement") or ""),
        comparison=str(decision.get("comparison") or "не определено"),
        result=str(decision.get("type") or "unchecked"),
        norm=str(decision.get("norm") or ""),
        clause=str(decision.get("clause") or ""),
        page=page,
        source_row=str(candidate.get("source_row") or ""),
        source_context=str(candidate.get("source_context") or ""),
        evidence_text=str(candidate.get("evidence_text") or ""),
        confidence=confidence,
        normative_sources=sources or [],
    )
