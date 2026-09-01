"""Executable first-pass visual/normative document checking service."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests

from app.checking.page_pipeline import annotate_evidence, normalize_bbox, render_pdf_pages
from app.knowledge.storage import KnowledgeStorage
from app.rag.retriever import Retriever
from app.llm.lmstudio_client import LMStudioClient

DEFAULT_NORM_NUMBER = "СП 30.13330.2020"
CHECK_DPI = 144
MAX_NORM_RESULTS = 5
MAX_NORM_CHARS = 6000
MAX_DECISION_CHARS = 12000
REPORT_API_BASE = "http://127.0.0.1:8000"

ProgressCallback = Callable[[dict[str, Any]], None]


def _json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(raw[start:end + 1])
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass
    return {}


def _json_array(text: str) -> list[dict[str, Any]]:
    raw = str(text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict) and isinstance(value.get("findings"), list):
            return [x for x in value["findings"] if isinstance(x, dict)]
    except json.JSONDecodeError:
        start, end = raw.find("["), raw.rfind("]")
        if start >= 0 and end > start:
            try:
                value = json.loads(raw[start:end + 1])
                return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []
            except json.JSONDecodeError:
                pass
    return []


def _image_data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _vision_request(client: LMStudioClient, prompt: str, image_path: Path, max_tokens: int = 1200) -> str:
    if client.model is None:
        client.model = client._select_chat_model(client.get_models())
    payload = {
        "model": client.model,
        "messages": [
            {"role": "system", "content": "Ты выполняешь визуальный анализ проектной документации. Не выдумывай факты и координаты."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _image_data_url(image_path)}},
            ]},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
    response = requests.post(f"{client.base_url}/chat/completions", json=payload, timeout=client.timeout)
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"].get("content") or "").strip()


def _context_text(results: list[dict[str, Any]], normative_number: str) -> str:
    parts = []
    for item in results:
        content = item.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        if text:
            parts.append(f"{normative_number}, стр. {item.get('page', '—')}: {text}")
    value = "\n\n".join(parts)
    return value[:MAX_NORM_CHARS] + ("\n[нормативный контекст сокращён]" if len(value) > MAX_NORM_CHARS else "")


def _decision(client: LMStudioClient, candidate: dict[str, Any], norm_text: str) -> dict[str, Any]:
    prompt = f"""Проведи нормативную проверку одного потенциального несоответствия.

ПРОЕКТНОЕ НАБЛЮДЕНИЕ:
{json.dumps(candidate, ensure_ascii=False)}

НОРМАТИВНЫЙ КОНТЕКСТ:
{norm_text[:MAX_DECISION_CHARS]}

Верни только JSON-объект:
{{"type":"violation|compliant|unchecked","title":"","description":"","recommendation":"","sheet":"","norm":"","clause":"","severity":"critical|major|minor","confidence":0.0}}

