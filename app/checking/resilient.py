"""Resilient page-level wrapper for the first-pass document checker.

The checker is deliberately resumable: every successfully completed page is
checkpointed to disk, so a transient LM Studio/VL failure does not force the
whole PDF to be analysed again.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.checking.first_pass import (
    CHECK_DPI,
    DEFAULT_NORM_NUMBER,
    MAX_NORM_RESULTS,
    REPORT_API_BASE,
    _context_text,
    _decision,
    _json_array,
    _strict_candidates,
    _vision_request,
    resolve_current_norm,
)
from app.checking.page_pipeline import annotate_evidence, normalize_bbox, render_pdf_pages
from app.knowledge.storage import KnowledgeStorage
from app.llm.lmstudio_client import LMStudioClient
from app.rag.retriever import Retriever

ProgressCallback = Callable[[dict[str, Any]], None]
MAX_PAGE_RETRIES = 3
RETRY_DELAY_SECONDS = 3.0


def _checkpoint_path(directory: Path) -> Path:
    return directory / "checkpoint.json"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_checkpoint(path: Path, document_id: str, pdf_name: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "running",
            "document_id": document_id,
            "document_name": pdf_name,
            "pages_completed": 0,
            "completed_pages": [],
            "findings": [],
            "last_error": None,
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("document_id") != document_id:
            raise ValueError("invalid checkpoint")
        value.setdefault("completed_pages", [])
        value.setdefault("findings", [])
        value.setdefault("pages_completed", len(value["completed_pages"]))
        return value
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "status": "running",
            "document_id": document_id,
            "document_name": pdf_name,
            "pages_completed": 0,
            "completed_pages": [],
            "findings": [],
            "last_error": None,
        }


def _build_report(
    document_id: str,
    pdf_name: str,
    normative_number: str,
    norm_id: str,
    version_id: str,
    total_pages: int,
    findings: list[dict[str, Any]],
    status: str,
    failed_pages: list[int],
) -> dict[str, Any]:
    violations = [x for x in findings if x.get("type") == "violation"]
    return {
        "template": "reference_normcontrol_report_ios_3.1",
        "document_id": document_id,
        "document_name": pdf_name,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "normative_document": normative_number,
        "normative_version": version_id,
        "normative_registry_id": norm_id,
        "results": findings,
        "check_scope": {
            "pages_checked": total_pages - len(failed_pages),
            "pages_available": total_pages,
            "limited": False,
            "max_pages": None,
            "failed_pages": failed_pages,
        },
        "summary": {
            "pages": total_pages,
            "total": len(findings),
            "violations": len(violations),
            "critical": sum(x.get("severity") == "critical" for x in violations),
            "major": sum(x.get("severity") == "major" for x in violations),
            "minor": sum(x.get("severity") == "minor" for x in violations),
            "compliant": sum(x.get("type") == "compliant" for x in findings),
            "unchecked": sum(x.get("type") == "unchecked" for x in findings),
        },
    }


def run_resilient_check(
    document_id: str,
    normative_number: str = DEFAULT_NORM_NUMBER,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run the full check with page checkpoints and bounded per-page retries."""
    def progress(**data: Any) -> None:
        if progress_callback:
            progress_callback(data)

    root = Path(__file__).resolve().parents[2] / "knowledge" / "project_documents" / document_id
    pdf_path = root / "source.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Исходный PDF не найден")

    evidence_dir = root / "checking" / "first_pass"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = _checkpoint_path(evidence_dir)

    storage = KnowledgeStorage()
    norm_document, norm_version = resolve_current_norm(storage, normative_number)
    norm_id, version_id = str(norm_document["id"]), str(norm_version["id"])
    retriever = Retriever(norm_id, version_id, storage)

    progress(stage="preparing", percent=1, current_page=0, total_pages=0, message="Подготовка проверки…")
    pages = render_pdf_pages(pdf_path, evidence_dir, dpi=CHECK_DPI)
    total_pages = len(pages)
    checkpoint = _load_checkpoint(checkpoint_file, document_id, pdf_path.name)
    completed_pages = {int(x) for x in checkpoint.get("completed_pages", [])}
    findings: list[dict[str, Any]] = [x for x in checkpoint.get("findings", []) if isinstance(x, dict)]
    next_finding_id = max((int(x.get("id", 0) or 0) for x in findings), default=0) + 1

    progress(
        stage="visual",
        percent=2,
        current_page=max(completed_pages, default=0),
        total_pages=total_pages,
        message=(f"Возобновляю проверку: уже завершено страниц {len(completed_pages)} из {total_pages}." if completed_pages else f"Подготовлено страниц: {total_pages}. Начинаю строгий визуальный анализ…"),
    )

    failed_pages: list[int] = []
    for page_index, page in enumerate(pages, start=1):
        if page_index in completed_pages:
            continue

        page_start = 2 + int((page_index - 1) / max(total_pages, 1) * 96)
        page_success = False
        last_error: Exception | None = None

        for attempt in range(1, MAX_PAGE_RETRIES + 1):
            client = LMStudioClient(model=None)
            try:
                progress(
                    stage="visual",
                    percent=page_start,
                    current_page=page_index,
                    total_pages=total_pages,
                    retry=attempt if attempt > 1 else 0,
                    message=(f"Повторная обработка страницы {page_index} из {total_pages} (попытка {attempt}/{MAX_PAGE_RETRIES})…" if attempt > 1 else f"Анализ страницы {page_index} из {total_pages}…"),
                )
                visual_prompt = f"""Ты выполняешь строгий первый визуальный проход нормоконтроля страницы PDF №{page.page}.

Ищи ТОЛЬКО конкретные визуально проверяемые факты, которые потенциально могут быть сопоставлены с требованием СП 30.13330.2020: реальные размеры и расстояния, отметки, диаметры, уклоны, параметры таблиц, видимые элементы схем, подключения, обозначения и другие инженерные параметры.

НЕ возвращай:
- просто названия проекта, раздела или тома;
- номера документов сами по себе;
- декоративный или организационный текст;
- утверждение «это нарушение» без нормы;
- предположения о невидимых данных.

Для каждого кандидата ОБЯЗАТЕЛЬНО укажи точный видимый факт в evidence_text, кратко объясни, что именно на странице нужно проверить, confidence от 0 до 1 и bbox в пикселях [x1,y1,x2,y2]. Если точный bbox определить нельзя — не возвращай кандидата.

Верни только JSON-массив:
[{{"title":"конкретный объект проверки","description":"какой конкретный факт виден и что именно проверяется","evidence_text":"точный видимый текст/значение/обозначение","bbox":[x1,y1,x2,y2],"confidence":0.0}}]
Если конкретных фактов нет, верни []."""
                candidates = _strict_candidates(_json_array(_vision_request(client, visual_prompt, Path(page.image_path), 1000)))
                progress(stage="normative", percent=min(98, page_start + 1), current_page=page_index, total_pages=total_pages, message=f"Страница {page_index}: найдено кандидатов {len(candidates)}. Выполняю RAG-проверку…")

                page_findings: list[dict[str, Any]] = []
                for candidate in candidates:
                    bbox = normalize_bbox(candidate.get("bbox"), page.width, page.height)
                    query = " ".join(str(candidate.get(k, "")) for k in ("title", "description", "evidence_text"))
                    norm_results = retriever.search(query, top_k=MAX_NORM_RESULTS) if query else []
                    norm_text = _context_text(norm_results, normative_number)
                    if not norm_text:
                        decision = {
                            "type": "unchecked",
                            "title": candidate.get("title", "Потенциальное несоответствие"),
                            "description": candidate.get("description", ""),
                            "recommendation": "Недостаточно нормативного контекста для подтверждения.",
                            "severity": "minor",
                            "confidence": 0.0,
                        }
                    else:
                        decision = _decision(client, candidate, norm_text)

                    finding_id = next_finding_id + len(page_findings)
                    evidence_image = None
                    image_url = None
                    if bbox:
                        evidence_path = evidence_dir / "annotated" / f"page_{page.page:04d}_finding_{finding_id:03d}.png"
                        evidence_image = annotate_evidence(page.image_path, bbox, evidence_path)
                        image_url = f"{REPORT_API_BASE}/api/reports/evidence/{document_id}/{evidence_path.name}"
                    page_findings.append({
                        "id": finding_id,
                        "type": decision.get("type", "unchecked"),
                        "docId": document_id,
                        "docName": pdf_path.name,
                        "title": str(decision.get("title") or candidate.get("title") or "Результат проверки"),
                        "description": str(decision.get("description") or candidate.get("description") or ""),
                        "recommendation": str(decision.get("recommendation") or ""),
                        "sheet": str(decision.get("sheet") or ""),
                        "norm": str(decision.get("norm") or normative_number),
                        "clause": str(decision.get("clause") or ""),
                        "severity": str(decision.get("severity") or "minor"),
                        "page": page.page,
                        "bbox": bbox,
                        "evidence_image": evidence_image,
                        "image": image_url,
                        "evidence_text": str(candidate.get("evidence_text") or ""),
                        "confidence": decision.get("confidence", candidate.get("confidence")),
                        "normative_sources": norm_results,
                    })

                findings.extend(page_findings)
                next_finding_id += len(page_findings)
                completed_pages.add(page_index)
                checkpoint.update({
                    "status": "running",
                    "pages_completed": len(completed_pages),
                    "completed_pages": sorted(completed_pages),
                    "findings": findings,
                    "last_error": None,
                })
                _write_json(checkpoint_file, checkpoint)
                page_success = True
                progress(stage="visual", percent=min(98, 2 + int(page_index / max(total_pages, 1) * 96)), current_page=page_index, total_pages=total_pages, page_completed=True, message=f"Страница {page_index} из {total_pages} завершена. Кандидатов: {len(candidates)}.")
                break
            except Exception as error:
                last_error = error
                checkpoint["last_error"] = {"page": page_index, "attempt": attempt, "error": str(error), "at": datetime.now().isoformat(timespec="seconds")}
                _write_json(checkpoint_file, checkpoint)
                if attempt < MAX_PAGE_RETRIES:
                    progress(stage="retry", percent=page_start, current_page=page_index, total_pages=total_pages, retry=attempt, message=f"Ошибка страницы {page_index}: {error}. Повторяю через {int(RETRY_DELAY_SECONDS)} с…")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    failed_pages.append(page_index)
                    progress(stage="error", percent=page_start, current_page=page_index, total_pages=total_pages, message=f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {error}")

        if not page_success:
            raise RuntimeError(f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {last_error}")

    report = _build_report(document_id, pdf_path.name, normative_number, norm_id, version_id, total_pages, findings, "completed", failed_pages)
    report_path = evidence_dir / "report.json"
    _write_json(report_path, report)
    checkpoint["status"] = "completed"
    checkpoint["pages_completed"] = total_pages
    checkpoint["completed_pages"] = list(range(1, total_pages + 1))
    checkpoint["findings"] = findings
    checkpoint["last_error"] = None
    _write_json(checkpoint_file, checkpoint)
    progress(stage="completed", percent=100, current_page=total_pages, total_pages=total_pages, page_completed=True, message="Проверка завершена. Отчёт готов.")
    return report
