"""Project Expert AI — report API backed by the IOS 3.1 report builder."""
from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.documents import DOCUMENTS_ROOT
from app.reporting.ios31 import build_docx, build_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])
REPORT_TEMPLATE = "reference_normcontrol_report_ios_3.1"


def _load_saved_report(document_id: str) -> dict | None:
    path = DOCUMENTS_ROOT / document_id / "checking" / "first_pass" / "report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _report_for_document(document_id: str) -> dict:
    report = _load_saved_report(document_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт для документа ещё не сформирован")
    report["template"] = REPORT_TEMPLATE
    return report


@router.get("/{document_id}")
def get_report(document_id: str):
    return {"success": True, **_report_for_document(document_id)}


@router.post("/create/{document_id}")
def create_report(document_id: str):
    report = _report_for_document(document_id)
    return {"success": True, **report}


@router.post("/pdf")
def export_pdf(report: dict):
    try:
        data = build_pdf(report)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать PDF: {error}") from error
    document_id = str(report.get("document_id", "report"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="project-expert-ai-check-{document_id}.pdf"'})


@router.post("/docx")
def export_docx(report: dict):
    try:
        data = build_docx(report)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать Word: {error}") from error
    document_id = str(report.get("document_id", "report"))
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="project-expert-ai-check-{document_id}.docx"'})
