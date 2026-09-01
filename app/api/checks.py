"""Project Expert AI — document checking API v5."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.documents import DOCUMENTS_ROOT
from app.knowledge.storage import KnowledgeStorage, StorageError
from app.llm.lmstudio_client import LMStudioClient
from app.rag.retriever import Retriever

router = APIRouter(prefix="/api/checks", tags=["checks"])

DEFAULT_NORM_NUMBER = "СП 30.13330.2020"

# LM Studio may have a deliberately small loaded context (the current local
# setup reports 8192 tokens). The checker therefore keeps the first-pass prompt
# bounded instead of sending an entire project PDF to the LLM in one request.
# A later checking stage can process the remaining pages in separate passes.
PROJECT_PROMPT_CHAR_LIMIT = 5000
NORMATIVE_PROMPT_CHAR_LIMIT = 2500
CHECK_MAX_OUTPUT_TOKENS = 1024


def _load_project_text(document_id: str) -> str:
    parsed = DOCUMENTS_ROOT / document_id / "parsed.json"
    if not parsed.exists():
        raise HTTPException(status_code=409, detail="Документ ещё не обработан")
    try:
        data = json.loads(parsed.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail=f"Не удалось прочитать parsed JSON: {error}") from error
    chunks = []
    for page in data.get("pages", []):
        page_number = page.get("page", 0)
        for block in page.get("blocks", []):
            text = str(block.get("text", "")).strip()
            if text:
                chunks.append(f"[стр. {page_number}] {text}")
    return "\n".join(chunks)


def _load_project_name(document_id: str) -> str:
    registry = DOCUMENTS_ROOT / "documents.json"
    if not registry.exists():
        return document_id
    try:
        data = json.loads(registry.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return document_id
    item = next((x for x in data if str(x.get("id")) == str(document_id)), None)
    return str(item.get("filename", document_id)) if item else document_id


def _resolve_norm(storage: KnowledgeStorage, canonical_number: str) -> tuple[str, dict, dict]:
    """Find the Registry document by canonical number, then resolve its current version."""
    target = storage.registry.canonical_number(canonical_number).lower()
    candidates = []
    target_group = storage.registry._number_group(canonical_number)
    for document in storage.registry.get_all_documents():
        number = storage.registry.canonical_number(document.get("number", "")).lower()
        if number == target:
            candidates.append(document)
            continue
        group = storage.registry._number_group(document.get("number", ""))
        if group and group == target_group:
            candidates.append(document)

    if not candidates:
        raise HTTPException(status_code=409, detail=f"В Registry не найден нормативный документ {canonical_number}.")

    candidates.sort(key=lambda item: (len(item.get("versions", [])), len(str(item.get("number", "")))), reverse=True)
    document = candidates[0]
    document_id = str(document.get("id"))

    try:
        current_version = storage.get_current_version(document_id)
    except Exception as error:
        raise HTTPException(
            status_code=409,
            detail=f"Для {canonical_number} в Registry нет действующей версии. Назначьте одну из версий действующей в разделе «Нормы».",
        ) from error

    return document_id, document, current_version


def _normative_context(retriever: Retriever, question: str, normative_number: str) -> list[dict]:
    try:
        results = retriever.search(question, top_k=5)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=409,
            detail=f"Проверка невозможна: индекс действующей версии {normative_number} не найден. Сначала нажмите «Индексировать» у действующей версии в разделе «Нормы».",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось получить нормативный контекст: {error}") from error

    if not results:
        raise HTTPException(
            status_code=409,
            detail=f"Индекс действующей версии {normative_number} существует, но не содержит доступных фрагментов. Переиндексируйте эту версию в разделе «Нормы».",
        )
    return results


def _clip_text(text: str, limit: int) -> str:
    """Keep an explicit character budget for small local LLM contexts."""
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[Контекст сокращён для текущего окна модели.]"


@router.post("/{document_id}")
def check_document(document_id: str):
    project_text = _load_project_text(document_id)
    if not project_text:
        raise HTTPException(status_code=409, detail="В PDF не найден текст для проверки")

    storage = KnowledgeStorage()
    norm_document_id, norm_document, current_version = _resolve_norm(storage, DEFAULT_NORM_NUMBER)
    current_version_id = str(current_version.get("id"))
    normative_number = str(norm_document.get("number") or DEFAULT_NORM_NUMBER)

    try:
        retriever = Retriever(norm_document_id, current_version_id, storage)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=409,
            detail=f"Проверка невозможна: для действующей версии {current_version_id} документа {normative_number} не найден FAISS-индекс. Откройте «Нормы» и нажмите «Индексировать» у этой версии.",
        ) from error
    except StorageError as error:
        raise HTTPException(status_code=409, detail=f"Не удалось определить путь нормативной версии: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось загрузить нормативный индекс: {error}") from error

    question = "Какие требования СП 30.13330.2020 непосредственно относятся к проектному решению внутреннего водопровода?"
    normative = _normative_context(retriever, question, normative_number)
    context_parts = []
    for item in normative:
        content = item.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        if text:
            context_parts.append(f"{normative_number}, стр. {item.get('page', '—')}: {text}")
    normative_context = _clip_text("\n\n".join(context_parts), NORMATIVE_PROMPT_CHAR_LIMIT)
    project_context = _clip_text(project_text, PROJECT_PROMPT_CHAR_LIMIT)

    prompt = f"""
