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


def _update(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.update(fields)
            started = job.get("started_monotonic")
            percent = float(job.get("percent", 0) or 0)
            if started and percent >= 2:
                elapsed = max(0.0, time.monotonic() - started)
                rate = elapsed / max(percent - 2, 1)
                remaining = max(0.0, (100 - percent) * rate)
                job["elapsed_seconds"] = round(elapsed)
                job["estimated_remaining_seconds"] = round(remaining)


def _worker(job_id: str, document_id: str) -> None:
    _update(job_id, status="running", started_at=datetime.now().isoformat(timespec="seconds"), started_monotonic=time.monotonic())
    try:
        report = run_first_pass_api(document_id, progress_callback=lambda data: _update(job_id, **data))
        _update(job_id, status="completed", percent=100, message="Проверка завершена", result=report, finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)
    except Exception as error:
        _update(job_id, status="error", percent=100, message=f"Ошибка проверки: {error}", error=str(error), finished_at=datetime.now().isoformat(timespec="seconds"), estimated_remaining_seconds=0)


def start_check_job(document_id: str) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {"job_id": job_id, "document_id": document_id, "status": "queued", "stage": "queued", "percent": 0, "current_page": 0, "total_pages": 0, "message": "Проверка поставлена в очередь…", "estimated_remaining_seconds": None, "elapsed_seconds": 0, "created_at": datetime.now().isoformat(timespec="seconds")}
    thread = threading.Thread(target=_worker, args=(job_id, document_id), daemon=True, name=f"check-{job_id[:8]}")
    thread.start()
    return get_check_job(job_id) or {}


def get_check_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        return {k: v for k, v in job.items() if k != "started_monotonic"}
