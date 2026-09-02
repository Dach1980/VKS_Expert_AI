"""Trace and recovery wrapper for the Skill -> RAG -> decision audit chain."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.reporting.report_contract import prepare_public_report

RECOVERY_PROMPT = """Выполни второй, короткий визуальный проход страницы проектной документации.
Профиль: Система водоотведения. Ищи только реально видимые инженерные факты: расходы, диаметры, уклоны, вентиляция канализации, выпуски, ревизии/прочистки, материалы канализационных труб, разделение систем, шумоизоляция стояков, поливочные устройства, приборы учёта, аварийные решения, координация с АР.
Не называй нарушение — только зафиксируй факт. Не используй номера листов, штампов и страниц.
Для каждого факта обязательно выбери один check_id: wastewater_flow, sewer_diameter, sewer_slope, sewer_ventilation, sewer_outlets, sewer_cleanouts, sewer_material, storm_separation, noise_insulation, irrigation, meters, emergency_outlets, ar_coordination.
Верни только JSON-массив максимум из 6 объектов:
[{"check_id":"...","title":"...","description":"...","parameter":"...","project_value":"...","unit":"...","source_row":"...","source_context":"...","evidence_text":"точный видимый фрагмент","bbox":[x1,y1,x2,y2],"confidence":0.0}]
Если инженерных фактов нет — []."""


def run_traced_resilient_check(document_id: str, normative_number: str, progress_callback: Callable[[dict[str, Any]], None] | None = None, skill_id: str = "vk_wastewater") -> dict[str, Any]:
    from app.checking import resilient as impl
    trace: dict[str, Any] = {"started_at": datetime.now().isoformat(timespec="seconds"), "skill_id": skill_id, "pages": 0, "raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements_seen": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0, "visual_recovery_pages": 0, "visual_recovery_candidates": 0, "raw_empty_pages": 0, "raw_samples": [], "drop_reasons": {}, "checks": {}}

    def bucket(candidate: dict[str, Any]) -> dict[str, Any]:
        key = str(candidate.get("check_id") or "unknown")
        return trace["checks"].setdefault(key, {"raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0})

    def drop(reason: str) -> None:
        trace["drop_reasons"][reason] = int(trace["drop_reasons"].get(reason, 0)) + 1

    original_strict = impl._strict_candidates
    original_filter = impl._filter_skill_candidates
    original_bbox = impl._bbox_has_real_evidence
    original_retrieve = impl.retrieve_audit_context
    original_decide = impl.decide_audit
    original_vision = impl._vision_request
    original_json_array = impl._json_array

    def traced_vision(client, prompt: str, image_path: Path, max_tokens: int = 1200) -> str:
        text = original_vision(client, prompt, image_path, max_tokens)
        parsed = original_json_array(text)
        if parsed:
            return text
        trace["raw_empty_pages"] += 1
        if len(trace["raw_samples"]) < 5:
            trace["raw_samples"].append({"kind": "empty_or_unparseable", "response_preview": str(text or "")[:1200]})
        recovery = original_vision(client, RECOVERY_PROMPT, image_path, max(2200, max_tokens))
        recovered = original_json_array(recovery)
        if recovered:
            trace["visual_recovery_pages"] += 1
            trace["visual_recovery_candidates"] += len(recovered)
        elif len(trace["raw_samples"]) < 5:
            trace["raw_samples"].append({"kind": "recovery_empty", "response_preview": str(recovery or "")[:1200]})
        return recovery

    def traced_strict(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        trace["raw_visual_candidates"] += len(raw)
        for item in raw:
            bucket(item)["raw_visual_candidates"] += 1
        accepted = []
        for item in raw:
            title = str(item.get("title") or "").strip(); description = str(item.get("description") or "").strip(); evidence_text = str(item.get("evidence_text") or "").strip(); bbox = item.get("bbox")
            try: confidence = float(item.get("confidence") or 0)
            except (TypeError, ValueError): confidence = 0.0
            if not evidence_text or not title or confidence < 0.35:
                drop("strict_candidate_validation"); continue
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                drop("strict_candidate_bbox_missing"); continue
            if not description or len(description) < 10:
                drop("strict_candidate_description"); continue
            accepted.append({**item, "evidence_text": evidence_text}); bucket(item)["strict_candidates"] += 1
        trace["strict_candidates"] += len(accepted)
        return accepted

    def traced_filter(candidates, skill, page_number):
        allowed = {str(x["id"]) for x in skill["checks"]}
        accepted = original_filter(candidates, skill, page_number)
        trace["skill_candidates"] += len(accepted)
        if candidates and not accepted: drop("skill_check_id_rejected")
        for item in candidates:
            if str(item.get("check_id") or "") not in allowed: drop("invalid_or_missing_check_id")
        for item in accepted: bucket(item)["skill_candidates"] += 1
        return accepted

    def traced_bbox(image_path: Path, bbox_value: list[float]) -> bool:
        ok = bool(bbox_value and len(bbox_value) == 4 and bbox_value[2] > bbox_value[0] and bbox_value[3] > bbox_value[1])
        if ok: trace["bbox_valid"] += 1
        else: trace["bbox_rejected"] += 1; drop("bbox_geometry")
        return ok

    def traced_retrieve(retrievers, candidate, top_k=6, skill_id="vk_wastewater"):
        trace["rag_calls"] += 1; b = bucket(candidate); b["rag_calls"] += 1
        results = original_retrieve(retrievers, candidate, top_k=top_k, skill_id=skill_id)
        if results: trace["rag_hits"] += 1; b["rag_hits"] += 1
        else: drop("rag_no_hits")
        return results

    def traced_multi(results, candidate):
        requirements = impl.select_normative_requirements(results, str(candidate.get("parameter") or ""), limit=4)
        requirements = [x for x in requirements if str(x.get("requirement") or "").strip() and str(x.get("norm") or "").strip()]
        trace["requirements_seen"] += len(requirements); b = bucket(candidate); b["requirements"] += len(requirements)
        with_clause = sum(bool(str(x.get("clause") or "").strip()) for x in requirements)
        trace["requirements_with_clause"] += with_clause; b["requirements_with_clause"] += with_clause
        if not requirements: drop("normative_requirement_missing")
        parts = []
        for item in requirements:
            clause = item.get("clause") or "—"; meta = f"{item.get('norm')}, версия {item.get('version','—')}, стр. {item.get('page','—')}, п. {clause}"; rule = f"оператор {item.get('operator') or '—'}, нормативное значение {item.get('normative_value') if item.get('normative_value') is not None else '—'} {item.get('normative_unit') or ''}".strip(); parts.append(f"{meta}: {rule}\nТекст требования: {item['requirement']}")
        value = "\n\n".join(parts)
        return value[:12000] + ("\n[нормативный контекст сокращён]" if len(value) > 12000 else ""), requirements

    def traced_decide(*args, **kwargs):
        trace["decisions"] += 1; decision = original_decide(*args, **kwargs); kind = str((decision or {}).get("type") or "unchecked")
        if kind == "violation": trace["violations"] += 1
        elif kind == "compliant": trace["compliant"] += 1
        else: trace["unchecked"] += 1
        candidate = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}; b = bucket(candidate); b["decisions"] += 1; b[kind if kind in {"violations", "compliant", "unchecked"} else "unchecked"] += 1
        return decision

    impl._strict_candidates = traced_strict; impl._filter_skill_candidates = traced_filter; impl._bbox_has_real_evidence = traced_bbox; impl.retrieve_audit_context = traced_retrieve; impl.decide_audit = traced_decide; impl._vision_request = traced_vision
    try:
        report = impl.run_resilient_check(document_id, normative_number=normative_number, progress_callback=progress_callback, skill_id=skill_id)
    finally:
        impl._strict_candidates = original_strict; impl._filter_skill_candidates = original_filter; impl._bbox_has_real_evidence = original_bbox; impl.retrieve_audit_context = original_retrieve; impl.decide_audit = original_decide; impl._vision_request = original_vision

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    checkpoint_path = root / "checking" / "first_pass" / "checkpoint.json"
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")); findings = checkpoint.get("findings") or []; trace["saved_findings"] = len(findings); trace["saved_violations"] = sum(x.get("type") == "violation" for x in findings if isinstance(x, dict)); trace["saved_compliant"] = sum(x.get("type") == "compliant" for x in findings if isinstance(x, dict)); trace["saved_unchecked"] = sum(x.get("type") == "unchecked" for x in findings if isinstance(x, dict))
        except (OSError, ValueError, json.JSONDecodeError): pass
    trace["finished_at"] = datetime.now().isoformat(timespec="seconds"); trace["pages"] = int((report.get("check_scope") or {}).get("pages_available") or (report.get("summary") or {}).get("pages") or 0)
    report["audit_trace"] = trace; report = prepare_public_report(report); report["audit_trace"] = trace
    (root / "checking" / "first_pass" / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
