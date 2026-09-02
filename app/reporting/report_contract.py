"""Single public report contract shared by the UI and IOS 3.1 exporters.

The checker may persist every machine result for traceability, but the user-facing
report must contain only confirmed remarks. Unchecked and compliant observations
remain separate datasets and are never promoted to remarks.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

REPORT_SCHEMA_VERSION = "1.1"


def _normalise_finding(finding: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(finding)
    item.setdefault("parameter", "")
    item.setdefault("project_value", "")
    item.setdefault("project_value_raw", item.get("project_value", ""))
    item.setdefault("normative_requirement", "")
    item.setdefault("normative_value_raw", item.get("normative_value", ""))
    item.setdefault("norm", "")
    item.setdefault("clause", "")
    item.setdefault("recommendation", "")
    item.setdefault("sheet", item.get("page", ""))
    item.setdefault("page", "")
    item.setdefault("severity", "minor")
    item.setdefault("type", "unchecked")
    return item


def _build_diagnostics(report: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact diagnostic view of the Skill → RAG → decision chain.

    This deliberately does not turn diagnostic observations into remarks. The
    diagnostic matrix shows where evidence exists and how many results reached
    each downstream stage using the data persisted by the checker.
    """
    matrix = []
    for item in report.get("check_matrix") or []:
        if not isinstance(item, dict):
            continue
        check_id = str(item.get("id") or "")
        related = [x for x in findings if str(x.get("check_id") or "") == check_id]
        rag_hits = sum(bool(x.get("normative_sources")) for x in related)
        requirements = sum(len(x.get("normative_requirements") or []) for x in related)
        decisions = {"violation": 0, "compliant": 0, "unchecked": 0}
        for finding in related:
            kind = str(finding.get("type") or "unchecked")
            if kind in decisions:
                decisions[kind] += 1
        matrix.append({
            "id": check_id,
            "name": item.get("name", ""),
            "visual_candidates": int(item.get("candidates", 0) or 0),
            "rag_candidates": rag_hits,
            "normative_requirements": requirements,
            "decisions": decisions,
            "remarks": decisions["violation"],
            "status": item.get("status") or ("evidence_found" if related else "no_evidence_candidate"),
        })
    return {
        "chain": ["Skill", "visual_candidates", "RAG", "normative_requirements", "decision", "remark"],
        "matrix": matrix,
        "note": "Диагностика не является частью замечаний. Отсутствие кандидата или нормативного требования означает необходимость проверки цепочки, а не нарушение проекта.",
    }


def prepare_public_report(report: dict[str, Any]) -> dict[str, Any]:
    """Convert internal checker output into the canonical user-facing report."""
    public = deepcopy(report)
    raw = report.get("results") or report.get("checks") or []
    findings = [_normalise_finding(x) for x in raw if isinstance(x, dict)]

    remarks = [x for x in findings if x.get("type") == "violation"]
    compliant = [x for x in findings if x.get("type") == "compliant"]
    review = [x for x in findings if x.get("type") == "unchecked"]

    public["schema_version"] = REPORT_SCHEMA_VERSION
    public["results"] = remarks
    public["remarks"] = remarks
    public["compliant_results"] = compliant
    public["review_results"] = review

    scope = report.get("check_scope") or {}
    source_summary = report.get("summary") or {}
    try:
        pages = int(scope.get("pages_checked", 0) or 0)
    except (TypeError, ValueError):
        pages = 0
    if pages <= 0:
        try:
            pages = int(scope.get("pages_available", 0) or 0)
        except (TypeError, ValueError):
            pages = 0
    if pages <= 0:
        try:
            pages = int(source_summary.get("pages", 0) or 0)
        except (TypeError, ValueError):
            pages = 0

    try:
        pages_available = int(scope.get("pages_available", pages) or pages)
    except (TypeError, ValueError):
        pages_available = pages

    public["summary"] = {
        "pages": pages,
        "pages_available": pages_available,
        "total": len(remarks),
        "violations": len(remarks),
        "critical": sum(x.get("severity") == "critical" for x in remarks),
        "major": sum(x.get("severity") == "major" for x in remarks),
        "minor": sum(x.get("severity") == "minor" for x in remarks),
        "compliant": len(compliant),
        "unchecked": len(review),
    }
    public["diagnostics"] = _build_diagnostics(report, findings)
    public["report_definition"] = {
        "remark_status": "violation",
        "remark_fields": [
            "id", "page", "sheet", "parameter", "project_value_raw",
            "normative_requirement", "norm", "clause", "type",
            "severity", "recommendation", "evidence_image", "image",
        ],
        "evidence_numbering": "remark_id_order",
        "review_results_excluded_from_remarks": True,
        "diagnostics_excluded_from_remarks": True,
    }
    return public


def prepare_job_result(result: dict[str, Any]) -> dict[str, Any]:
    """Prepare a completed check result for frontend tabs without losing status."""
    if not isinstance(result, dict):
        return result
    return prepare_public_report(result)
