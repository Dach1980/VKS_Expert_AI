"""Project Expert AI — report generation API.

Generates downloadable PDF/DOCX reports from an actual CheckReport payload.
Evidence images are included when a finding contains a valid PDF page/bbox.
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
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib import colors

from app.api.documents import DOCUMENTS_ROOT

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _safe_text(value) -> str:
    return str(value or "").strip()


def _document_pdf(document_id: str) -> Path | None:
    root = DOCUMENTS_ROOT / document_id
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    return candidates[0] if candidates else None


def _evidence_image(finding: dict) -> bytes | None:
    """Render a project PDF page and mark a supplied bbox in red.

    We never invent coordinates. If bbox is absent, no evidence image is created.
    """
    document_id = _safe_text(finding.get("docId"))
    page_number = int(finding.get("page") or 0)
    bbox = finding.get("bbox")
    if not document_id or page_number <= 0 or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None

    pdf_path = _document_pdf(document_id)
    if not pdf_path:
        return None

    try:
        rect = [float(x) for x in bbox]
        pdf = fitz.open(pdf_path)
        if page_number > len(pdf):
            pdf.close()
            return None
        page = pdf[page_number - 1]
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


def _summary(report: dict) -> dict:
    return report.get("summary") or {}


def _build_pdf(report: dict) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Finding", parent=styles["Heading2"], fontSize=12, leading=15, spaceBefore=8, spaceAfter=5))

    story = []
    story.append(Paragraph("PROJECT EXPERT AI", styles["Title"]))
    story.append(Paragraph("ОТЧЁТ ПО ПРОВЕРКЕ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", styles["Heading1"]))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(f"<b>Документ:</b> {_safe_text(report.get('document_name'))}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Дата проверки:</b> {_safe_text(report.get('checked_at')) or datetime.now().strftime('%d.%m.%Y %H:%M')}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Нормативная база:</b> {_safe_text(report.get('normative_document'))}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Версия:</b> {_safe_text(report.get('normative_version'))}", styles["BodyText"]))
    story.append(Spacer(1, 6 * mm))

    s = _summary(report)
    table = Table([
        ["Всего", "Соответствует", "Нарушения", "Не проверено", "Критические"],
        [s.get("total", 0), s.get("compliant", 0), s.get("violations", 0), s.get("unchecked", 0), s.get("critical", 0)],
    ], colWidths=[32 * mm] * 5)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("РЕЗУЛЬТАТЫ ПРОВЕРКИ", styles["Heading1"]))
    findings = report.get("results") or report.get("checks") or []
    if not findings:
        story.append(Paragraph("Результаты проверки отсутствуют.", styles["BodyText"]))

    for index, finding in enumerate(findings, 1):
        kind = {"violation": "НЕСООТВЕТСТВИЕ", "compliant": "СООТВЕТСТВИЕ", "unchecked": "НЕ ПРОВЕРЕНО"}.get(finding.get("type"), "РЕЗУЛЬТАТ")
        title = _safe_text(finding.get("title")) or "Результат проверки"
        story.append(KeepTogether([
            Paragraph(f"{index}. {kind}: {title}", styles["Finding"]),
            Paragraph(f"<b>Критичность:</b> {_safe_text(finding.get('severity')) or '—'}", styles["Small"]),
            Paragraph(f"<b>Страница:</b> {_safe_text(finding.get('page')) or '—'} &nbsp;&nbsp; <b>Лист:</b> {_safe_text(finding.get('sheet')) or '—'}", styles["Small"]),
            Paragraph(f"<b>Норматив:</b> {_safe_text(finding.get('norm')) or '—'}", styles["Small"]),
            Spacer(1, 2 * mm),
            Paragraph(f"<b>Описание:</b> {_safe_text(finding.get('description')) or '—'}", styles["BodyText"]),
        ]))
        if finding.get("recommendation"):
            story.append(Paragraph(f"<b>Рекомендация:</b> {_safe_text(finding.get('recommendation'))}", styles["BodyText"]))
        image_bytes = _evidence_image(finding)
        if image_bytes:
            image = Image(io.BytesIO(image_bytes), width=165 * mm, height=105 * mm)
            story.append(Spacer(1, 3 * mm))
            story.append(image)
            story.append(Paragraph(f"Доказательный фрагмент — замечание №{index}", styles["Small"]))
        elif finding.get("bbox"):
            story.append(Paragraph("Доказательный фрагмент не сформирован: координаты не удалось обработать.", styles["Small"]))
        story.append(Spacer(1, 5 * mm))

    if report.get("conclusion"):
        story.append(Paragraph("ЗАКЛЮЧЕНИЕ", styles["Heading1"]))
        story.append(Paragraph(_safe_text(report.get("conclusion")), styles["BodyText"]))

    doc.build(story)
    return output.getvalue()


def _build_docx(report: dict) -> bytes:
    document = Document()
    document.add_heading("PROJECT EXPERT AI", level=0)
    document.add_heading("ОТЧЁТ ПО ПРОВЕРКЕ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", level=1)
    document.add_paragraph(f"Документ: {_safe_text(report.get('document_name'))}")
    document.add_paragraph(f"Дата проверки: {_safe_text(report.get('checked_at')) or datetime.now().strftime('%d.%m.%Y %H:%M')}")
    document.add_paragraph(f"Нормативная база: {_safe_text(report.get('normative_document'))}")
    document.add_paragraph(f"Версия: {_safe_text(report.get('normative_version'))}")

    s = _summary(report)
    table = document.add_table(rows=2, cols=5)
    headers = ["Всего", "Соответствует", "Нарушения", "Не проверено", "Критические"]
    values = [s.get("total", 0), s.get("compliant", 0), s.get("violations", 0), s.get("unchecked", 0), s.get("critical", 0)]
    for i, value in enumerate(headers):
        table.cell(0, i).text = value
        table.cell(1, i).text = str(values[i])

    document.add_heading("РЕЗУЛЬТАТЫ ПРОВЕРКИ", level=1)
    findings = report.get("results") or report.get("checks") or []
    for index, finding in enumerate(findings, 1):
        kind = {"violation": "НЕСООТВЕТСТВИЕ", "compliant": "СООТВЕТСТВИЕ", "unchecked": "НЕ ПРОВЕРЕНО"}.get(finding.get("type"), "РЕЗУЛЬТАТ")
        document.add_heading(f"{index}. {kind}: {_safe_text(finding.get('title'))}", level=2)
        document.add_paragraph(f"Критичность: {_safe_text(finding.get('severity')) or '—'}")
        document.add_paragraph(f"Страница: {_safe_text(finding.get('page')) or '—'} | Лист: {_safe_text(finding.get('sheet')) or '—'}")
        document.add_paragraph(f"Норматив: {_safe_text(finding.get('norm')) or '—'}")
        document.add_paragraph(f"Описание: {_safe_text(finding.get('description')) or '—'}")
        if finding.get("recommendation"):
            document.add_paragraph(f"Рекомендация: {_safe_text(finding.get('recommendation'))}")
        image_bytes = _evidence_image(finding)
        if image_bytes:
            document.add_picture(io.BytesIO(image_bytes), width=Inches(6.2))
            document.add_paragraph(f"Доказательный фрагмент — замечание №{index}")

    if report.get("conclusion"):
        document.add_heading("ЗАКЛЮЧЕНИЕ", level=1)
        document.add_paragraph(_safe_text(report.get("conclusion")))

    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


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