Не придумывай пункт нормы. Если нормативного доказательства недостаточно, type=unchecked.
"""
    return _json_object(client.chat(prompt, temperature=0.1, max_tokens=900, enable_thinking=False))


def resolve_current_norm(storage: KnowledgeStorage, canonical_number: str = DEFAULT_NORM_NUMBER):
    target = storage.registry.canonical_number(canonical_number).lower()
    group = storage.registry._number_group(canonical_number)
    candidates = []
    for document in storage.registry.get_all_documents():
        number = storage.registry.canonical_number(document.get("number", "")).lower()
        if number == target or (group and storage.registry._number_group(document.get("number", "")) == group):
            candidates.append(document)
    if not candidates:
        raise RuntimeError(f"В Registry не найден {canonical_number}")
    candidates.sort(key=lambda x: len(x.get("versions", [])), reverse=True)
    document = candidates[0]
    version = storage.get_current_version(document["id"])
    return document, version


def run_first_pass_api(
    document_id: str,
    normative_number: str = DEFAULT_NORM_NUMBER,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run page -> VL -> RAG -> compliance -> evidence -> report JSON."""
    def progress(**data: Any) -> None:
        if progress_callback:
            progress_callback(data)

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    pdf_path = root / "source.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Исходный PDF не найден")
    evidence_dir = root / "checking" / "first_pass"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    progress(stage="preparing", percent=1, current_page=0, total_pages=0, message="Подготовка проверки…")

    storage = KnowledgeStorage()
    norm_document, norm_version = resolve_current_norm(storage, normative_number)
    norm_id, version_id = str(norm_document["id"]), str(norm_version["id"])
    retriever = Retriever(norm_id, version_id, storage)
    client = LMStudioClient(model=None)
    pages = render_pdf_pages(pdf_path, evidence_dir, dpi=CHECK_DPI)
    total_pages = len(pages)
    findings = []
    progress(stage="visual", percent=2, current_page=0, total_pages=total_pages, message=f"Страницы подготовлены: {total_pages}. Начинаю визуальный анализ…")

    for page_index, page in enumerate(pages, start=1):
        page_start = 2 + int((page_index - 1) / max(total_pages, 1) * 96)
        progress(stage="visual", percent=page_start, current_page=page_index, total_pages=total_pages, message=f"Визуальный анализ страницы {page_index} из {total_pages}…")
        visual_prompt = f"""Страница PDF №{page.page}. Найди видимые элементы, которые требуют инженерной проверки по нормативам: размеры, схемные решения, обозначения, таблицы, подписи, параметры. Не утверждай нарушение без нормы. Для каждого кандидата укажи bbox в пикселях [x1,y1,x2,y2]. Если координаты ненадёжны — null. Верни только JSON-массив объектов с полями title, description, evidence_text, bbox, confidence."""
        candidates = _json_array(_vision_request(client, visual_prompt, Path(page.image_path), 1000))
        for candidate_index, candidate in enumerate(candidates, start=1):
            progress(stage="normative", percent=min(98, page_start + 1), current_page=page_index, total_pages=total_pages, message=f"Проверяю нормативное основание: страница {page_index}…")
            bbox = normalize_bbox(candidate.get("bbox"), page.width, page.height)
            query = " ".join(str(candidate.get(k, "")) for k in ("title", "description", "evidence_text"))
            norm_results = retriever.search(query, top_k=MAX_NORM_RESULTS) if query else []
            norm_text = _context_text(norm_results, normative_number)
            if not norm_text:
                decision = {"type": "unchecked", "title": candidate.get("title", "Потенциальное несоответствие"), "description": candidate.get("description", ""), "recommendation": "Требуется дополнительная проверка нормативной базы.", "severity": "minor", "confidence": 0.0}
            else:
                decision = _decision(client, candidate, norm_text)
            finding_id = len(findings) + 1
            evidence_image = None
            image_url = None
            if bbox:
                evidence_path = evidence_dir / "annotated" / f"page_{page.page:04d}_finding_{finding_id:03d}.png"
                evidence_image = annotate_evidence(page.image_path, bbox, evidence_path)
                image_url = f"{REPORT_API_BASE}/api/reports/evidence/{document_id}/{evidence_path.name}"
            findings.append({
                "id": finding_id, "type": decision.get("type", "unchecked"), "docId": document_id,
                "docName": pdf_path.name, "title": str(decision.get("title") or candidate.get("title") or "Результат проверки"),
                "description": str(decision.get("description") or candidate.get("description") or ""),
                "recommendation": str(decision.get("recommendation") or ""), "sheet": str(decision.get("sheet") or ""),
                "norm": str(decision.get("norm") or normative_number), "clause": str(decision.get("clause") or ""),
                "severity": str(decision.get("severity") or "minor"), "page": page.page, "bbox": bbox,
                "evidence_image": evidence_image, "image": image_url, "evidence_text": str(candidate.get("evidence_text") or ""),
                "confidence": decision.get("confidence", candidate.get("confidence")), "normative_sources": norm_results,
            })
        completed_percent = 2 + int(page_index / max(total_pages, 1) * 96)
        progress(stage="visual", percent=min(98, completed_percent), current_page=page_index, total_pages=total_pages, message=f"Страница {page_index} из {total_pages} завершена.")

    violations = [x for x in findings if x["type"] == "violation"]
    report = {
        "template": "reference_normcontrol_report_ios_3.1", "document_id": document_id, "document_name": pdf_path.name,
        "checked_at": datetime.now().isoformat(timespec="seconds"), "normative_document": normative_number,
        "normative_version": version_id, "normative_registry_id": norm_id, "results": findings,
        "summary": {"pages": len(pages), "total": len(findings), "violations": len(violations),
                    "critical": sum(x["severity"] == "critical" for x in violations),
                    "major": sum(x["severity"] == "major" for x in violations), "minor": sum(x["severity"] == "minor" for x in violations),
                    "compliant": sum(x["type"] == "compliant" for x in findings), "unchecked": sum(x["type"] == "unchecked" for x in findings)},
    }
    report_path = evidence_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    progress(stage="completed", percent=100, current_page=total_pages, total_pages=total_pages, message="Проверка завершена. Формирую отчёт…")
    report["report_json"] = str(report_path)
    return report
