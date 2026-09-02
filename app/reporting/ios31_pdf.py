"""PDF export for the persisted Project Expert AI norm-control report."""
from __future__ import annotations

import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONT_READY = False
_FONT = "Helvetica"
_BOLD = "Helvetica-Bold"


def _fonts():
    global _FONT_READY, _FONT, _BOLD
    if _FONT_READY:
        return _FONT, _BOLD
    for regular, bold in [
        (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
        (Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")),
    ]:
        if regular.exists() and bold.exists():
            try:
                pdfmetrics.registerFont(TTFont("ProjectExpertReport", str(regular)))
                pdfmetrics.registerFont(TTFont("ProjectExpertReportBold", str(bold)))
                _FONT, _BOLD = "ProjectExpertReport", "ProjectExpertReportBold"
                break
            except Exception:
                pass
    _FONT_READY = True
    return _FONT, _BOLD


def _text(value) -> str:
    return str(value or "").strip()


def _p(value) -> str:
    return escape(_text(value)).replace("\n", "<br/>")


def _findings(report: dict) -> list[dict]:
    return report.get("results") or report.get("checks") or []


def _norm_requirement(finding: dict) -> str:
    value = _text(finding.get("normative_requirement")) or _text(finding.get("normative_value_raw")) or _text(finding.get("normative_value"))
    if not value:
        value = _text(finding.get("description")) or "—"
    unit = _text(finding.get("normative_unit"))
    if unit and unit not in value:
        value = f"{value} {unit}"
    return value


def _project_value(finding: dict) -> str:
    value = _text(finding.get("project_value_raw")) or _text(finding.get("project_value")) or _text(finding.get("evidence_text")) or "—"
    unit = _text(finding.get("project_unit"))
    if unit and unit not in value:
        value = f"{value} {unit}"
    return value


def _parameter(finding: dict) -> str:
    names = {
        "wastewater_flow": "Расчётные расходы",
        "sewer_diameter": "Диаметры канализации",
        "sewer_slope": "Уклоны канализации",
        "sewer_ventilation": "Вентиляция канализации",
        "sewer_outlets": "Выпуски",
        "sewer_cleanouts": "Ревизии и прочистки",
        "sewer_material": "Материалы труб",
        "storm_separation": "Разделение систем",
        "noise_insulation": "Шумоизоляция стояков",
        "irrigation": "Поливочные устройства",
        "meters": "Приборы учёта",
        "emergency_outlets": "Аварийные решения",
        "ar_coordination": "Координация с АР",
    }
    key = _text(finding.get("parameter"))
    return names.get(key, key or _text(finding.get("title")) or "Проверка")


def _status(finding: dict) -> str:
    return {"violation": "Нарушение", "compliant": "Соответствие", "unchecked": "Требует проверки"}.get(_text(finding.get("type")), "—")


def _evidence_bytes(finding: dict, report: dict) -> bytes | None:
    candidates = [finding.get("evidence_image"), finding.get("image")]
    document_id = _text(report.get("document_id"))
    for raw in candidates:
        value = _text(raw)
        if not value:
            continue
        paths = [Path(value)]
        if document_id:
            paths.append(Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id / "checking" / "first_pass" / "annotated" / Path(value).name)
        for path in paths:
            try:
                if path.is_file():
                    return path.read_bytes()
            except OSError:
                continue
    return None


def _evidence_image(raw: bytes, max_width: float = 178 * mm, max_height: float = 112 * mm):
    reader = ImageReader(io.BytesIO(raw))
    width, height = reader.getSize()
    if not width or not height:
        return None
    scale = min(max_width / float(width), max_height / float(height), 1.0)
    return Image(io.BytesIO(raw), width=float(width) * scale, height=float(height) * scale, preserveAspectRatio=True, anchor="sw", hAlign="LEFT", vAlign="TOP")


def _sources(findings: list[dict]) -> list[str]:
    result, seen = [], set()
    for finding in findings:
        sources = finding.get("normative_sources") or []
        for source in sources:
            document = _text(source.get("document") or source.get("norm_number")) or "СП"
            version = _text(source.get("version")) or "—"
            page = _text(source.get("page")) or "—"
            key = (document, version, page)
            if key in seen:
                continue
            seen.add(key)
            result.append(f"{document} — версия {version}, стр. {page}")
    return result


def build_pdf(report: dict) -> bytes:
    regular, bold = _fonts()
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=11 * mm, rightMargin=11 * mm, topMargin=11 * mm, bottomMargin=11 * mm)
    base = getSampleStyleSheet()
    title = ParagraphStyle("PETitle", parent=base["Title"], fontName=bold, fontSize=18, leading=21, alignment=1)
    h1 = ParagraphStyle("PEH1", parent=base["Heading1"], fontName=bold, fontSize=14, leading=17, spaceBefore=7, spaceAfter=6)
    h2 = ParagraphStyle("PEH2", parent=base["Heading2"], fontName=bold, fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle("PEBody", parent=base["BodyText"], fontName=regular, fontSize=8.5, leading=11)
    small = ParagraphStyle("PESmall", parent=body, fontSize=7.5, leading=9)
    cell = ParagraphStyle("PECell", parent=body, fontSize=6.8, leading=8.2)
    cellb = ParagraphStyle("PECellB", parent=cell, fontName=bold)

    findings = _findings(report)
    summary = report.get("summary") or {}
    story = [
        Paragraph("PROJECT EXPERT AI", title),
        Spacer(1, 3 * mm),
        Paragraph("ОТЧЁТ ПО НОРМОКОНТРОЛЮ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", h1),
        Paragraph(f"<b>Документ:</b> {_p(report.get('document_name'))}", body),
        Paragraph(f"<b>Профиль экспертизы:</b> {_p(report.get('skill_name') or report.get('skill_id') or '—')}", body),
        Paragraph(f"<b>Дата проверки:</b> {_p(report.get('checked_at'))}", body),
        Paragraph(f"<b>Нормативная база:</b> {_p(report.get('normative_document'))}", body),
        Paragraph(f"<b>Действующие версии:</b> {_p(report.get('normative_version'))}", body),
        Spacer(1, 5 * mm),
        Paragraph("1. Область и нормативная база", h1),
        Paragraph(f"Проверено страниц: {summary.get('pages', 0)}. Результатов: {summary.get('total', 0)}. Подтверждённых замечаний: {summary.get('violations', 0)}. Соответствий: {summary.get('compliant', 0)}. Требуют проверки: {summary.get('unchecked', 0)}.", body),
    ]
    overview = Table([
        ["Страниц", "Результатов", "Замечаний", "Соответствий", "Требуют проверки"],
        [summary.get("pages", 0), summary.get("total", 0), summary.get("violations", 0), summary.get("compliant", 0), summary.get("unchecked", 0)],
    ], colWidths=[32 * mm, 34 * mm, 34 * mm, 34 * mm, 40 * mm], repeatRows=1)
    overview.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .35, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("FONTNAME", (0, 0), (-1, 0), bold), ("FONTNAME", (0, 1), (-1, -1), regular), ("FONTSIZE", (0, 0), (-1, -1), 7), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [Spacer(1, 4 * mm), overview, Spacer(1, 7 * mm), Paragraph("2. Заключение", h1), Paragraph(_p(report.get("conclusion")) or "Неподтверждённые результаты не считаются установленными нарушениями и требуют экспертной верификации.", body), Spacer(1, 7 * mm), Paragraph("3. Результаты проверки", h1)]

    table_data = [[Paragraph("№", cellb), Paragraph("Лист", cellb), Paragraph("Параметр", cellb), Paragraph("Значение в исходнике", cellb), Paragraph("Нормативное требование", cellb), Paragraph("СП / пункт", cellb), Paragraph("Результат", cellb), Paragraph("Рекомендация", cellb)]]
    for index, finding in enumerate(findings, 1):
        norm = _text(finding.get("norm")) or "—"
        clause = _text(finding.get("clause"))
        norm_clause = f"{norm} / п. {clause}" if clause else norm
        table_data.append([
            Paragraph(str(index), cell),
            Paragraph(_p(finding.get("sheet") or finding.get("page") or "—"), cell),
            Paragraph(_p(_parameter(finding)), cell),
            Paragraph(_p(_project_value(finding)), cell),
            Paragraph(_p(_norm_requirement(finding)), cell),
            Paragraph(_p(norm_clause), cell),
            Paragraph(_p(_status(finding)), cell),
            Paragraph(_p(finding.get("recommendation") or "—"), cell),
        ])
    results_table = Table(table_data, colWidths=[7 * mm, 13 * mm, 27 * mm, 45 * mm, 45 * mm, 25 * mm, 23 * mm, 34 * mm], repeatRows=1)
    results_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .35, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("FONTNAME", (0, 0), (-1, 0), bold), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 1), (0, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(results_table)

    story += [Spacer(1, 8 * mm), Paragraph("4. Доказательства по результатам", h1)]
    if not findings:
        story.append(Paragraph("Доказательств нет: результатов проверки не сохранено.", body))
    for index, finding in enumerate(findings, 1):
        story.append(Paragraph(f"4.{index}. Результат №{index} — {_p(_parameter(finding))}", h2))
        norm = _text(finding.get("norm")) or "—"
        clause = _text(finding.get("clause"))
        norm_clause = f"{norm} / п. {clause}" if clause else norm
        page = _p(finding.get("page") or "—")
        story.append(Paragraph(f"<b>Страница:</b> {page} &nbsp;&nbsp; <b>Статус:</b> {_p(_status(finding))} &nbsp;&nbsp; <b>СП / пункт:</b> {_p(norm_clause)}", small))
        story.append(Paragraph(f"<b>Значение в исходнике:</b> {_p(_project_value(finding))}", body))
        story.append(Paragraph(f"<b>Нормативное требование:</b> {_p(_norm_requirement(finding))}", body))
        if _text(finding.get("comparison")):
            story.append(Paragraph(f"<b>Сравнение:</b> {_p(finding.get('comparison'))}", body))
        if _text(finding.get("recommendation")):
            story.append(Paragraph(f"<b>Рекомендация:</b> {_p(finding.get('recommendation'))}", body))
        raw = _evidence_bytes(finding, report)
        if raw:
            image = _evidence_image(raw)
            if image:
                story += [Spacer(1, 2 * mm), image, Paragraph(f"Изображение №{index} — страница исходной документации с отмеченной областью результата №{index}.", small)]
        else:
            story.append(Paragraph("Изображение не сохранено для этого результата.", small))
        story.append(Spacer(1, 5 * mm))

    story += [Spacer(1, 4 * mm), Paragraph("5. Нормативные источники", h1)]
    sources = _sources(findings)
    if sources:
        for source in sources:
            story.append(Paragraph(f"• {_p(source)}", body))
    else:
        story.append(Paragraph("Нормативные источники для подтверждённых результатов отсутствуют.", body))

    doc.build(story)
    return out.getvalue()
