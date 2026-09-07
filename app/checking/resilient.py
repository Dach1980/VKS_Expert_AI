"""Resilient document checking driven by explicit expert Skill checks."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from app.checking.first_pass import CHECK_DPI, DEFAULT_NORM_NUMBER, MAX_NORM_RESULTS, REPORT_API_BASE, _json_array, _strict_candidates, _vision_request
from app.checking.audit_decision import decide_audit
from app.checking.scope import CheckCancelled
from app.checking.table_check import build_table_check_row, deterministic_numeric_comparison
from app.checking.page_pipeline import annotate_evidence, normalize_bbox, render_pdf_pages
from app.knowledge.storage import KnowledgeStorage
from app.llm.lmstudio_client import LMStudioClient
from app.rag.retriever import Retriever
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_requirement import select_normative_requirements
from app.reporting.report_contract import prepare_public_report
from app.skills.registry import get_skill

ProgressCallback = Callable[[dict[str, Any]], None]
MAX_PAGE_RETRIES = 3
RETRY_DELAY_SECONDS = 3.0
MAX_PAGE_CANDIDATES = 12
MAX_CANDIDATES_PER_CHECK_PER_PAGE = 2


def _checkpoint_path(directory: Path) -> Path:
    return directory / "checkpoint.json"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_checkpoint(path: Path, document_id: str, pdf_name: str, skill_id: str, model: str, selected_pages: list[int]) -> dict[str, Any]:
    empty = {"status": "running", "document_id": document_id, "document_name": pdf_name, "skill_id": skill_id, "model": model, "selected_pages": selected_pages, "pages_completed": 0, "completed_pages": [], "findings": [], "last_error": None}
    if not path.exists():
        return empty
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("document_id") != document_id or value.get("skill_id", skill_id) != skill_id:
            return empty
        if str(value.get("model") or model) != model or list(value.get("selected_pages") or selected_pages) != selected_pages:
            return empty
        if value.get("status") == "completed":
            return empty
        value.setdefault("completed_pages", [])
        value.setdefault("findings", [])
        value.setdefault("pages_completed", len(value["completed_pages"]))
        value["skill_id"] = skill_id
        value["model"] = model
        value["selected_pages"] = selected_pages
        return value
    except (OSError, ValueError, json.JSONDecodeError):
        return empty


def _indexed_norms(storage: KnowledgeStorage) -> list[tuple[dict[str, Any], dict[str, Any], Retriever]]:
    result = []
    for document in storage.registry.get_all_documents():
        try:
            version = storage.get_current_version(document["id"])
            paths = storage.paths(document["id"], version["id"])
            if (paths.embeddings / "index.faiss").exists() and (paths.embeddings / "metadata.json").exists():
                result.append((document, version, Retriever(document["id"], version["id"], storage)))
        except Exception:
            continue
    return result


def _multi_context(results: list[dict[str, Any]], candidate: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    requirements = select_normative_requirements(results, str(candidate.get("parameter") or ""), limit=4)
    requirements = [x for x in requirements if str(x.get("clause") or "").strip() and str(x.get("requirement") or "").strip() and str(x.get("norm") or "").strip()]
    parts = []
    for item in requirements:
        meta = f"{item.get('norm')}, версия {item.get('version','—')}, стр. {item.get('page','—')}, п. {item.get('clause')}"
        rule = f"оператор {item.get('operator') or '—'}, нормативное значение {item.get('normative_value') if item.get('normative_value') is not None else '—'} {item.get('normative_unit') or ''}".strip()
        parts.append(f"{meta}: {rule}\nТекст требования: {item['requirement']}")
    value = "\n\n".join(parts)
    return value[:12000] + ("\n[нормативный контекст сокращён]" if len(value) > 12000 else ""), requirements


def _bbox_has_real_evidence(image_path: Path, bbox: list[float]) -> bool:
    try:
        with Image.open(image_path).convert("L") as image:
            width, height = image.size
            x1, y1, x2, y2 = bbox
            area = max(1.0, (x2 - x1) * (y2 - y1))
            if area / float(width * height) > 0.82:
                return False
            crop = image.crop((int(x1), int(y1), int(x2), int(y2)))
            pixels = list(crop.getdata())
            return bool(pixels) and sum(1 for value in pixels if value < 245) / len(pixels) >= 0.001
    except Exception:
        return False


def _build_check_matrix(skill: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix = []
    for check in skill["checks"]:
        check_id = str(check["id"])
        related = [x for x in findings if str(x.get("check_id") or "") == check_id]
        matrix.append({"id": check_id, "name": check["name"], "candidates": len(related), "violations": sum(x.get("type") == "violation" for x in related), "compliant": sum(x.get("type") == "compliant" for x in related), "unchecked": sum(x.get("type") == "unchecked" for x in related), "status": "evidence_found" if related else "no_evidence_candidate"})
    return matrix


def _build_report(document_id: str, pdf_name: str, norms, total_pages: int, findings: list[dict[str, Any]], failed_pages: list[int], skill: dict[str, Any], model: str, selected_pages: list[int], status: str = "completed") -> dict[str, Any]:
    basis = [{"number": d.get("number"), "version": v.get("id"), "title": d.get("title")} for d, v, _ in norms]
    violations = [x for x in findings if x.get("type") == "violation"]
    compliant = [x for x in findings if x.get("type") == "compliant"]
    unchecked = [x for x in findings if x.get("type") == "unchecked"]
    checked_pages = sorted({int(x.get("page")) for x in findings if x.get("page")})
    report = {
        "template": "reference_normcontrol_report_ios_3.1", "document_id": document_id, "document_name": pdf_name,
        "skill_id": skill["id"], "skill_name": skill["name"], "checked_at": datetime.now().isoformat(timespec="seconds"),
        "status": status, "model": {"requested": model, "actual": model},
        "normative_document": ", ".join(str(x.get("number")) for x in basis if x.get("number")) or DEFAULT_NORM_NUMBER,
        "normative_version": ", ".join(str(x.get("version")) for x in basis if x.get("version")), "normative_basis": basis,
        "results": findings, "check_matrix": _build_check_matrix(skill, findings),
        "summary": {"pages": len(selected_pages), "pages_available": total_pages, "total": len(violations), "violations": len(violations), "critical": sum(x.get("severity") == "critical" for x in violations), "major": sum(x.get("severity") == "major" for x in violations), "minor": sum(x.get("severity") == "minor" for x in violations), "compliant": len(compliant), "unchecked": len(unchecked)},
        "check_scope": {"total_pages": total_pages, "pages_checked": len(checked_pages), "pages_available": total_pages, "limited": len(selected_pages) != total_pages, "mode": "whole_document" if len(selected_pages) == total_pages else "selected", "requested_pages": selected_pages, "checked_pages": checked_pages, "failed_pages": failed_pages},
    }
    return prepare_public_report(report)


def _finalise_decision(decision: dict[str, Any], candidate: dict[str, Any], requirements: list[dict[str, Any]]) -> dict[str, Any]:
    decision = dict(decision or {})
    decision["type"] = decision.get("type") if decision.get("type") in {"violation", "compliant", "unchecked"} else "unchecked"
    valid = [r for r in requirements if r.get("clause") and r.get("requirement") and r.get("norm")]
    if decision["type"] in {"violation", "compliant"}:
        if not valid:
            decision["type"] = "unchecked"
            decision["comparison"] = "не определено"
        else:
            selected = valid[0]
            decision["norm"] = str(selected.get("norm") or "")
            decision["clause"] = str(selected.get("clause") or "")
            decision["normative_requirement"] = str(selected.get("requirement") or "")
    if decision["type"] == "violation":
        decision["title"] = str(decision.get("title") or "Нарушение требований нормативной документации")
        decision["description"] = str(decision.get("description") or "")
        decision["recommendation"] = str(decision.get("recommendation") or "Привести проектное решение в соответствие с указанным нормативным требованием.")
    return decision


def _dedupe_page_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    result = []
    for candidate in candidates:
        key = (str(candidate.get("check_id") or ""), re.sub(r"\s+", " ", str(candidate.get("evidence_text") or "").lower()).strip(), str(candidate.get("project_value") or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def run_resilient_check(document_id: str, normative_number: str = DEFAULT_NORM_NUMBER, progress_callback: ProgressCallback | None = None, skill_id: str = "vk_wastewater", model: str | None = None, selected_pages: list[int] | None = None, cancel_event=None) -> dict[str, Any]:
    skill = get_skill(skill_id)

    def progress(**data):
        if progress_callback:
            progress_callback(data)

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    pdf_path = root / "source.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Исходный PDF не найден")
    evidence_dir = root / "checking" / "first_pass"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = _checkpoint_path(evidence_dir)
    storage = KnowledgeStorage()
    norms = _indexed_norms(storage)
    if not norms:
        raise RuntimeError("Нет индексированных действующих нормативных документов. Индексируйте действующие СП в разделе «Нормы».")
    if not model:
        raise RuntimeError("Модель для проверки не выбрана")
    probe = LMStudioClient(model=model, cancel_event=cancel_event)
    available_models = [str(item.get("id")) for item in probe.get_models().get("data", []) if isinstance(item, dict) and item.get("id")]
    if model not in available_models:
        raise RuntimeError(f"Выбранная модель недоступна в LM Studio: {model}")

    progress(stage="preparing", percent=1, current_page=0, total_pages=0, message=f"Подготовка Skill «{skill['name']}»: {len(skill['checks'])} предметных проверок…")
    pages = render_pdf_pages(pdf_path, evidence_dir, dpi=CHECK_DPI)
    total_pages = len(pages)
    selected_pages = sorted({int(x) for x in (selected_pages or list(range(1, total_pages + 1)))})
    if not selected_pages or any(x < 1 or x > total_pages for x in selected_pages):
        raise RuntimeError(f"Некорректный набор страниц. Допустим диапазон 1-{total_pages}")
    checkpoint = _load_checkpoint(checkpoint_file, document_id, pdf_path.name, skill_id, model, selected_pages)
    completed_pages = {int(x) for x in checkpoint.get("completed_pages", []) if int(x) in selected_pages}
    findings = [x for x in checkpoint.get("findings", []) if isinstance(x, dict) and int(x.get("page", 0) or 0) in selected_pages]
    next_finding_id = max((int(x.get("id", 0) or 0) for x in findings), default=0) + 1
    progress(stage="visual", percent=2, current_page=max(completed_pages, default=0), total_pages=total_pages, pages_available=total_pages, pages_checked=len(completed_pages), requested_pages=selected_pages, message=f"Подготовлено страниц: {total_pages}. К проверке выбрано: {len(selected_pages)}.")
    failed_pages: list[int] = []

    for page_index in selected_pages:
        if cancel_event is not None and cancel_event.is_set():
            report = _build_report(document_id, pdf_path.name, norms, total_pages, findings, failed_pages, skill, model, selected_pages, "partial")
            report["status"] = "partial"
            return report
        if page_index in completed_pages:
            continue
        page = pages[page_index - 1]
        page_start = 2 + int(selected_pages.index(page_index) / max(len(selected_pages), 1) * 96)
        page_success = False
        last_error = None
        for attempt in range(1, MAX_PAGE_RETRIES + 1):
            if cancel_event is not None and cancel_event.is_set():
                report = _build_report(document_id, pdf_path.name, norms, total_pages, findings, failed_pages, skill, model, selected_pages, "partial")
                report["status"] = "partial"
                return report
            client = LMStudioClient(model=model, cancel_event=cancel_event)
            try:
                progress(stage="visual", percent=page_start, current_page=page_index, total_pages=total_pages, pages_available=total_pages, pages_checked=len(completed_pages), retry=attempt if attempt > 1 else 0, message=f"Аудит страницы {page_index} из {total_pages}: модель {model}…")
                raw = _json_array(_vision_request(client, __import__("app.checking.vk_audit", fromlist=["build_vk_audit_prompt"]).build_vk_audit_prompt(page.page, skill_id), Path(page.image_path), 1400))
                candidates = _dedupe_page_candidates(_filter_skill_candidates(_strict_candidates(raw), skill, page.page))
                progress(stage="normative", percent=min(98, page_start + 1), current_page=page_index, total_pages=total_pages, pages_available=total_pages, pages_checked=len(completed_pages), message=f"Страница {page_index}: {len(candidates)} предметных кандидатов. RAG → normative requirement → decision…")
                page_findings = []
                for candidate in candidates:
                    if cancel_event is not None and cancel_event.is_set():
                        raise CheckCancelled("Проверка отменена пользователем")
                    bbox = normalize_bbox(candidate.get("bbox"), page.width, page.height)
                    if not bbox or not _bbox_has_real_evidence(Path(page.image_path), bbox):
                        continue
                    norm_results = retrieve_audit_context(norms, candidate, top_k=MAX_NORM_RESULTS, skill_id=skill_id)
                    norm_text, normative_requirements = _multi_context(norm_results, candidate)
                    if not normative_requirements:
                        continue
                    decision = decide_audit(client, candidate, norm_text)
                    decision = deterministic_numeric_comparison(candidate, decision, normative_requirements)
                    decision = _finalise_decision(decision, candidate, normative_requirements)
                    table_row = build_table_check_row(candidate, decision, page.page, norm_results)
                    finding_id = next_finding_id + len(page_findings)
                    evidence_path = evidence_dir / "annotated" / f"page_{page.page:04d}_finding_{finding_id:03d}.png"
                    evidence_image = annotate_evidence(page.image_path, bbox, evidence_path)
                    page_findings.append({"id": finding_id, "type": decision.get("type", "unchecked"), "check_id": str(candidate.get("check_id") or ""), "check_name": str(candidate.get("check_name") or ""), "docId": document_id, "docName": pdf_path.name, "skill_id": skill_id, "skill_name": skill["name"], "title": str(decision.get("title") or candidate.get("title") or "Результат проверки"), "description": str(decision.get("description") or candidate.get("description") or ""), "recommendation": str(decision.get("recommendation") or ""), "sheet": str(decision.get("sheet") or page.page), "norm": table_row.norm, "clause": table_row.clause, "parameter": table_row.parameter, "project_value": table_row.project_value_raw, "project_value_raw": table_row.project_value_raw, "project_unit": table_row.project_unit, "normative_requirement": table_row.normative_requirement, "normative_value": table_row.normative_value_raw, "normative_value_raw": table_row.normative_value_raw, "normative_unit": table_row.normative_unit, "comparison": table_row.comparison, "project_value_normalized": table_row.project_value, "project_kind": table_row.project_kind, "normative_value_normalized": table_row.normative_value, "normative_kind": table_row.normative_kind, "source_row": table_row.source_row, "source_context": table_row.source_context, "table_check": table_row.to_dict(), "severity": str(decision.get("severity") or "minor"), "page": page.page, "bbox": bbox, "evidence_image": evidence_image, "image": f"{REPORT_API_BASE}/api/reports/evidence/{document_id}/{evidence_path.name}", "evidence_text": table_row.evidence_text, "confidence": table_row.confidence, "normative_route": candidate.get("normative_route"), "normative_requirements": normative_requirements, "normative_sources": norm_results})
                findings.extend(page_findings)
                next_finding_id += len(page_findings)
                completed_pages.add(page_index)
                checkpoint.update({"status": "running", "model": model, "selected_pages": selected_pages, "pages_completed": len(completed_pages), "completed_pages": sorted(completed_pages), "findings": findings, "last_error": None})
                _write_json(checkpoint_file, checkpoint)
                page_success = True
                progress(stage="visual", percent=min(98, 2 + int((selected_pages.index(page_index) + 1) / max(len(selected_pages), 1) * 96)), current_page=page_index, total_pages=total_pages, pages_available=total_pages, pages_checked=len(completed_pages), page_completed=True, message=f"Страница {page_index} из {total_pages} завершена. Результатов Skill: {len(page_findings)}.")
                break
            except CheckCancelled:
                report = _build_report(document_id, pdf_path.name, norms, total_pages, findings, failed_pages, skill, model, selected_pages, "partial")
                report["status"] = "partial"
                return report
            except Exception as error:
                last_error = error
                checkpoint["last_error"] = {"page": page_index, "attempt": attempt, "error": str(error), "at": datetime.now().isoformat(timespec="seconds")}
                _write_json(checkpoint_file, checkpoint)
                if attempt < MAX_PAGE_RETRIES:
                    progress(stage="retry", percent=page_start, current_page=page_index, total_pages=total_pages, retry=attempt, message=f"Ошибка страницы {page_index}: {error}. Повторяю через {int(RETRY_DELAY_SECONDS)} с…")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    failed_pages.append(page_index)
                    progress(stage="error", percent=page_start, current_page=page_index, total_pages=total_pages, message=f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {error}")
        if not page_success:
            raise RuntimeError(f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {last_error}")

    report = _build_report(document_id, pdf_path.name, norms, total_pages, findings, failed_pages, skill, model, selected_pages, "completed")
    _write_json(evidence_dir / "report.json", report)
    checkpoint.update({"status": "completed", "model": model, "selected_pages": selected_pages, "pages_completed": len(selected_pages), "completed_pages": selected_pages, "findings": findings, "last_error": None})
    _write_json(checkpoint_file, checkpoint)
    progress(stage="completed", percent=100, current_page=max(selected_pages), total_pages=total_pages, pages_available=total_pages, pages_checked=len(selected_pages), page_completed=True, message=f"Проверка завершена. Обработано {len(selected_pages)} из {total_pages} страниц; модель: {model}. Отчёт готов.")
    return report


def _filter_skill_candidates(candidates: list[dict[str, Any]], skill: dict[str, Any], page_number: int) -> list[dict[str, Any]]:
    allowed = {str(item["id"]): item for item in skill["checks"]}
    counts: dict[str, int] = {}
    accepted = []
    for candidate in candidates:
        check_id = str(candidate.get("check_id") or "").strip()
        if check_id not in allowed:
            continue
        candidate["page"] = page_number
        candidate["check_name"] = allowed[check_id]["name"]
        counts[check_id] = counts.get(check_id, 0) + 1
        if counts[check_id] > MAX_CANDIDATES_PER_CHECK_PER_PAGE:
            continue
        accepted.append(candidate)
        if len(accepted) >= MAX_PAGE_CANDIDATES:
            break
    return accepted
