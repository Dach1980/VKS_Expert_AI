"""First-pass page-by-page document checking pipeline.

The pipeline deliberately separates visual evidence from normative reasoning:
PDF -> rendered page -> VL model -> candidate bbox -> RAG -> compliance decision
-> annotated evidence image -> report-ready finding.

This module is deterministic and conservative: it never invents a bbox and it
keeps page-level evidence attached to every finding.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


RED = (1, 0, 0)
DEFAULT_DPI = 144


@dataclass
class PageEvidence:
    page: int
    image_path: str
    width: int
    height: int


@dataclass
class Finding:
    type: str
    title: str
    description: str
    recommendation: str
    norm: str
    severity: str
    page: int
    bbox: Optional[list[float]]
    evidence_image: Optional[str]
    clause: str = ""
    evidence_text: str = ""
    confidence: Optional[float] = None

    def to_report_dict(self) -> dict[str, Any]:
        return asdict(self)


def render_pdf_pages(pdf_path: str | Path, output_dir: str | Path, dpi: int = DEFAULT_DPI) -> list[PageEvidence]:
    """Render every PDF page to PNG and return stable page metadata."""
    if fitz is None:
        raise RuntimeError("PyMuPDF is required for page rendering")
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    pages: list[PageEvidence] = []
    try:
        for index, page in enumerate(doc, start=1):
            image_path = output_dir / f"page_{index:04d}.png"
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(image_path))
            pages.append(PageEvidence(index, str(image_path), pix.width, pix.height))
    finally:
        doc.close()
    return pages


def _extract_json(text: str) -> dict[str, Any]:
    """Extract one JSON object from conservative VL output."""
    text = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def normalize_bbox(value: Any, width: int, height: int) -> Optional[list[float]]:
    """Accept pixel or normalized [x1,y1,x2,y2], reject unsafe boxes."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        box = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    if all(0 <= v <= 1 for v in box) and width > 1 and height > 1:
        box = [box[0] * width, box[1] * height, box[2] * width, box[3] * height]
    x1, y1, x2, y2 = box
    x1, x2 = max(0, min(x1, width)), max(0, min(x2, width))
    y1, y2 = max(0, min(y1, height)), max(0, min(y2, height))
    if x2 <= x1 or y2 <= y1:
        return None
    return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]


def annotate_evidence(image_path: str | Path, bbox: Optional[list[float]], output_path: str | Path) -> Optional[str]:
    """Draw a red rectangle around verified evidence without modifying source PDF."""
    if not bbox:
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required for evidence annotation") from exc
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = bbox
    for offset in range(4):
        draw.rectangle((x1 - offset, y1 - offset, x2 + offset, y2 + offset), outline=(255, 0, 0))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")
    return str(output_path)


def _vl_prompt(page_number: int) -> str:
    return f"""Ты выполняешь первый визуальный проход нормоконтроля страницы PDF №{page_number}.
Найди только потенциально проверяемые несоответствия проектной документации.
Не определяй нормативное соответствие без нормативного контекста.
Если координаты нельзя определить уверенно, bbox = null.
Верни только JSON:
{{"findings":[{{"title":"","description":"","evidence_text":"","bbox":[x1,y1,x2,y2],"confidence":0.0}}]}}
"""


def inspect_page_with_vl(page: PageEvidence, vl_chat: Callable[[str, str], str]) -> list[dict[str, Any]]:
    """Run the VL model on one rendered page. Image transport is delegated to the client."""
    raw = vl_chat(_vl_prompt(page.page), page.image_path)
    payload = _extract_json(raw)
    findings = payload.get("findings", [])
    return findings if isinstance(findings, list) else []


def build_report(pages: Iterable[PageEvidence], findings: Iterable[Finding], document_name: str, normative_number: str) -> dict[str, Any]:
    findings = list(findings)
    violations = [f for f in findings if f.type == "violation"]
    compliant = [f for f in findings if f.type == "compliant"]
    unchecked = [f for f in findings if f.type == "unchecked"]
    return {
        "template": "reference_normcontrol_report_ios_3.1",
        "document": document_name,
        "normative_basis": [normative_number],
        "summary": {
            "pages": len(list(pages)),
            "total": len(findings),
            "violations": len(violations),
            "critical": sum(f.severity == "critical" for f in violations),
            "major": sum(f.severity == "major" for f in violations),
            "minor": sum(f.severity == "minor" for f in violations),
            "compliant": len(compliant),
            "unchecked": len(unchecked),
        },
        "findings": [f.to_report_dict() for f in findings],
    }


def run_first_pass(
    pdf_path: str | Path,
    evidence_dir: str | Path,
    document_name: str,
    normative_number: str,
    vl_chat: Callable[[str, str], str],
    rag_lookup: Callable[[str], list[dict[str, Any]]],
    compliance_check: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]],
) -> dict[str, Any]:
    """Execute the complete first-pass pipeline with injectable VL/RAG/LLM adapters."""
    pages = render_pdf_pages(pdf_path, evidence_dir)
    all_findings: list[Finding] = []
    evidence_root = Path(evidence_dir) / "annotated"
    for page in pages:
        candidates = inspect_page_with_vl(page, vl_chat)
        for candidate in candidates:
            bbox = normalize_bbox(candidate.get("bbox"), page.width, page.height)
            query = " ".join(str(candidate.get(k, "")) for k in ("title", "description", "evidence_text"))
            normative_context = rag_lookup(query)
            decision = compliance_check(candidate, normative_context)
            finding_type = str(decision.get("type", "unchecked"))
            if finding_type not in {"violation", "compliant", "unchecked"}:
                finding_type = "unchecked"
            evidence_image = None
            if bbox:
                evidence_image = annotate_evidence(page.image_path, bbox, evidence_root / f"page_{page.page:04d}_finding_{len(all_findings)+1:03d}.png")
            all_findings.append(Finding(
                type=finding_type,
                title=str(decision.get("title") or candidate.get("title") or "Потенциальное несоответствие"),
                description=str(decision.get("description") or candidate.get("description") or ""),
                recommendation=str(decision.get("recommendation") or ""),
                norm=str(decision.get("norm") or normative_number),
                severity=str(decision.get("severity") or "minor"),
                page=page.page,
                bbox=bbox,
                evidence_image=evidence_image,
                clause=str(decision.get("clause") or ""),
                evidence_text=str(candidate.get("evidence_text") or ""),
                confidence=decision.get("confidence", candidate.get("confidence")),
            ))
    report = build_report(pages, all_findings, document_name, normative_number)
    report_path = Path(evidence_dir) / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_json"] = str(report_path)
    return report
