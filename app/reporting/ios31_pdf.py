"""Enhanced PDF renderer following the IOS 3.1 findings-table layout."""
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

_FONT_READY=False
_FONT="Helvetica"
_BOLD="Helvetica-Bold"

def _fonts():
    global _FONT_READY,_FONT,_BOLD
    if _FONT_READY:return _FONT,_BOLD
    for regular,bold in [(Path(r"C:\Windows\Fonts\arial.ttf"),Path(r"C:\Windows\Fonts\arialbd.ttf")),(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))]:
        if regular.exists() and bold.exists():
            try:
                pdfmetrics.registerFont(TTFont("ProjectExpertUnicode2",str(regular))); pdfmetrics.registerFont(TTFont("ProjectExpertUnicodeBold2",str(bold))); _FONT="ProjectExpertUnicode2"; _BOLD="ProjectExpertUnicodeBold2"; break
            except Exception: pass
    _FONT_READY=True
    return _FONT,_BOLD

def _t(v):return str(v or "").strip()
def _p(v):return escape(_t(v)).replace("\n","<br/>")
def _findings(report):return report.get("results") or report.get("checks") or []
def _violations(report):return [x for x in _findings(report) if x.get("type")=="violation"]
def _image(path):
    p=Path(_t(path));
    if not p.is_file():return None
    try:return p.read_bytes()
    except OSError:return None