Проведи предварительный инженерный нормоконтроль проектной документации.

Это первый проход по документу. Анализируй только переданный фрагмент проекта и нормативный контекст.

Верни только JSON-массив объектов. Каждый объект должен содержать:
- type: violation | compliant | unchecked
- title
- description
- recommendation
- sheet: номер листа или пустая строка
- norm: нормативный источник или пустая строка
- severity: critical | major | minor
- page: номер страницы PDF или 0
- bbox: массив [x1, y1, x2, y2] только если координаты надёжно известны; иначе null

Не выдумывай сведения. Если доказательств недостаточно, используй unchecked. Никогда не придумывай bbox.

НОРМАТИВНЫЙ КОНТЕКСТ:
{normative_context}

ФРАГМЕНТ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ:
{project_context}
"""
    system_prompt = """
Ты инженерный AI-ассистент Project Expert AI.
Отвечай только на русском языке.
Используй только предоставленные проектные данные и нормативный контекст.
Не придумывай номера листов, пункты СП, размеры и требования.
Если координаты места нарушения не представлены или не могут быть определены надёжно, возвращай bbox: null.
Результат должен быть только валидным JSON-массивом без Markdown.
"""

    try:
        # model=None now deterministically selects an LLM from /v1/models and
        # never the embedding model used by the RAG retriever.
        answer = LMStudioClient(model=None).chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=CHECK_MAX_OUTPUT_TOKENS,
            enable_thinking=False,
        )
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"LM Studio недоступна или модель не загружена: {error}") from error

    try:
        raw = answer.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1).replace("```", "", 1).strip()
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("LLM returned non-list JSON")
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"LM Studio вернула некорректный формат проверки: {error}") from error

    doc_name = Path(_load_project_name(document_id)).stem
    normalized = []
    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox")
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox)):
            bbox = None
        normalized.append({
            "id": index,
            "type": item.get("type", "unchecked"),
            "docId": document_id,
            "docName": doc_name,
            "title": str(item.get("title", "Результат проверки")),
            "description": str(item.get("description", "")),
            "recommendation": str(item.get("recommendation", "")),
            "sheet": str(item.get("sheet", "")),
            "norm": str(item.get("norm", normative_number)),
            "severity": item.get("severity", "minor"),
            "page": int(item.get("page", 0) or 0),
            "bbox": bbox,
            "image": None,
        })

    return {
        "success": True,
        "document_id": document_id,
        "document_name": doc_name,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "normative_document": normative_number,
        "normative_version": current_version_id,
        "normative_registry_id": norm_document_id,
        "results": normalized,
        "summary": {
            "total": len(normalized),
            "compliant": sum(x["type"] == "compliant" for x in normalized),
            "violations": sum(x["type"] == "violation" for x in normalized),
            "unchecked": sum(x["type"] == "unchecked" for x in normalized),
            "critical": sum(x["type"] == "violation" and x["severity"] == "critical" for x in normalized),
        },
        "normative_sources": [
            {"document": item.get("document", normative_number), "version": current_version_id, "page": item.get("page", 0), "score": item.get("score", 0.0)}
            for item in normative
        ],
    }
