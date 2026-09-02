"""Structured data contract for the engineering checking table."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

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
