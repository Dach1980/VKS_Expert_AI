"""Trace and recovery wrapper for the Skill -> RAG -> decision audit chain."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.reporting.report_contract import prepare_public_report

LOGGER = logging.getLogger("project_expert_ai.checking")

RECOVERY_PROMPT = """Выполни короткий визуальный проход страницы проектной документации. Профиль: Система водоотведения. Ищи только реально видимые инженерные факты: расходы, диаметры, уклоны, вентиляция канализации, выпуски, ревизии/прочистки, материалы канализационных труб, разделение систем, шумоизоляция стояков, поливочные устройства, приборы учёта, аварийные решения, координация с АР. Не называй нарушение — только зафиксируй факт. Не используй номера листов, штампов и страниц. Для каждого факта выбери один check_id: wastewater_flow, sewer_diameter, sewer_slope, sewer_ventilation, sewer_outlets, sewer_cleanouts, sewer_material, storm_separation, noise_insulation, irrigation, meters, emergency_outlets, ar_coordination. Верни только JSON-массив максимум из 6 объектов с полями check_id,title,description,parameter,project_value,unit,source_row,source_context,evidence_text,bbox,confidence. Если фактов нет — []."""


def _log(message: str, *args: Any) -> None:
    rendered = message % args if args else message
    line = "[NORMCONTROL] " + rendered
    try:
        print(line, file=sys.stdout, flush=True)
    except Exception:
        pass
    try:
        LOGGER.info(line)
    except Exception:
        pass


def run_traced_resilient_check(document_id: str, normative_number: str, progress_callback: Callable[[dict[str, Any]], None] | None = None, skill_id: str = "vk_wastewater") -> dict[str, Any]:
    from app.checking import resilient as impl
    from app.checking import first_pass as vision_impl
    from app.skills.registry import get_skill

    skill = get_skill(skill_id)
    allowed_ids = {str(x["id"]) for x in skill["checks"]}
    trace = {"started_at": datetime.now().isoformat(timespec="seconds"), "skill_id": skill_id, "pages": 0, "raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements_seen": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0, "visual_recovery_pages": 0, "visual_recovery_candidates": 0, "raw_empty_pages": 0, "raw_invalid_skill_pages": 0, "raw_samples": [], "drop_reasons": {}, "checks": {}, "diagnostics_log": []}

    def trace_log(kind: str, message: str, **data: Any) -> None:
        """Persist diagnostic events in report.json using real UTF-8 text."""
        event: dict[str, Any] = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "kind": kind,
            "message": message,
        }
        event.update(data)
        trace["diagnostics_log"].append(event)
        if len(trace["diagnostics_log"]) > 500:
            del trace["diagnostics_log"][:-500]

    _log("START document=%s skill=%s checks=%d", document_id, skill_id, len(skill["checks"]))
    trace_log("start", "Начало проверки", document_id=document_id, skill_id=skill_id, checks=len(skill["checks"]))

    def bucket(c):
        k = str(c.get("check_id") or "unknown")
        return trace["checks"].setdefault(k, {"raw_visual_candidates": 0, "strict_candidates": 0, "skill_candidates": 0, "bbox_valid": 0, "bbox_rejected": 0, "rag_calls": 0, "rag_hits": 0, "requirements": 0, "requirements_with_clause": 0, "decisions": 0, "violations": 0, "compliant": 0, "unchecked": 0})

    def drop(r):
        trace["drop_reasons"][r] = int(trace["drop_reasons"].get(r, 0)) + 1
        trace_log("drop", f"Отброшено: {r}", reason=r)

    os_ = {n: getattr(impl, n) for n in ["_strict_candidates", "_filter_skill_candidates", "_bbox_has_real_evidence", "retrieve_audit_context", "_multi_context", "decide_audit", "_vision_request", "_json_array"]}

    def vision(client, prompt, image_path, max_tokens=1200):
        original_post = vision_impl.requests.post
        captured: dict[str, Any] = {}

        def capture_post(*args, **kwargs):
            response = original_post(*args, **kwargs)
            captured["http_status"] = getattr(response, "status_code", None)
            captured["content_type"] = str(getattr(response, "headers", {}).get("Content-Type", ""))
            raw_bytes = bytes(getattr(response, "content", b"") or b"")
            captured["raw_response_bytes_length"] = len(raw_bytes)
            try:
                decoded = raw_bytes.decode("utf-8")
                captured["utf8_decode_ok"] = True
                captured["utf8_decoded_length"] = len(decoded)
                captured["utf8_decoded_preview"] = decoded[:1000]
                captured["utf8_decoded_repr"] = repr(decoded[:1000])
                captured["utf8_decoded_has_replacement_char"] = "\ufffd" in decoded
                captured["utf8_decoded_has_question_mark"] = "?" in decoded
                try:
                    payload = json.loads(decoded)
                    message_content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) if isinstance(payload, dict) else None
                    if message_content is not None:
                        message_content = str(message_content)
                        captured["message_content_length_from_raw"] = len(message_content)
                        captured["message_content_preview_from_raw"] = message_content[:1000]
                        captured["message_content_repr_from_raw"] = repr(message_content[:1000])
                        captured["message_content_has_replacement_char"] = "\ufffd" in message_content
                        captured["message_content_has_question_mark"] = "?" in message_content
                except (TypeError, ValueError, json.JSONDecodeError):
                    captured["raw_json_parse_error"] = True
            except UnicodeDecodeError as exc:
                captured["utf8_decode_ok"] = False
                captured["utf8_decode_error"] = str(exc)
                decoded = raw_bytes.decode("utf-8", errors="replace")
                captured["utf8_decoded_length"] = len(decoded)
                captured["utf8_decoded_preview"] = decoded[:1000]
                captured["utf8_decoded_repr"] = repr(decoded[:1000])
                captured["utf8_decoded_has_replacement_char"] = "\ufffd" in decoded
                captured["utf8_decoded_has_question_mark"] = "?" in decoded
            return response

        vision_impl.requests.post = capture_post
        try:
            text = os_["_vision_request"](client, prompt, image_path, max_tokens)
        except Exception as exc:
            event = dict(captured)
            event.update({
                "page_image": str(image_path),
                "response_length": len(str(locals().get("text") or "")),
                "response_preview": str(locals().get("text") or "")[:1000],
                "response_repr": repr(str(locals().get("text") or "")[:1000]),
                "response_has_replacement_char": "\ufffd" in str(locals().get("text") or ""),
                "response_has_question_mark": "?" in str(locals().get("text") or ""),
            })
            trace_log("vision_transport", "Диагностика транспорта Vision при ошибке", **event)
            trace_log("vision_error", "Ошибка Vision-запроса", error_type=type(exc).__name__, error=str(exc), page_image=str(image_path))
            raise
        finally:
            vision_impl.requests.post = original_post

        response_text = str(text or "")
        event = dict(captured)
        event.update({
            "page_image": str(image_path),
            "response_length": len(response_text),
            "response_preview": response_text[:1000],
            "response_repr": repr(response_text[:1000]),
            "response_has_replacement_char": "\ufffd" in response_text,
            "response_has_question_mark": "?" in response_text,
        })
        trace_log("vision_transport", "Диагностика сырого HTTP-ответа и message.content", **event)
        trace_log("vision_response", "Получен ответ Vision", page_image=str(image_path), response_length=len(response_text), response=response_text[:12000])
        parsed = os_["_json_array"](text)
        trace_log("vision_parsed", "Результат разбора Vision-ответа", parsed_count=len(parsed))
        valid = [x for x in parsed if str(x.get("check_id") or "") in allowed_ids and str(x.get("title") or "").strip() and str(x.get("description") or "").strip() and str(x.get("evidence_text") or "").strip() and isinstance(x.get("bbox"), (list, tuple)) and len(x.get("bbox")) == 4]
        if valid:
            return text
        trace["raw_empty_pages"] += int(not parsed)
        trace["raw_invalid_skill_pages"] += int(bool(parsed))
        if len(trace["raw_samples"]) < 5:
            trace["raw_samples"].append({"kind": "empty_or_invalid_skill", "response_preview": response_text[:1200]})
        trace_log("vision_recovery", "Основной Vision-ответ не дал валидных Skill-кандидатов; запускается recovery", parsed_count=len(parsed), valid_count=len(valid))
        recovery = os_["_vision_request"](client, RECOVERY_PROMPT, image_path, max(2200, max_tokens))
        trace_log("vision_recovery_response", "Получен ответ Vision recovery", page_image=str(image_path), response_length=len(str(recovery or "")), response=str(recovery or "")[:12000])
        recovered = os_["_json_array"](recovery)
        trace_log("vision_recovery_parsed", "Результат разбора recovery-ответа", parsed_count=len(recovered))
        if recovered:
            trace["visual_recovery_pages"] += 1
            trace["visual_recovery_candidates"] += len(recovered)
        elif len(trace["raw_samples"]) < 5:
            trace["raw_samples"].append({"kind": "recovery_empty", "response_preview": str(recovery or "")[:1200]})
        return recovery

    def strict(raw):
        trace["raw_visual_candidates"] += len(raw)
        for x in raw:
            bucket(x)["raw_visual_candidates"] += 1
        out = []
        for x in raw:
            title = str(x.get("title") or "").strip()
            desc = str(x.get("description") or "").strip()
            ev = str(x.get("evidence_text") or "").strip()
            bbox = x.get("bbox")
            try:
                conf = float(x.get("confidence") or 0)
            except (TypeError, ValueError):
                conf = 0.0
            if not ev or not title or conf < 0.35:
                drop("strict_candidate_validation")
                continue
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                drop("strict_candidate_bbox_missing")
                continue
            if len(desc) < 10:
                drop("strict_candidate_description")
                continue
            out.append({**x, "evidence_text": ev})
            bucket(x)["strict_candidates"] += 1
        trace["strict_candidates"] += len(out)
        return out

    def filt(candidates, skill_arg, page_number):
        out = os_["_filter_skill_candidates"](candidates, skill_arg, page_number)
        trace["skill_candidates"] += len(out)
        if candidates and not out:
            drop("skill_check_id_rejected")
        for x in candidates:
            if str(x.get("check_id") or "") not in {str(i["id"]) for i in skill_arg["checks"]}:
                drop("invalid_or_missing_check_id")
        for x in out:
            bucket(x)["skill_candidates"] += 1
        return out

    def bbox(image, b):
        ok = bool(b and len(b) == 4 and b[2] > b[0] and b[3] > b[1])
        trace["bbox_valid" if ok else "bbox_rejected"] += 1
        if not ok:
            drop("bbox_geometry")
        return ok

    def retrieve(retrievers, candidate, top_k=6, skill_id="vk_wastewater"):
        trace["rag_calls"] += 1
        bucket(candidate)["rag_calls"] += 1
        result = os_["retrieve_audit_context"](retrievers, candidate, top_k=top_k, skill_id=skill_id)
        if result:
            trace["rag_hits"] += 1
            bucket(candidate)["rag_hits"] += 1
        else:
            drop("rag_no_hits")
        return result

    def multi(results, candidate):
        req = impl.select_normative_requirements(results, str(candidate.get("parameter") or ""), limit=4)
        req = [x for x in req if str(x.get("requirement") or "").strip() and str(x.get("norm") or "").strip()]
        trace["requirements_seen"] += len(req)
        bucket(candidate)["requirements"] += len(req)
        with_clause = sum(bool(str(x.get("clause") or "").strip()) for x in req)
        trace["requirements_with_clause"] += with_clause
        bucket(candidate)["requirements_with_clause"] += with_clause
        if not req:
            drop("normative_requirement_missing")
        parts = []
        for x in req:
            parts.append(f"{x.get('norm')}, версия {x.get('version','—')}, стр. {x.get('page','—')}, п. {x.get('clause') or '—'}: оператор {x.get('operator') or '—'}, нормативное значение {x.get('normative_value') if x.get('normative_value') is not None else '—'} {x.get('normative_unit') or ''}\nТекст требования: {x.get('requirement')}")
        text = "\n\n".join(parts)
        return text[:12000] + ("\n[нормативный контекст сокращён]" if len(text) > 12000 else ""), req

    def decide(*args, **kwargs):
        trace["decisions"] += 1
        d = os_["decide_audit"](*args, **kwargs)
        k = str((d or {}).get("type") or "unchecked")
        if k in {"violation", "compliant", "unchecked"}:
            trace["violations" if k == "violation" else k] += 1
        c = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        bucket(c)["decisions"] += 1
        bucket(c)["violations" if k == "violation" else k if k in {"compliant", "unchecked"} else "unchecked"] += 1
        return d

    impl._strict_candidates = strict
    impl._filter_skill_candidates = filt
    impl._bbox_has_real_evidence = bbox
    impl.retrieve_audit_context = retrieve
    impl._multi_context = multi
    impl.decide_audit = decide
    impl._vision_request = vision
    try:
        report = impl.run_resilient_check(document_id, normative_number=normative_number, progress_callback=progress_callback, skill_id=skill_id)
    finally:
        impl._strict_candidates = os_["_strict_candidates"]
        impl._filter_skill_candidates = os_["_filter_skill_candidates"]
        impl._bbox_has_real_evidence = os_["_bbox_has_real_evidence"]
        impl.retrieve_audit_context = os_["retrieve_audit_context"]
        impl._multi_context = os_["_multi_context"]
        impl.decide_audit = os_["decide_audit"]
        impl._vision_request = os_["_vision_request"]

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    cp = root / "checking" / "first_pass" / "checkpoint.json"
    if cp.exists():
        try:
            saved = json.loads(cp.read_text(encoding="utf-8")).get("findings") or []
            trace["saved_findings"] = len(saved)
            trace["saved_violations"] = sum(x.get("type") == "violation" for x in saved if isinstance(x, dict))
            trace["saved_compliant"] = sum(x.get("type") == "compliant" for x in saved if isinstance(x, dict))
            trace["saved_unchecked"] = sum(x.get("type") == "unchecked" for x in saved if isinstance(x, dict))
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    trace["finished_at"] = datetime.now().isoformat(timespec="seconds")
    trace["pages"] = int((report.get("check_scope") or {}).get("pages_available") or (report.get("summary") or {}).get("pages") or 0)
    report["audit_trace"] = trace
    report = prepare_public_report(report)
    report["audit_trace"] = trace
    report_path = root / "checking" / "first_pass" / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _log("END pages=%d raw=%d strict=%d skill=%d bbox_ok=%d bbox_rejected=%d rag=%d/%d requirements=%d clauses=%d decisions=%d violations=%d compliant=%d unchecked=%d", trace["pages"], trace["raw_visual_candidates"], trace["strict_candidates"], trace["skill_candidates"], trace["bbox_valid"], trace["bbox_rejected"], trace["rag_hits"], trace["rag_calls"], trace["requirements_seen"], trace["requirements_with_clause"], trace["decisions"], trace["violations"], trace["compliant"], trace["unchecked"])
    _log("DROP_REASONS %s", json.dumps(trace["drop_reasons"], ensure_ascii=False, sort_keys=True))
    if trace["raw_samples"]:
        _log("RAW_SAMPLES %s", json.dumps(trace["raw_samples"], ensure_ascii=False)[:4000])
    for check_id, stats in trace["checks"].items():
        if any(int(stats.get(k, 0) or 0) for k in ("raw_visual_candidates", "strict_candidates", "skill_candidates", "rag_calls", "decisions")):
            _log("CHECK %s raw=%d strict=%d skill=%d rag=%d/%d req=%d clause=%d decisions=%d violations=%d compliant=%d unchecked=%d", check_id, stats["raw_visual_candidates"], stats["strict_candidates"], stats["skill_candidates"], stats["rag_hits"], stats["rag_calls"], stats["requirements"], stats["requirements_with_clause"], stats["decisions"], stats["violations"], stats["compliant"], stats["unchecked"])
    return report