def build_pdf(report:dict)->bytes:
    regular,bold=_fonts(); out=io.BytesIO(); doc=SimpleDocTemplate(out,pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm)
    base=getSampleStyleSheet(); body=ParagraphStyle("PEBody",parent=base["BodyText"],fontName=regular,fontSize=8.5,leading=11); small=ParagraphStyle("PESmall",parent=body,fontSize=7.5,leading=9); h1=ParagraphStyle("PEH1",parent=base["Heading1"],fontName=bold,fontSize=14,leading=17,spaceBefore=7,spaceAfter=6); title=ParagraphStyle("PETitle",parent=base["Title"],fontName=bold,fontSize=18,leading=21,alignment=1); cell=ParagraphStyle("PECell",parent=body,fontSize=7,leading=8.5); cellb=ParagraphStyle("PECellB",parent=cell,fontName=bold)
    findings=_findings(report); violations=_violations(report); summary=report.get("summary") or {}; story=[Paragraph("PROJECT EXPERT AI",title),Spacer(1,3*mm),Paragraph("ОТЧЁТ ПО НОРМОКОНТРОЛЮ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ",h1),Paragraph(f"<b>Документ:</b> {_p(report.get('document_name'))}",body),Paragraph(f"<b>Дата проверки:</b> {_p(report.get('checked_at'))}",body),Paragraph(f"<b>Нормативная база:</b> {_p(report.get('normative_document'))}",body),Paragraph(f"<b>Действующие версии:</b> {_p(report.get('normative_version'))}",body),Spacer(1,5*mm),Paragraph("1. Общая оценка",h1),Paragraph(f"Проверено страниц: {summary.get('pages',0)}. Всего результатов: {summary.get('total',0)}. Подтверждённых замечаний: {summary.get('violations',0)}. Соответствий: {summary.get('compliant',0)}. Требуют проверки: {summary.get('unchecked',0)}.",body),Spacer(1,5*mm)]
    overview=Table([["Страниц","Результатов","Замечаний","Критических","Значительных","Не подтверждено"],[summary.get("pages",0),summary.get("total",0),summary.get("violations",0),summary.get("critical",0),summary.get("major",0),summary.get("unchecked",0)]],colWidths=[28*mm]*6,repeatRows=1); overview.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.35,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("FONTNAME",(0,0),(-1,0),bold),("FONTNAME",(0,1),(-1,-1),regular),("FONTSIZE",(0,0),(-1,-1),7),("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story += [overview,Spacer(1,7*mm),Paragraph("2. Сводный реестр результатов",h1)]
    register=[[Paragraph("№",cellb),Paragraph("Замечание",cellb),Paragraph("Статус",cellb),Paragraph("Класс",cellb),Paragraph("Страница",cellb),Paragraph("Норматив",cellb)]]
    status={"violation":"Замечание","compliant":"Соответствует","unchecked":"Не подтверждено"}
    for i,f in enumerate(findings,1): register.append([str(i),Paragraph(_p(f.get("title")),cell),Paragraph(status.get(f.get("type"),"—"),cell),Paragraph(_p(f.get("severity")),cell),Paragraph(_p(f.get("page")),cell),Paragraph(_p((f.get("norm") or "—")+(("; "+_t(f.get("clause"))) if f.get("clause") else "")),cell)])
    t=Table(register,colWidths=[7*mm,61*mm,25*mm,19*mm,16*mm,49*mm],repeatRows=1); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.35,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("FONTNAME",(0,0),(-1,0),bold),("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(0,1),(0,-1),"CENTER")]))
    story += [t,Spacer(1,7*mm),Paragraph("3. Результаты проверки: выявленные замечания",h1)]
    if violations:
        data=[[Paragraph("№",cellb),Paragraph("Страница / лист",cellb),Paragraph("Выявленное несоответствие",cellb),Paragraph("Нормативное основание",cellb),Paragraph("Рекомендация",cellb)]]
        for i,f in enumerate(violations,1):
            location=_p(f.get("page")); sheet=_t(f.get("sheet")); location += ("<br/>"+_p(sheet)) if sheet else ""
            norm=_p(f.get("norm") or "—"); clause=_t(f.get("clause")); norm += ("<br/><b>Пункт:</b> "+_p(clause)) if clause else ""
            desc=_p(f.get("description") or f.get("evidence_text") or f.get("title")); rec=_p(f.get("recommendation") or "Требуется устранение и повторная проверка")
            data.append([str(i),Paragraph(location,cell),Paragraph(desc,cell),Paragraph(norm,cell),Paragraph(rec,cell)])
        vt=Table(data,colWidths=[7*mm,25*mm,59*mm,47*mm,39*mm],repeatRows=1); vt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("FONTNAME",(0,0),(-1,0),bold),("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(0,1),(0,-1),"CENTER"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); story.append(vt)
    else: story.append(Paragraph("Подтверждённых замечаний не выявлено.",body))
    story += [Spacer(1,7*mm),Paragraph("4. Доказательства и подробные результаты",h1)]
    for i,f in enumerate(findings,1):
        story += [Paragraph(f"4.{i}. {_p(f.get('title') or 'Результат проверки')}",h1),Paragraph(f"<b>Страница:</b> {_p(f.get('page'))} &nbsp; <b>Лист:</b> {_p(f.get('sheet')) or '—'} &nbsp; <b>Норматив:</b> {_p(f.get('norm')) or '—'} &nbsp; <b>Пункт:</b> {_p(f.get('clause')) or '—'}",small),Paragraph(f"<b>Описание:</b> {_p(f.get('description')) or '—'}",body)]
        if f.get("evidence_text"): story.append(Paragraph(f"<b>Видимый факт:</b> {_p(f.get('evidence_text'))}",body))
        if f.get("recommendation"): story.append(Paragraph(f"<b>Рекомендация:</b> {_p(f.get('recommendation'))}",body))
        raw=_image(f.get("evidence_image"))
        if raw:
            try:
                reader=ImageReader(io.BytesIO(raw)); iw,ih=reader.getSize(); maxw=175*mm; maxh=105*mm; scale=min(maxw/iw,maxh/ih); story += [Spacer(1,2*mm),Image(io.BytesIO(raw),width=iw*scale,height=ih*scale),Paragraph("Фрагмент исходной страницы с отмеченной областью.",small)]
            except Exception: pass
        story.append(Spacer(1,5*mm))
    story += [PageBreak(),Paragraph("5. Заключение",h1),Paragraph(_p(report.get("conclusion")) or "Подтверждённые несоответствия рекомендуется устранить до выпуска документации. Результаты ИИ являются инструментом предварительного нормоконтроля и подлежат экспертной верификации.",body),Paragraph("6. Нормативные источники",h1)]
    seen=set(); sources=[]
    for f in findings:
        for s in f.get("normative_sources") or []:
            key=(_t(s.get("document")),_t(s.get("version")),_t(s.get("page"))); 
            if key not in seen: seen.add(key); sources.append(f"{key[0] or 'СП'} — версия {key[1] or '—'}, стр. {key[2] or '—'}")
    for i,s in enumerate(sources,1): story.append(Paragraph(f"{i}. {_p(s)}",body))
    doc.build(story); return out.getvalue()
