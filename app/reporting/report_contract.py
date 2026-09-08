"""Single public report contract shared by the UI and IOS 3.1 exporters."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from app.reporting.result_store import build_question_mark_trace

REPORT_SCHEMA_VERSION = "1.2"


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


def _pipeline_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all decision findings without depending on public results semantics."""
    stored = report.get("_pipeline_findings")
    if isinstance(stored, list):
        return [_normalise_finding(x) for x in stored if isinstance(x, dict)]

    combined: list[dict[str, Any]] = []
    for key in ("results", "compliant_results", "review_results"):
        value = report.get(key)
        if isinstance(value, list):
            combined.extend(x for x in value if isinstance(x, dict))
    if combined:
        return [_normalise_finding(x) for x in combined]

    value = report.get("results") or report.get("checks") or []
    return [_normalise_finding(x) for x in value if isinstance(x, dict)]


def _build_diagnostics(report: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Build diagnostics from the executed pipeline trace, not from public remarks."""
    trace = report.get("audit_trace") or {}
    traced_checks = trace.get("checks") if isinstance(trace, dict) else None
    matrix = []

    if isinstance(traced_checks, dict) and traced_checks:
        check_names = {
            str(item.get("id")): str(item.get("name") or "")
            for item in (report.get("check_matrix") or [])
            if isinstance(item, dict)
        }
        for check_id, stats in traced_checks.items():
            if not isinstance(stats, dict):
                continue
            decisions = {
                "violation": int(stats.get("violations", 0) or 0),
                "compliant": int(stats.get("compliant", 0) or 0),
                "unchecked": int(stats.get("unchecked", 0) or 0),
            }
            visual_candidates = int(stats.get("skill_candidates", 0) or 0)
            rag_hits = int(stats.get("rag_hits", 0) or 0)
            requirements = int(stats.get("requirements", 0) or 0)
            matrix.append({
                "id": str(check_id),
                "name": check_names.get(str(check_id), str(check_id)),
                "visual_candidates": visual_candidates,
                "rag_candidates": rag_hits,
                "normative_requirements": requirements,
                "decisions": decisions,
                "remarks": decisions["violation"],
                "status": "evidence_found" if visual_candidates else "no_evidence_candidate",
            })
    else:
        # Backward-compatible fallback for reports produced without audit_trace.
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
        "source": "audit_trace.checks" if isinstance(traced_checks, dict) and traced_checks else "findings_fallback",
        "note": "Диагностика не является частью замечаний. Отсутствие кандидата или нормативного требования означает необходимость проверки цепочки, а не нарушение проекта.",
    }


def prepare_public_report(report: dict[str, Any]) -> dict[str, Any]:
    """Convert checker output into the canonical user-facing report without losing pipeline data."""
    public = deepcopy(report)
    findings = _pipeline_findings(report)

    remarks = [x for x in findings if x.get("type") == "violation"]
    compliant = [x for x in findings if x.get("type") == "compliant"]
    review = [x for x in findings if x.get("type") == "unchecked"]

    public["schema_version"] = REPORT_SCHEMA_VERSION
    public["results"] = remarks
    public["remarks"] = remarks
    public["compliant_results"] = compliant
    public["review_results"] = review

    # Keep the complete internal decision set available to a second preparation
    # pass. It is not a user-facing report section and is removed before save.
    public["_pipeline_findings"] = findings

    scope = report.get("check_scope") or {}
    source_summary = report.get("summary") or {}
    trace = report.get("audit_trace") or {}
    try:
        pages = int((trace.get("pages_processed") if isinstance(trace, dict) else 0) or 0)
    except (TypeError, ValueError):
        pages = 0
    if pages <= 0:
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

    if isinstance(trace, dict) and trace:
        violations_count = int(trace.get("violations", len(remarks)) or 0)
        compliant_count = int(trace.get("compliant", len(compliant)) or 0)
        unchecked_count = int(trace.get("unchecked", len(review)) or 0)
    else:
        violations_count = len(remarks)
        compliant_count = len(compliant)
        unchecked_count = len(review)

    public["summary"] = {
        "pages": pages,
        "pages_available": pages_available,
        "total": violations_count + compliant_count + unchecked_count,
        "violations": violations_count,
        "critical": sum(x.get("severity") == "critical" for x in remarks),
        "major": sum(x.get("severity") == "major" for x in remarks),
        "minor": sum(x.get("severity") == "minor" for x in remarks),
        "compliant": compliant_count,
        "unchecked": unchecked_count,
    }
    public["diagnostics"] = _build_diagnostics(report, findings)

    document_id = str(public.get("document_id") or "").strip()
    if document_id:
        root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
        try:
            public["question_mark_trace"] = build_question_mark_trace(root, public)
        except Exception as error:
            public["question_mark_trace"] = {"error": str(error), "first_detected_stage": None}

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
        "question_mark_trace_excluded_from_remarks": True,
    }
    return public


def prepare_job_result(result: dict[str, Any]) -> dict[str, Any]:
    """Prepare a completed check result for frontend tabs without losing status."""
    if not isinstance(result, dict):
        return result
    return prepare_public_report(result)
