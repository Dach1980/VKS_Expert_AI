"""Single public report contract shared by the UI and IOS 3.1 exporters.

The checker may persist every machine result for traceability, but the user-facing
report must contain only confirmed remarks. Unchecked and compliant observations
remain separate datasets and are never promoted to remarks.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

REPORT_SCHEMA_VERSION = "1.0"


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


def prepare_public_report(report: dict[str, Any]) -> dict[str, Any]:
    """Convert internal checker output into the canonical user-facing report."""
    public = deepcopy(report)
    raw = report.get("results") or report.get("checks") or []
    findings = [_normalise_finding(x) for x in raw if isinstance(x, dict)]

    remarks = [x for x in findings if x.get("type") == "violation"]
    compliant = [x for x in findings if x.get("type") == "compliant"]
    review = [x for x in findings if x.get("type") == "unchecked"]

    # `results` is deliberately the remarks register. This is the contract used
    # by the Remarks tab, web report and PDF/Word exporters.
    public["schema_version"] = REPORT_SCHEMA_VERSION
    public["results"] = remarks
    public["remarks"] = remarks
    public["compliant_results"] = compliant
    public["review_results"] = review

    source_summary = report.get("summary") or {}
    public["summary"] = {
        "pages": source_summary.get("pages", 0),
        "total": len(remarks),
        "violations": len(remarks),
        "critical": sum(x.get("severity") == "critical" for x in remarks),
        "major": sum(x.get("severity") == "major" for x in remarks),
        "minor": sum(x.get("severity") == "minor" for x in remarks),
        "compliant": len(compliant),
        "unchecked": len(review),
    }
    public["report_definition"] = {
        "remark_status": "violation",
        "remark_fields": [
            "id", "page", "sheet", "parameter", "project_value_raw",
            "normative_requirement", "norm", "clause", "type",
            "severity", "recommendation", "evidence_image", "image",
        ],
        "evidence_numbering": "remark_id_order",
        "review_results_excluded_from_remarks": True,
    }
    return public


def prepare_job_result(result: dict[str, Any]) -> dict[str, Any]:
    """Prepare a completed check result for frontend tabs without losing status."""
    if not isinstance(result, dict):
        return result
    return prepare_public_report(result)
