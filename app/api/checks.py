"""Project Expert AI — document checking API.

The endpoint is now the executable first-pass pipeline:
PDF pages -> Qwen VL -> bbox -> version-aware RAG -> compliance decision ->
red evidence images -> report-ready JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.checking.first_pass import run_first_pass_api
from app.api.documents import DOCUMENTS_ROOT

router = APIRouter(prefix="/api/checks", tags=["checks"])


@router.post("/{document_id}")
def check_document(document_id: str):
    """Run the complete first-pass check for one uploaded project PDF."""
    root = DOCUMENTS_ROOT / document_id
    parsed = root / "parsed.json"
    source = root / "source.pdf"
    if not root.exists() or not source.exists():
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not parsed.exists():
        raise HTTPException(status_code=409, detail="Документ ещё не обработан. Дождитесь завершения обработки PDF.")

    try:
        report = run_first_pass_api(document_id)
    except RuntimeError as error:
        message = str(error)
        if "Registry" in message or "действующ" in message:
            raise HTTPException(status_code=409, detail=message) from error
        raise HTTPException(status_code=503, detail=message) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=409, detail=f"Не найден ресурс для проверки: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Проверка не выполнена: {error}") from error

    return {"success": True, **report}
