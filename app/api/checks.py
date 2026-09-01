"""Project Expert AI — asynchronous document checking API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.documents import DOCUMENTS_ROOT
from app.checking.jobs import get_check_job, start_check_job

router = APIRouter(prefix="/api/checks", tags=["checks"])


@router.post("/{document_id}")
def check_document(document_id: str):
    """Start a background first-pass check and return immediately with a job id."""
    root = DOCUMENTS_ROOT / document_id
    parsed = root / "parsed.json"
    source = root / "source.pdf"
    if not root.exists() or not source.exists():
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not parsed.exists():
        raise HTTPException(status_code=409, detail="Документ ещё не обработан. Дождитесь завершения обработки PDF.")
    try:
        return {"success": True, **start_check_job(document_id)}
    except RuntimeError as error:
        message = str(error)
        if "Registry" in message or "действующ" in message:
            raise HTTPException(status_code=409, detail=message) from error
        raise HTTPException(status_code=503, detail=message) from error


@router.get("/jobs/{job_id}")
def check_job_status(job_id: str):
    job = get_check_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача проверки не найдена")
    return {"success": True, **job}
