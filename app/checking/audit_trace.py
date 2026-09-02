"""Trace and recovery wrapper for the Skill -> RAG -> decision audit chain."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from app.reporting.report_contract import prepare_public_report

RECOVERY_PROMPT = """Выполни короткий визуальный проход страницы проектной документации. Профиль: Система водоотведения. Ищи только реально видимые инженерные факты: расходы, диаметры, уклоны, вентиляция канализации, выпуски, ревизии/прочистки, материалы канализационных труб, разделение систем, шумоизоляция стояков, поливочные устройства, приборы учёта, аварийные решения, координация с АР. Не называй нарушение — только зафиксируй факт. Не используй номера листов, штампов и страниц. Для каждого факта выбери один check_id: wastewater_flow, sewer_diameter, sewer_slope, sewer_ventilation, sewer_outlets, sewer_cleanouts, sewer_material, storm_separation, noise_insulation, irrigation, meters, emergency_outlets, ar_coordination. Верни только JSON-массив максимум из 6 объектов с полями check_id,title,description,parameter,project_value,unit,source_row,source_context,evidence_text,bbox,confidence. Если фактов нет — []."""


def run_traced_resilient_check(document_id: str, normative_number: str, progress_callback: Callable[[dict[str, Any]], None] | None = None, skill_id: str = "vk_wastewater") -> dict[str, Any]:
    from app.checking import resilient as impl
    from app.skills.registry import get_skill
    allowed_ids = {str(x["id"]) for x in get_skill(skill_id)["checks"]}
    trace = {"started_at": datetime.now().isoformat(timespec="seconds"), "skill_id": skill_id, "pages": 0, "raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements_seen": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0, "visual_recovery_pages": 0, "visual_recovery_candidates": 0, "raw_empty_pages": 0, "raw_invalid_skill_pages": 0, "raw_samples": [], "drop_reasons": {}, "checks": {}}

    def bucket(c):
        k = str(c.get("check_id") or "unknown")
        return trace["checks"].setdefault(k, {"raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0})
    def drop(r): trace["drop_reasons"][r] = int(trace["drop_reasons"].get(r, 0)) + 1

    os_ = {n: getattr(impl, n) for n in ["_strict_candidates", "_filter_skill_candidates", "_bbox_has_real_evidence", "retrieve_audit_context", "_multi_context", "decide_audit", "_vision_request", "_json_array"]}

    def vision(client, prompt, image_path, max_tokens=1200):
        text = os_["_vision_request"](client, prompt, image_path, max_tokens); parsed = os_["_json_array"](text)
        valid = [x for x in parsed if str(x.get("check_id") or "") in allowed_ids and str(x.get("title") or "").strip() and str(x.get("description") or "").strip() and str(x.get("evidence_text") or "").strip() and isinstance(x.get("bbox"), (list, tuple)) and len(x.get("bbox")) == 4]
        if valid: return text
        trace["raw_empty_pages"] += int(not parsed); trace["raw_invalid_skill_pages"] += int(bool(parsed))
        if len(trace["raw_samples"]) < 5: trace["raw_samples"].append({"kind": "empty_or_invalid_skill", "response_preview": str(text or "")[:1200]})
        recovery = os_["_vision_request"](client, RECOVERY_PROMPT, image_path, max(2200, max_tokens)); recovered = os_["_json_array"](recovery)
        if recovered: trace["visual_recovery_pages"] += 1; trace["visual_recovery_candidates"] += len(recovered)
        elif len(trace["raw_samples"]) < 5: trace["raw_samples"].append({"kind": "recovery_empty", "response_preview": str(recovery or "")[:1200]})
        return recovery

    def strict(raw):
        trace["raw_visual_candidates"] += len(raw)
        for x in raw: bucket(x)["raw_visual_candidates"] += 1
        out = []
        for x in raw:
            title = str(x.get("title") or "").strip(); desc = str(x.get("description") or "").strip(); ev = str(x.get("evidence_text") or "").strip(); bbox = x.get("bbox")
            try: conf = float(x.get("confidence") or 0)
            except (TypeError, ValueError): conf = 0.0
            if not ev or not title or conf < 0.35: drop("strict_candidate_validation"); continue
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4: drop("strict_candidate_bbox_missing"); continue
            if len(desc) < 10: drop("strict_candidate_description"); continue
            out.append({**x, "evidence_text": ev}); bucket(x)["strict_candidates"] += 1
        trace["strict_candidates"] += len(out); return out

    def filt(candidates, skill, page_number):
        out = os_["_filter_skill_candidates"](candidates, skill, page_number); trace["skill_candidates"] += len(out)
        if candidates and not out: drop("skill_check_id_rejected")
        for x in candidates:
            if str(x.get("check_id") or "") not in {str(i["id"]) for i in skill["checks"]}: drop("invalid_or_missing_check_id")
        for x in out: bucket(x)["skill_candidates"] += 1
        return out

    def bbox(image, b):
        ok = bool(b and len(b) == 4 and b[2] > b[0] and b[3] > b[1]); trace["bbox_valid" if ok else "bbox_rejected"] += 1
        if not ok: drop("bbox_geometry")
        return ok

    def retrieve(retrievers, candidate, top_k=6, skill_id="vk_wastewater"):
        trace["rag_calls"] += 1; bucket(candidate)["rag_calls"] += 1; result = os_["retrieve_audit_context"](retrievers, candidate, top_k=top_k, skill_id=skill_id)
        if result: trace["rag_hits"] += 1; bucket(candidate)["rag_hits"] += 1
        else: drop("rag_no_hits")
        return result

    def multi(results, candidate):
        req = impl.select_normative_requirements(results, str(candidate.get("parameter") or ""), limit=4)
        req = [x for x in req if str(x.get("requirement") or "").strip() and str(x.get("norm") or "").strip()]
        # A missing parser clause is not permission to erase the visual fact. Let
        # it reach decision as unchecked; confirmed violation/compliance still
        # requires a concrete clause in resilient._finalise_decision().
        trace["requirements_seen"] += len(req); bucket(candidate)["requirements"] += len(req); with_clause = sum(bool(str(x.get("clause") or "").strip()) for x in req); trace["requirements_with_clause"] += with_clause; bucket(candidate)["requirements_with_clause"] += with_clause
        if not req: drop("normative_requirement_missing")
        parts = []
        for x in req:
            parts.append(f"{x.get('norm')}, версия {x.get('version','—')}, стр. {x.get('page','—')}, п. {x.get('clause') or '—'}: оператор {x.get('operator') or '—'}, нормативное значение {x.get('normative_value') if x.get('normative_value') is not None else '—'} {x.get('normative_unit') or ''}\nТекст требования: {x.get('requirement')}")
        text = "\n\n".join(parts); return text[:12000] + ("\n[нормативный контекст сокращён]" if len(text) > 12000 else ""), req

    def decide(*args, **kwargs):
        trace["decisions"] += 1; d = os_["decide_audit"](*args, **kwargs); k = str((d or {}).get("type") or "unchecked"); trace[k if k in {"violations", "compliant", "unchecked"} else "unchecked"] += 1; c = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}; bucket(c)["decisions"] += 1; bucket(c)[k if k in {"violations", "compliant", "unchecked"} else "unchecked"] += 1; return d

    impl._strict_candidates = strict; impl._filter_skill_candidates = filt; impl._bbox_has_real_evidence = bbox; impl.retrieve_audit_context = retrieve; impl._multi_context = multi; impl.decide_audit = decide; impl._vision_request = vision
    try:
        report = impl.run_resilient_check(document_id, normative_number=normative_number, progress_callback=progress_callback, skill_id=skill_id)
    finally:
        impl._strict_candidates = os_["_strict_candidates"]; impl._filter_skill_candidates = os_["_filter_skill_candidates"]; impl._bbox_has_real_evidence = os_["_bbox_has_real_evidence"]; impl.retrieve_audit_context = os_["retrieve_audit_context"]; impl._multi_context = os_["_multi_context"]; impl.decide_audit = os_["decide_audit"]; impl._vision_request = os_["_vision_request"]

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id; cp = root / "checking" / "first_pass" / "checkpoint.json"
    if cp.exists():
        try:
            findings = json.loads(cp.read_text(encoding="utf-8")).get("findings") or []; trace["saved_findings"] = len(findings); trace["saved_violations"] = sum(x.get("type") == "violation" for x in findings if isinstance(x, dict)); trace["saved_compliant"] = sum(x.get("type") == "compliant" for x in findings if isinstance(x, dict)); trace["saved_unchecked"] = sum(x.get("type") == "unchecked" for x in findings if isinstance(x, dict))
        except (OSError, ValueError, json.JSONDecodeError): pass
    trace["finished_at"] = datetime.now().isoformat(timespec="seconds"); trace["pages"] = int((report.get("check_scope") or {}).get("pages_available") or (report.get("summary") or {}).get("pages") or 0); report["audit_trace"] = trace; report = prepare_public_report(report); report["audit_trace"] = trace; (root / "checking" / "first_pass" / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"); return report
