"""Tracing/robustness wrapper for the Skill -> RAG -> decision audit chain.

The production checker remains page-based and Skill-driven. This wrapper makes
intermediate losses observable and prevents harmless evidence heuristics from
silently deleting a candidate before normative reasoning.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.reporting.report_contract import prepare_public_report


def run_traced_resilient_check(
    document_id: str,
    normative_number: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    skill_id: str = "vk_wastewater",
) -> dict[str, Any]:
    from app.checking import resilient as impl

    trace: dict[str, Any] = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "skill_id": skill_id,
        "pages": 0,
        "raw_visual_candidates": 0,
        "strict_candidates": 0,
        "skill_candidates": 0,
        "bbox_valid": 0,
        "bbox_rejected": 0,
        "rag_calls": 0,
        "rag_hits": 0,
        "requirements_seen": 0,
        "requirements_with_clause": 0,
        "decisions": 0,
        "violations": 0,
        "compliant": 0,
        "unchecked": 0,
        "drop_reasons": {},
        "checks": {},
    }

    def check_bucket(candidate: dict[str, Any]) -> dict[str, Any]:
        check_id = str(candidate.get("check_id") or "unknown")
        bucket = trace["checks"].setdefault(check_id, {
            "raw_visual_candidates": 0,
            "strict_candidates": 0,
            "skill_candidates": 0,
            "bbox_valid": 0,
            "bbox_rejected": 0,
            "rag_calls": 0,
            "rag_hits": 0,
            "requirements": 0,
            "requirements_with_clause": 0,
            "decisions": 0,
            "violations": 0,
            "compliant": 0,
            "unchecked": 0,
        })
        return bucket

    def drop(reason: str) -> None:
        trace["drop_reasons"][reason] = int(trace["drop_reasons"].get(reason, 0)) + 1

    original_strict = impl._strict_candidates
    original_filter = impl._filter_skill_candidates
    original_bbox = impl._bbox_has_real_evidence
    original_retrieve = impl.retrieve_audit_context
    original_multi = impl._multi_context
    original_decide = impl.decide_audit

    def traced_strict(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        trace["raw_visual_candidates"] += len(raw)
        accepted = []
        for item in raw:
            bucket = check_bucket(item)
            bucket["raw_visual_candidates"] += 1
        # The original 0.55 threshold was a hard, undocumented loss point.
        # Keep all structurally valid observations with a modest confidence floor;
        # the normative gate remains authoritative later in the chain.
        for item in raw:
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            evidence_text = str(item.get("evidence_text") or "").strip()
            bbox = item.get("bbox")
            try:
                confidence = float(item.get("confidence") or 0)
            except (TypeError, ValueError):
                confidence = 0.0
            if not evidence_text or not title or confidence < 0.35:
                drop("strict_candidate_validation")
                continue
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                drop("strict_candidate_bbox_missing")
                continue
            if not description or len(description) < 10:
                drop("strict_candidate_description")
                continue
            accepted.append({**item, "evidence_text": evidence_text})
            check_bucket(item)["strict_candidates"] += 1
        trace["strict_candidates"] += len(accepted)
        return accepted

    def traced_filter(candidates: list[dict[str, Any]], skill: dict[str, Any], page_number: int) -> list[dict[str, Any]]:
        accepted = original_filter(candidates, skill, page_number)
        trace["skill_candidates"] += len(accepted)
        for item in accepted:
            check_bucket(item)["skill_candidates"] += 1
        return accepted

    def traced_bbox(image_path: Path, bbox: list[float]) -> bool:
        # A pixel-density heuristic must not decide whether an explicitly supplied
        # VL bbox is evidence. It is especially unsafe for thin CAD lines and light
        # construction drawings. Valid geometry is sufficient for annotation.
        ok = bool(bbox and len(bbox) == 4 and bbox[2] > bbox[0] and bbox[3] > bbox[1])
        if ok:
            trace["bbox_valid"] += 1
        else:
            trace["bbox_rejected"] += 1
            drop("bbox_geometry")
        return ok

    def traced_retrieve(retrievers, candidate, top_k=6, skill_id="vk_wastewater"):
        trace["rag_calls"] += 1
        bucket = check_bucket(candidate)
        bucket["rag_calls"] += 1
        results = original_retrieve(retrievers, candidate, top_k=top_k, skill_id=skill_id)
        if results:
            trace["rag_hits"] += 1
            bucket["rag_hits"] += 1
        else:
            drop("rag_no_hits")
        return results

    def traced_multi(results: list[dict[str, Any]], candidate: dict[str, Any]):
        # Preserve the original ranking, but do not discard a candidate solely
        # because the parser/retriever failed to expose a clause field. Such a
        # candidate must reach decision as `unchecked`, where the missing clause
        # remains visible in diagnostics instead of becoming a silent zero-result.
        requirements = impl.select_normative_requirements(results, str(candidate.get("parameter") or ""), limit=4)
        requirements = [
            x for x in requirements
            if str(x.get("requirement") or "").strip() and str(x.get("norm") or "").strip()
        ]
        trace["requirements_seen"] += len(requirements)
        bucket = check_bucket(candidate)
        bucket["requirements"] += len(requirements)
        with_clause = sum(bool(str(x.get("clause") or "").strip()) for x in requirements)
        trace["requirements_with_clause"] += with_clause
        bucket["requirements_with_clause"] += with_clause
        if not requirements:
            drop("normative_requirement_missing")
        parts = []
        for item in requirements:
            clause = item.get("clause") or "—"
            meta = f"{item.get('norm')}, версия {item.get('version','—')}, стр. {item.get('page','—')}, п. {clause}"
            rule = f"оператор {item.get('operator') or '—'}, нормативное значение {item.get('normative_value') if item.get('normative_value') is not None else '—'} {item.get('normative_unit') or ''}".strip()
            parts.append(f"{meta}: {rule}\nТекст требования: {item['requirement']}")
        value = "\n\n".join(parts)
        return value[:12000] + ("\n[нормативный контекст сокращён]" if len(value) > 12000 else ""), requirements

    def traced_decide(*args, **kwargs):
        trace["decisions"] += 1
        decision = original_decide(*args, **kwargs)
        kind = str((decision or {}).get("type") or "unchecked")
        if kind == "violation":
            trace["violations"] += 1
        elif kind == "compliant":
            trace["compliant"] += 1
        else:
            trace["unchecked"] += 1
        candidate = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        bucket = check_bucket(candidate)
        bucket["decisions"] += 1
        bucket[kind if kind in {"violations", "compliant", "unchecked"} else "unchecked"] += 1
        return decision

    impl._strict_candidates = traced_strict
    impl._filter_skill_candidates = traced_filter
    impl._bbox_has_real_evidence = traced_bbox
    impl.retrieve_audit_context = traced_retrieve
    impl._multi_context = traced_multi
    impl.decide_audit = traced_decide
    try:
        report = impl.run_resilient_check(
            document_id,
            normative_number=normative_number,
            progress_callback=progress_callback,
            skill_id=skill_id,
        )
    finally:
        impl._strict_candidates = original_strict
        impl._filter_skill_candidates = original_filter
        impl._bbox_has_real_evidence = original_bbox
        impl.retrieve_audit_context = original_retrieve
        impl._multi_context = original_multi
        impl.decide_audit = original_decide

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    checkpoint_path = root / "checking" / "first_pass" / "checkpoint.json"
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            findings = checkpoint.get("findings") or []
            trace["saved_findings"] = len(findings)
            trace["saved_violations"] = sum(x.get("type") == "violation" for x in findings if isinstance(x, dict))
            trace["saved_compliant"] = sum(x.get("type") == "compliant" for x in findings if isinstance(x, dict))
            trace["saved_unchecked"] = sum(x.get("type") == "unchecked" for x in findings if isinstance(x, dict))
            trace["saved_findings_by_check"] = {}
            for item in findings:
                if isinstance(item, dict):
                    key = str(item.get("check_id") or "unknown")
                    trace["saved_findings_by_check"][key] = trace["saved_findings_by_check"].get(key, 0) + 1
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    trace["finished_at"] = datetime.now().isoformat(timespec="seconds")
    trace["pages"] = int((report.get("check_scope") or {}).get("pages_available") or (report.get("summary") or {}).get("pages") or 0)
    report["audit_trace"] = trace
    report = prepare_public_report(report)
    report["audit_trace"] = trace
    report_path = root / "checking" / "first_pass" / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
