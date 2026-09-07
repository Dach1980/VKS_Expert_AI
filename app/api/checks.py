"""Project Expert AI — asynchronous document checking API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.documents import DOCUMENTS_ROOT
from app.checking.jobs import cancel_check_job, get_check_job, mark_check_job, start_check_job
from app.checking.scope import get_pdf_page_count, normalize_page_scope
from app.llm.lmstudio_client import LMStudioClient
from app.reporting.report_contract import prepare_job_result
from app.skills.registry import get_skill

router = APIRouter(prefix="/api/checks", tags=["checks"])


@router.get("/models")
def available_models():
    try:
        data = LMStudioClient().get_models()
        models = [str(item.get("id")) for item in data.get("data", []) if isinstance(item, dict) and item.get("id") and "embedding" not in str(item.get("id")).lower()]
        return {"success": True, "models": models}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось получить модели из LM Studio: {error}") from error


@router.post("/{document_id}")
def check_document(
    document_id: str,
    skill_id: str = Query("vk_wastewater", description="Профиль экспертной проверки"),
    model: str = Query("", description="Явно выбранная модель LM Studio"),
    whole_document: bool = Query(True, description="Проверять весь документ"),
    page_ranges: str = Query("", description="Диапазоны страниц, например 1-3, 7, 12-15"),
):
    root = DOCUMENTS_ROOT / document_id
    parsed = root / "parsed.json"
    source = root / "source.pdf"
    if not root.exists() or not source.exists():
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not parsed.exists():
        raise HTTPException(status_code=409, detail="Документ ещё не обработан. Дождитесь завершения обработки PDF.")
    try:
        skill = get_skill(skill_id)
        total_pages = get_pdf_page_count(source)
        selected_pages = normalize_page_scope(total_pages, whole_document, page_ranges)
        if not model:
            raise ValueError("Перед началом проверки необходимо выбрать модель")
        client = LMStudioClient()
        available = [str(item.get("id")) for item in client.get_models().get("data", []) if isinstance(item, dict) and item.get("id") and "embedding" not in str(item.get("id")).lower()]
        if model not in available:
            raise ValueError(f"Выбранная модель недоступна в LM Studio: {model}")
        return {"success": True, "skill_id": skill["id"], "skill_name": skill["name"], "normative_documents": skill["normative_documents"], "total_pages": total_pages, "requested_pages": selected_pages, "model": {"requested": model}, **start_check_job(document_id, skill_id, model, selected_pages)}
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
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
    payload = {"success": True, **job}
    if payload.get("status") == "completed" and isinstance(payload.get("result"), dict):
        payload["result"] = prepare_job_result(payload["result"])
    return payload


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = cancel_check_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача проверки не найдена")
    return {"success": True, **job}


@router.post("/jobs/{job_id}/mark")
def mark_job(job_id: str):
    job = mark_check_job(job_id)
    if job is None:
        raise HTTPException(status_code=409, detail="Текущий результат проверки ещё недоступен для фиксации")
    payload = {"success": True, **job}
    if isinstance(payload.get("result"), dict):
        payload["result"] = prepare_job_result(payload["result"])
    return payload
