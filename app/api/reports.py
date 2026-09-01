"""Project Expert AI — report generation API.

The report API consumes the first-pass CheckReport JSON produced by /api/checks.
PDF/DOCX exports preserve the reference IOS 3.1 structure and include saved
annotated evidence images with red rectangles whenever bbox was verified.
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

import fitz
from docx import Document
from docx.shared import Inches
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.lib import colors

from app.api.documents import DOCUMENTS_ROOT

router = APIRouter(prefix="/api/reports", tags=["reports"])
REPORT_TEMPLATE = "reference_normcontrol_report_ios_3.1"


def _safe_text(value) -> str:
    return str(value or "").strip()


def _document_pdf(document_id: str) -> Path | None:
    root = DOCUMENTS_ROOT / document_id
    if not root.exists():
        return None
    source = root / "source.pdf"
    if source.exists():
        return source
    candidates = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    return candidates[0] if candidates else None


def _saved_evidence_image(finding: dict) -> bytes | None:
    value = _safe_text(finding.get("evidence_image") or finding.get("image"))
    if value:
        path = Path(value)
        if path.exists() and path.is_file():
            try:
                return path.read_bytes()
            except OSError:
                pass
    return None


def _evidence_image(finding: dict) -> bytes | None:
    """Use persisted evidence first; otherwise render the PDF using PDF-space bbox."""
    saved = _saved_evidence_image(finding)
    if saved:
        return saved

    document_id = _safe_text(finding.get("docId"))
    page_number = int(finding.get("page") or 0)
    bbox = finding.get("bbox")
    if not document_id or page_number <= 0 or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    pdf_path = _document_pdf(document_id)
    if not pdf_path:
        return None
    try:
        pdf = fitz.open(pdf_path)
        if page_number > len(pdf):
            pdf.close()
            return None
        page = pdf[page_number - 1]
        rect = [float(x) for x in bbox]
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(*rect))
        shape.finish(color=(1, 0, 0), width=2)
        shape.commit()
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        data = pix.tobytes("png")
        pdf.close()
        return data
    except Exception:
        return None


def _load_saved_report(document_id: str) -> dict | None:
    path = DOCUMENTS_ROOT / document_id / "checking" / "first_pass" / "report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _summary(report: dict) -> dict:
    return report.get("summary") or {}


def _build_pdf(report: dict) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Finding", parent=styles["Heading2"], fontSize=12, leading=15, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name="RedTitle", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.red))

    story = [
        Paragraph("PROJECT EXPERT AI", styles["Title"]),
        Paragraph("ОТЧЁТ ПО РЕЗУЛЬТАТАМ ПРОВЕРКИ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", styles["Heading1"]),
        Spacer(1, 5 * mm),
        Paragraph(f"<b>Документ:</b> {_safe_text(report.get('document_name'))}", styles["BodyText"]),
        Paragraph(f"<b>Дата проверки:</b> {_safe_text(report.get('checked_at')) or datetime.now().strftime('%d.%m.%Y %H:%M')}", styles["BodyText"]),
        Paragraph(f"<b>Нормативная база:</b> {_safe_text(report.get('normative_document'))}", styles["BodyText"]),
        Paragraph(f"<b>Действующая версия:</b> {_safe_text(report.get('normative_version'))}", styles["BodyText"]),
        Spacer(1, 6 * mm),
    ]

    s = _summary(report)
    table = Table([
        ["Проверено страниц", "Всего результатов", "Нарушения", "Соответствия", "Не проверено", "Критические"],
        [s.get("pages", 0), s.get("total", 0), s.get("violations", 0), s.get("compliant", 0), s.get("unchecked", 0), s.get("critical", 0)],
    ], colWidths=[27 * mm, 27 * mm, 25 * mm, 27 * mm, 27 * mm, 27 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ]))
    story += [table, Spacer(1, 8 * mm), Paragraph("РЕЗУЛЬТАТЫ ПРОВЕРКИ", styles["Heading1"])]

    findings = report.get("results") or report.get("checks") or []
    if not findings:
        story.append(Paragraph("Результаты проверки отсутствуют.", styles["BodyText"]))

    for index, finding in enumerate(findings, 1):
        kind = {"violation": "НЕСООТВЕТСТВИЕ", "compliant": "СООТВЕТСТВИЕ", "unchecked": "НЕ ПРОВЕРЕНО"}.get(finding.get("type"), "РЕЗУЛЬТАТ")
        heading_style = styles["RedTitle"] if finding.get("type") == "violation" else styles["Finding"]
        story.append(KeepTogether([
            Paragraph(f"{index}. {kind}: {_safe_text(finding.get('title')) or 'Результат проверки'}", heading_style),
            Paragraph(f"<b>Страница:</b> {_safe_text(finding.get('page')) or '—'} &nbsp;&nbsp; <b>Лист:</b> {_safe_text(finding.get('sheet')) or '—'}", styles["Small"]),
            Paragraph(f"<b>Критичность:</b> {_safe_text(finding.get('severity')) or '—'}", styles["Small"]),
            Paragraph(f"<b>Норматив:</b> {_safe_text(finding.get('norm')) or '—'} &nbsp;&nbsp; <b>Пункт:</b> {_safe_text(finding.get('clause')) or '—'}", styles["Small"]),
            Spacer(1, 2 * mm),
            Paragraph(f"<b>Описание:</b> {_safe_text(finding.get('description')) or '—'}", styles["BodyText"]),
        ]))
        if finding.get("evidence_text"):
            story.append(Paragraph(f"<b>Фрагмент доказательства:</b> {_safe_text(finding.get('evidence_text'))}", styles["BodyText"]))
        if finding.get("recommendation"):
            story.append(Paragraph(f"<b>Рекомендация:</b> {_safe_text(finding.get('recommendation'))}", styles["BodyText"]))
        image_bytes = _evidence_image(finding)
        if image_bytes:
            story.append(Spacer(1, 3 * mm))
            story.append(Image(io.BytesIO(image_bytes), width=165 * mm, height=105 * mm))
            story.append(Paragraph(f"Доказательный фрагмент с красной рамкой — замечание №{index}", styles["Small"]))
        story.append(Spacer(1, 6 * mm))

    if report.get("conclusion"):
        story.append(PageBreak())
        story.append(Paragraph("ЗАКЛЮЧЕНИЕ", styles["Heading1"]))
        story.append(Paragraph(_safe_text(report.get("conclusion")), styles["BodyText"]))

    doc.build(story)
    return output.getvalue()


def _build_docx(report: dict) -> bytes:
    document = Document()
    document.add_heading("PROJECT EXPERT AI", level=0)
    document.add_heading("ОТЧЁТ ПО РЕЗУЛЬТАТАМ ПРОВЕРКИ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", level=1)
    document.add_paragraph(f"Документ: {_safe_text(report.get('document_name'))}")
    document.add_paragraph(f"Дата проверки: {_safe_text(report.get('checked_at')) or datetime.now().strftime('%d.%m.%Y %H:%M')}")
    document.add_paragraph(f"Нормативная база: {_safe_text(report.get('normative_document'))}")
    document.add_paragraph(f"Действующая версия: {_safe_text(report.get('normative_version'))}")

    s = _summary(report)
    table = document.add_table(rows=2, cols=6)
    headers = ["Страниц", "Результатов", "Нарушений", "Соответствий", "Не проверено", "Критических"]
    values = [s.get("pages", 0), s.get("total", 0), s.get("violations", 0), s.get("compliant", 0), s.get("unchecked", 0), s.get("critical", 0)]
    for i, value in enumerate(headers):
        table.cell(0, i).text = value
        table.cell(1, i).text = str(values[i])

    document.add_heading("РЕЗУЛЬТАТЫ ПРОВЕРКИ", level=1)
    findings = report.get("results") or report.get("checks") or []
    for index, finding in enumerate(findings, 1):
        kind = {"violation": "НЕСООТВЕТСТВИЕ", "compliant": "СООТВЕТСТВИЕ", "unchecked": "НЕ ПРОВЕРЕНО"}.get(finding.get("type"), "РЕЗУЛЬТАТ")
        document.add_heading(f"{index}. {kind}: {_safe_text(finding.get('title'))}", level=2)
        document.add_paragraph(f"Страница: {_safe_text(finding.get('page')) or '—'} | Лист: {_safe_text(finding.get('sheet')) or '—'}")
        document.add_paragraph(f"Критичность: {_safe_text(finding.get('severity')) or '—'}")
        document.add_paragraph(f"Норматив: {_safe_text(finding.get('norm')) or '—'} | Пункт: {_safe_text(finding.get('clause')) or '—'}")
        document.add_paragraph(f"Описание: {_safe_text(finding.get('description')) or '—'}")
        if finding.get("evidence_text"):
            document.add_paragraph(f"Фрагмент доказательства: {_safe_text(finding.get('evidence_text'))}")
        if finding.get("recommendation"):
            document.add_paragraph(f"Рекомендация: {_safe_text(finding.get('recommendation'))}")
        image_bytes = _evidence_image(finding)
        if image_bytes:
            document.add_picture(io.BytesIO(image_bytes), width=Inches(6.2))
            document.add_paragraph(f"Доказательный фрагмент с красной рамкой — замечание №{index}")

    if report.get("conclusion"):
        document.add_heading("ЗАКЛЮЧЕНИЕ", level=1)
        document.add_paragraph(_safe_text(report.get("conclusion")))

    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


@router.get("/{document_id}")
def get_report(document_id: str):
    report = _load_saved_report(document_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт для документа ещё не сформирован")
    return {"success": True, **report}


@router.post("/create/{document_id}")
def create_report(document_id: str):
    """Return the persisted first-pass report, ready for PDF/DOCX export."""
    report = _load_saved_report(document_id)
    if report is None:
        raise HTTPException(status_code=409, detail="Сначала выполните проверку документа через /api/checks/{document_id}")
    return {"success": True, "template": REPORT_TEMPLATE, **report}


@router.post("/pdf")
def export_pdf(report: dict):
    try:
        data = _build_pdf(report)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать PDF: {error}") from error
    filename = f"project-expert-ai-check-{report.get('document_id', 'report')}.pdf"
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/docx")
def export_docx(report: dict):
    try:
        data = _build_docx(report)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать Word: {error}") from error
    filename = f"project-expert-ai-check-{report.get('document_id', 'report')}.docx"
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
