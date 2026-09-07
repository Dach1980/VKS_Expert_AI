"""In-process background jobs and progress estimation for document checks."""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.checking.audit_trace import run_traced_resilient_check
from app.checking.scope import CheckCancelled
from app.checking.vision_structured import structured_vision_request
from app.reporting.result_store import save_result

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_STAGE_LABELS = {
    "queued": "Ожидание запуска", "preparing": "Подготовка документа", "visual": "Визуальный анализ страниц",
    "normative": "Нормативная проверка через RAG", "retry": "Повторная попытка страницы",
    "completed": "Формирование отчёта", "partial": "Частичный результат", "cancelled": "Проверка остановлена", "error": "Ошибка проверки",
}


def _update(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(fields)
        stage = str(job.get("stage", "queued"))
        job["stage_label"] = _STAGE_LABELS.get(stage, stage)
        started = job.get("started_monotonic")
        total_pages = int(job.get("total_pages", 0) or 0)
        completed_pages = int(job.get("pages_completed", 0) or 0)
        if started:
            elapsed = max(0.0, time.monotonic() - started)
            job["elapsed_seconds"] = round(elapsed)
            if total_pages > 0 and completed_pages > 0 and completed_pages < total_pages:
                spp = elapsed / completed_pages
                job["average_seconds_per_page"] = round(spp, 1)
                job["estimated_remaining_seconds"] = round(spp * (total_pages - completed_pages))
            elif total_pages > 0 and completed_pages >= total_pages:
                job["average_seconds_per_page"] = round(elapsed / max(completed_pages, 1), 1)
                job["estimated_remaining_seconds"] = 0
            else:
                job["estimated_remaining_seconds"] = None


def _progress(job_id: str, data: dict[str, Any]) -> None:
    fields = dict(data)
    if data.get("page_completed"):
        current = int(data.get("current_page", 0) or 0)
        with _lock:
            job = _jobs.get(job_id)
            previous = int(job.get("pages_completed", 0) or 0) if job else 0
        fields["pages_completed"] = max(previous, current)
    _update(job_id, **fields)


def _worker(job_id: str, document_id: str, skill_id: str, model: str, selected_pages: list[int]) -> None:
    with _lock:
        cancel_event = _jobs[job_id]["cancel_event"]
    _update(job_id, status="running", started_at=datetime.now().isoformat(timespec="seconds"), started_monotonic=time.monotonic(), model=model, requested_pages=selected_pages)
    try:
        from app.checking import resilient
        original_vision_request = resilient._vision_request
        original_run = resilient.run_resilient_check
        resilient._vision_request = structured_vision_request
        resilient.run_resilient_check = lambda doc_id, normative_number="СП 30.13330.2020", progress_callback=None, skill_id=skill_id: original_run(doc_id, normative_number=normative_number, progress_callback=progress_callback, skill_id=skill_id, model=model, selected_pages=selected_pages, cancel_event=cancel_event)
        try:
            report = run_traced_resilient_check(document_id, normative_number="СП 30.13330.2020", progress_callback=lambda data: _progress(job_id, data), skill_id=skill_id)
        finally:
            resilient.run_resilient_check = original_run
            resilient._vision_request = original_vision_request

        report = dict(report)
        status = str(report.get("status") or "completed")
        report.setdefault("model", {"requested": model, "actual": model})
        if status == "partial":
            checked = int((report.get("check_scope") or {}).get("pages_checked", 0) or 0)
            _update(job_id, status="cancelled", stage="cancelled", percent=checked / max(len(selected_pages), 1) * 100, message="Проверка остановлена. Текущий результат можно зафиксировать.", result=report, pages_completed=checked, pages_checked=checked, pages_available=len(selected_pages), total_pages=len(selected_pages), finished_at=datetime.now().isoformat(timespec="seconds"))
            return

        document_root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
        result_path = save_result(document_root, report)
        report["result_file"] = result_path.name
        report["result_id"] = result_path.stem
        scope = report.get("check_scope") or {}
        pages_checked = int(scope.get("pages_checked", 0) or 0)
        pages_available = int(scope.get("pages_available", len(selected_pages)) or len(selected_pages))
        _update(job_id, status="completed", percent=100, stage="completed", message="Проверка завершена. Результат сохранён.", result=report, result_file=result_path.name, current_page=max(selected_pages), total_pages=pages_available, pages_completed=pages_checked, pages_checked=pages_checked, pages_available=pages_available, failed_pages=scope.get("failed_pages", []), report_url=f"/api/reports/{document_id}", report_pdf_url="/api/reports/pdf", report_docx_url="/api/reports/docx", finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)
    except CheckCancelled:
        _update(job_id, status="cancelled", stage="cancelled", message="Проверка остановлена пользователем. Текущий результат можно зафиксировать.", finished_at=datetime.now().isoformat(timespec="seconds"))
    except Exception as error:
        _update(job_id, status="error", stage="error", percent=100, message=f"Ошибка проверки: {error}", error=str(error), finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)


def start_check_job(document_id: str, skill_id: str = "vk_wastewater", model: str = "", selected_pages: list[int] | None = None) -> dict[str, Any]:
    if not model:
        raise ValueError("Модель для проверки не выбрана")
    if not selected_pages:
        raise ValueError("Не выбраны страницы для проверки")
    job_id = uuid.uuid4().hex
    cancel_event = threading.Event()
    with _lock:
        _jobs[job_id] = {"job_id": job_id, "document_id": document_id, "skill_id": skill_id, "model": model, "requested_pages": selected_pages, "status": "queued", "stage": "queued", "stage_label": _STAGE_LABELS["queued"], "percent": 0, "current_page": 0, "total_pages": 0, "pages_completed": 0, "pages_checked": 0, "pages_available": None, "message": "Проверка поставлена в очередь…", "estimated_remaining_seconds": None, "average_seconds_per_page": None, "elapsed_seconds": 0, "created_at": datetime.now().isoformat(timespec="seconds"), "cancel_event": cancel_event}
    thread = threading.Thread(target=_worker, args=(job_id, document_id, skill_id, model, selected_pages), daemon=True, name=f"check-{job_id[:8]}")
    with _lock:
        _jobs[job_id]["thread"] = thread
    thread.start()
    return get_check_job(job_id) or {}


def cancel_check_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if str(job.get("status")) in {"completed", "error", "cancelled"}:
            return {k: v for k, v in job.items() if k not in {"started_monotonic", "cancel_event", "thread"}}
        job["cancel_requested"] = True
        event = job.get("cancel_event")
        if event:
            event.set()
    _update(job_id, message="Запрошена остановка проверки…")
    return get_check_job(job_id)


def mark_check_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        report = job.get("result")
        document_id = job.get("document_id")
    if not isinstance(report, dict) or not document_id:
        return None
    document_root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / str(document_id)
    report = dict(report)
    report["status"] = "partial"
    report["marked_at"] = datetime.now().isoformat(timespec="seconds")
    result_path = save_result(document_root, report)
    report["result_file"] = result_path.name
    report["result_id"] = result_path.stem
    _update(job_id, result=report, result_file=result_path.name, result_id=result_path.stem, marked=True, marked_at=report["marked_at"], message="Текущий результат зафиксирован.")
    return get_check_job(job_id)


def get_check_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        return {k: v for k, v in job.items() if k not in {"started_monotonic", "cancel_event", "thread"}}
