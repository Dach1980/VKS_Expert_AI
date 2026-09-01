"""In-process background jobs and progress estimation for document checks."""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime
from typing import Any

from app.checking.first_pass import run_first_pass_api

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

_STAGE_LABELS = {
    "queued": "Ожидание запуска",
    "preparing": "Подготовка документа",
    "visual": "Визуальный анализ страниц",
    "normative": "Нормативная проверка через RAG",
    "completed": "Формирование отчёта",
    "error": "Ошибка проверки",
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
        current_page = int(job.get("current_page", 0) or 0)
        if started:
            elapsed = max(0.0, time.monotonic() - started)
            job["elapsed_seconds"] = round(elapsed)
            # ETA is based on completed pages rather than the arbitrary visual percent.
            if total_pages > 0 and current_page > 0 and current_page < total_pages:
                seconds_per_page = elapsed / current_page
                remaining_pages = total_pages - current_page
                job["average_seconds_per_page"] = round(seconds_per_page, 1)
                job["estimated_remaining_seconds"] = round(seconds_per_page * remaining_pages)
            elif total_pages > 0 and current_page >= total_pages:
                job["average_seconds_per_page"] = round(elapsed / total_pages, 1)
                job["estimated_remaining_seconds"] = 0
            else:
                job["estimated_remaining_seconds"] = None


def _worker(job_id: str, document_id: str) -> None:
    _update(job_id, status="running", started_at=datetime.now().isoformat(timespec="seconds"), started_monotonic=time.monotonic())
    try:
        report = run_first_pass_api(document_id, progress_callback=lambda data: _update(job_id, **data))
        _update(job_id, status="completed", percent=100, stage="completed", message="Проверка завершена. Отчёт готов.", result=report, finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)
    except Exception as error:
        _update(job_id, status="error", stage="error", percent=100, message=f"Ошибка проверки: {error}", error=str(error), finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)


def start_check_job(document_id: str) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id, "document_id": document_id, "status": "queued", "stage": "queued",
            "stage_label": _STAGE_LABELS["queued"], "percent": 0, "current_page": 0, "total_pages": 0,
            "message": "Проверка поставлена в очередь…", "estimated_remaining_seconds": None,
            "average_seconds_per_page": None, "elapsed_seconds": 0, "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    thread = threading.Thread(target=_worker, args=(job_id, document_id), daemon=True, name=f"check-{job_id[:8]}")
    thread.start()
    return get_check_job(job_id) or {}


def get_check_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        return {k: v for k, v in job.items() if k != "started_monotonic"}
