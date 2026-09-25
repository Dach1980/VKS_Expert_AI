"""Audit the existing Skill/RAG candidate matrix against the current index.

This experiment does not call Qwen and does not change production behavior. It
reuses the saved first-pass report as the candidate source and runs every saved
candidate through the production routing, indexed-norm retrieval and normative
requirement extraction path. Checks with no saved candidate are reported as
NO_CANDIDATE rather than being treated as failures.

Required local state:
- saved report for document 53c22e43fcc843ef81f950516e81e68d;
- current KnowledgeStorage registry and indexed normative versions.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from app.checking.resilient import _indexed_norms
from app.knowledge.storage import KnowledgeStorage
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_router import filter_retrievers, route_candidate
from app.skills.registry import get_skill

DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
REPORT_PATH = (
    Path("knowledge")
    / "project_documents"
    / DOCUMENT_ID
    / "checking"
    / "first_pass"
    / "report.json"
)
OUTPUT_PATH = Path("data") / "skill_rag_matrix_20260925_result.json"
SKILL_ID = "vk_wastewater"


def _candidate_from_finding(finding: dict[str, object]) -> dict[str, object]:
    """Keep the production-relevant candidate fields from a saved finding."""
    return {
        "check_id": finding.get("check_id"),
        "title": finding.get("check_name") or finding.get("title") or "",
        "description": finding.get("description") or "",
        "parameter": finding.get("parameter") or "",
        "project_value": finding.get("project_value_raw") or finding.get("project_value") or "",
        "evidence_text": finding.get("evidence_text") or "",
        "source_context": finding.get("source_context") or "",
        "normative_route": finding.get("normative_route") or {},
    }


def main() -> None:
    if not REPORT_PATH.exists():
        raise SystemExit(f"Saved report not found: {REPORT_PATH}")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    skill = get_skill(SKILL_ID)
    findings = [x for x in report.get("results", []) if isinstance(x, dict)]
    storage = KnowledgeStorage()
    indexed_norms = _indexed_norms(storage)
    if not indexed_norms:
        raise SystemExit("No indexed normative documents are available")

    findings_by_check: dict[str, list[dict[str, object]]] = defaultdict(list)
    for finding in findings:
        findings_by_check[str(finding.get("check_id") or "")].append(finding)

    matrix = []
    for check in skill["checks"]:
        check_id = str(check["id"])
        candidates = findings_by_check.get(check_id, [])
        if not candidates:
            matrix.append({
                "check_id": check_id,
                "name": check["name"],
                "candidate_count": 0,
                "status": "NO_CANDIDATE",
                "routes": [],
                "retrieval_hits": 0,
                "requirements": 0,
            })
            continue

        candidate_results = []
        for finding in candidates:
            candidate = _candidate_from_finding(finding)
            route = route_candidate(candidate, SKILL_ID)
            scoped = filter_retrievers(indexed_norms, route)
            retrieved = retrieve_audit_context(
                indexed_norms,
                candidate,
                top_k=6,
                skill_id=SKILL_ID,
            )
            requirements = []
            # Keep requirement extraction on the same production selector used
            # by the final chain, without invoking the decision model.
            from app.rag.normative_requirement import select_normative_requirements

            requirements = select_normative_requirements(
                retrieved,
                str(candidate.get("parameter") or ""),
                limit=4,
            )
            valid_requirements = [
                item
                for item in requirements
                if item.get("clause") and item.get("requirement") and item.get("norm")
            ]
            candidate_results.append({
                "route": route,
                "scoped_retrievers": [
                    {"number": d.get("number"), "version": v.get("id")}
                    for d, v, _ in scoped
                ],
                "retrieved_count": len(retrieved),
                "requirement_count": len(valid_requirements),
                "requirements": [
                    {
                        "norm": item.get("norm"),
                        "version": item.get("version"),
                        "page": item.get("page"),
                        "clause": item.get("clause"),
                        "requirement": item.get("requirement"),
                    }
                    for item in valid_requirements
                ],
            })

        statuses = [
            "PASS"
            if item["route"].get("scope")
            and item["retrieved_count"] > 0
            and item["requirement_count"] > 0
            else "FAIL"
            for item in candidate_results
        ]
        matrix.append({
            "check_id": check_id,
            "name": check["name"],
            "candidate_count": len(candidates),
            "status": "PASS" if all(x == "PASS" for x in statuses) else "FAIL",
            "candidate_results": candidate_results,
        })

    counts = Counter(item["status"] for item in matrix)
    result = {
        "experiment": "skill_rag_matrix",
        "date": "2026-09-25",
        "document_id": DOCUMENT_ID,
        "skill_id": SKILL_ID,
        "indexed_norms": [
            {"number": d.get("number"), "version": v.get("id")}
            for d, v, _ in indexed_norms
        ],
        "checks_total": len(matrix),
        "status_counts": dict(counts),
        "matrix": matrix,
        "decision_stage": "not_run",
        "note": "This experiment validates Visual/Skill-saved candidates through routing, indexed RAG and requirement extraction only; it does not call Qwen or classify compliance.",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
