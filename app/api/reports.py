"""Project Expert AI — report API backed by the canonical report contract."""
from __future__ import annotations

import io
import json
from pathlib import Path

import fitz
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.documents import DOCUMENTS_ROOT
from app.reporting.report_contract import prepare_public_report
from app.reporting.ios31 import build_docx
from app.reporting.ios31_pdf import build_pdf

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


def _save_report(document_id: str, report: dict) -> None:
    path = DOCUMENTS_ROOT / document_id / "checking" / "first_pass" / "report.json"
    try:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _document_filename(document_id: str, report: dict) -> str:
    current = str(report.get("document_name") or "").strip()
    if current and current.lower() != "source.pdf":
        return current
    registry_path = DOCUMENTS_ROOT / "documents.json"
    try:
        items = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        items = []
    item = next((x for x in items if str(x.get("id")) == document_id), None)
    if item:
        filename = str(item.get("filename") or "").strip()
        if filename:
            return filename
        name = str(item.get("name") or "").strip()
        if name:
            return f"{name}.pdf"
    source = str(report.get("source") or "").strip()
    return source if source and source.lower() != "source.pdf" else "Документ.pdf"


def _report_page_count(report: dict) -> int | None:
    for key in ("report_pages", "pdf_pages", "generated_report_pages", "pages_report"):
        try:
            value = int(report.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    try:
        pdf_data = build_pdf(report)
        with fitz.open(stream=pdf_data, filetype="pdf") as document:
            return document.page_count
    except Exception:
        return None


def _enrich_report(document_id: str, report: dict) -> dict:
    # Normalize before enrichment so every consumer sees the same report model.
    report = prepare_public_report(report)
    changed = False
    filename = _document_filename(document_id, report)
    if report.get("document_name") != filename:
        report["document_name"] = filename
        changed = True
    page_count = _report_page_count(report)
    if page_count is not None and report.get("report_pages") != page_count:
        report["report_pages"] = page_count
        changed = True
    report["template"] = REPORT_TEMPLATE
    if changed:
        _save_report(document_id, report)
    return report


def _report_for_document(document_id: str) -> dict:
    report = _load_saved_report(document_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт для документа ещё не сформирован")
    return _enrich_report(document_id, report)


@router.get("")
def list_reports():
    items = []
    if DOCUMENTS_ROOT.exists():
        for root in DOCUMENTS_ROOT.iterdir():
            if root.is_dir():
                report = _load_saved_report(root.name)
                if report:
                    items.append(_enrich_report(root.name, report))
    items.sort(key=lambda x: str(x.get("checked_at") or ""), reverse=True)
    return {"reports": items}


@router.get("/{document_id}")
def get_report(document_id: str):
    return {"success": True, **_report_for_document(document_id)}


@router.post("/create/{document_id}")
def create_report(document_id: str):
    return {"success": True, **_report_for_document(document_id)}


@router.post("/pdf")
def export_pdf(report: dict):
    try:
        data = build_pdf(prepare_public_report(report))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать PDF: {error}") from error
    document_id = str(report.get("document_id", "report"))
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="project-expert-ai-check-{document_id}.pdf"'},
    )


@router.post("/docx")
def export_docx(report: dict):
    try:
        data = build_docx(prepare_public_report(report))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать Word: {error}") from error
    document_id = str(report.get("document_id", "report"))
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="project-expert-ai-check-{document_id}.docx"'},
    )
