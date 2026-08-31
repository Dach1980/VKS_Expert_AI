"""Project Expert AI — document checking API v1."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.documents import DOCUMENTS_ROOT
from app.llm.lmstudio_client import LMStudioClient
from app.rag.retriever import Retriever


router = APIRouter(prefix="/api/checks", tags=["checks"])


def _load_project_text(document_id: str) -> str:
    parsed = DOCUMENTS_ROOT / document_id / "parsed.json"
    if not parsed.exists():
        raise HTTPException(status_code=409, detail="Документ ещё не обработан")
    try:
        data = json.loads(parsed.read_text(encoding="utf-8"))
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


@router.post("/{document_id}")
def check_document(document_id: str):
    project_text = _load_project_text(document_id)
    if not project_text:
        raise HTTPException(status_code=409, detail="В PDF не найден текст для проверки")

    # Keep the first V1 request bounded. The normative Retriever remains the
    # existing RAG implementation and is used as the source of requirements.
    question = "Какие требования СП 30.13330.2020 непосредственно относятся к проектному решению внутреннего водопровода?"
    try:
        retriever = Retriever()
        normative = retriever.search(question, top_k=5)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось получить нормативный контекст: {error}") from error

    context_parts = []
    for item in normative:
        content = item.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        if text:
            context_parts.append(f"СП 30.13330.2020, стр. {item.get('page', '—')}: {text}")
    normative_context = "\n\n".join(context_parts)

    # Avoid sending an unbounded project document into the local model.
    project_excerpt = project_text[:45000]
    prompt = f"""
Проведи предварительный инженерный нормоконтроль проектной документации.

Верни только JSON-массив объектов. Каждый объект должен содержать:
- type: violation | compliant | unchecked
- title
- description
- recommendation
- sheet: номер листа или пустая строка
- norm: нормативный источник или пустая строка
- severity: critical | major | minor
- page: номер страницы PDF или 0

Не выдумывай сведения, которых нет в проектном документе или нормативном контексте.
Если доказательств недостаточно, используй unchecked.

НОРМАТИВНЫЙ КОНТЕКСТ:
{normative_context}

ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ:
{project_excerpt}
"""

    system_prompt = """
Ты инженерный AI-ассистент Project Expert AI.
Отвечай только на русском языке.
Используй только предоставленные проектные данные и нормативный контекст.
Не придумывай номера листов, пункты СП, размеры и требования.
Результат должен быть только валидным JSON-массивом без Markdown.
"""

    try:
        answer = LMStudioClient(model="qwen/qwen3.5-9b-mtp").chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=4096,
            enable_thinking=False,
        )
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"LM Studio недоступна: {error}") from error

    try:
        raw = answer.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1).replace("```", "", 1).strip()
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("LLM returned non-list JSON")
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"LM Studio вернула некорректный формат проверки: {error}") from error

    normalized = []
    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append({
            "id": index,
            "type": item.get("type", "unchecked"),
            "docId": document_id,
            "docName": Path(_load_project_name(document_id)).stem,
            "title": str(item.get("title", "Результат проверки")),
            "description": str(item.get("description", "")),
            "recommendation": str(item.get("recommendation", "")),
            "sheet": str(item.get("sheet", "")),
            "norm": str(item.get("norm", "")),
            "severity": item.get("severity", "minor"),
            "page": int(item.get("page", 0) or 0),
            "image": None,
        })

    return {
        "success": True,
        "document_id": document_id,
        "results": normalized,
        "normative_sources": [
            {"document": item.get("document", "СП 30.13330.2020"), "page": item.get("page", 0), "score": item.get("score", 0.0)}
            for item in normative
        ],
    }


def _load_project_name(document_id: str) -> str:
    registry = DOCUMENTS_ROOT / "documents.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    item = next((x for x in data if x["id"] == document_id), None)
    return item.get("filename", document_id) if item else document_id
