"""Project Expert AI — Knowledge Base API."""

from __future__ import annotations

import re
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_rag_pipeline
from app.rag.rag_diagnostics import RAGDiagnostics


router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


class KnowledgeQuery(BaseModel):
    question: str
    search_in_norms: bool = True
    search_in_docs: bool = False
    top_k: int = Field(default=5, ge=1, le=20)
    diagnostics: bool = True


def _error_response(stage: str, error: Exception, status_code: int = 500):
    message = str(error) or error.__class__.__name__
    print(f"[Knowledge Base] {stage} failed: {message}")
    traceback.print_exc()
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": {
                "stage": stage,
                "type": error.__class__.__name__,
                "message": message,
            },
        },
    )


def _get_pipeline():
    # Resolve the cached pipeline inside the endpoint so an initialization
    # failure is returned as JSON to the browser instead of becoming an opaque
    # dependency 500 that hides the real RAG failure stage.
    return get_rag_pipeline()


def _display_document(item: dict) -> str:
    """Return a human-readable source name including the normative amendment."""
    document = str(item.get("document") or item.get("document_number") or "unknown")
    change = item.get("change_number")
    if change is None or str(change).strip() == "":
        metadata = item.get("metadata") or {}
        change = metadata.get("change_number")
    if change is None or str(change).strip() == "":
        filename = item.get("original_filename") or item.get("filename") or ""
        match = re.search(r"(?:изм(?:енение|енения)?\.?|изменени[ея])\s*№?\s*(\d+)\b", str(filename), re.IGNORECASE)
        if match:
            change = match.group(1)
    if change is None or str(change).strip() == "":
        version_id = str(item.get("version_id") or "")
        match = re.search(r"(?:^|[_\s-])(?:изм|amendment)[._\s-]*(\d+)(?:$|[_\s-])", version_id, re.IGNORECASE)
        if match:
            change = match.group(1)
    if change is not None and str(change).strip() != "":
        return f"{document} — Изменение №{str(change).strip()}"
    return document


@router.get("/status")
def knowledge_base_status():
    """Check every local dependency needed by the Knowledge Base RAG."""
    status = {
        "ok": True,
        "pipeline": {"ok": False},
        "norm_index": {"ok": False},
        "embedding_api": {"ok": False},
        "chat_api": {"ok": False},
    }
    try:
        pipeline = _get_pipeline()
        status["pipeline"] = {"ok": True, "type": type(pipeline).__name__}

        retriever = pipeline.retriever
        status["norm_index"] = {
            "ok": True,
            "document": retriever.document_id,
            "version": retriever.version_id,
            "index": str(retriever.index_file),
            "vectors": int(retriever.index.ntotal),
            "metadata": len(retriever.metadata),
        }

        embedding_ok = retriever.client.health_check()
        status["embedding_api"] = {
            "ok": bool(embedding_ok),
            "model": retriever.client.model,
            "endpoint": retriever.client.base_url,
        }

        try:
            models = pipeline.llm.get_models()
            available = [
                str(item.get("id", ""))
                for item in models.get("data", [])
                if isinstance(item, dict) and item.get("id")
            ]
            chat_models = [m for m in available if "embedding" not in m.lower()]
            status["chat_api"] = {
                "ok": bool(chat_models),
                "available_models": available,
                "chat_models": chat_models,
            }
        except Exception as error:
            status["chat_api"] = {
                "ok": False,
                "error": {"type": error.__class__.__name__, "message": str(error)},
            }

        status["ok"] = all(item.get("ok", False) for item in status.values() if isinstance(item, dict) and "ok" in item)
        return status
    except Exception as error:
        status["ok"] = False
        status["pipeline"] = {"ok": False, "error": {"type": error.__class__.__name__, "message": str(error)}}
        return status


@router.post("/query")
def query_database(request: KnowledgeQuery):
    """Run the complete RAG answer and expose retrieval diagnostics."""
    if not str(request.question or "").strip():
        return _error_response("question_validation", ValueError("Вопрос не задан."), 400)
    try:
        pipeline = _get_pipeline()
    except Exception as error:
        return _error_response("pipeline_initialization", error)

    try:
        result = pipeline.ask(request.question, top_k=request.top_k)
    except Exception as error:
        return _error_response("rag_pipeline", error)

    sources = []
    for item in result.get("sources", []):
        source = dict(item)
        source["document"] = _display_document(source)
        source["document_number"] = item.get("document")
        source["change_number"] = item.get("change_number")
        source["version_id"] = item.get("version_id")
        sources.append({
            "document": source["document"],
            "document_number": source.get("document_number"),
            "change_number": source.get("change_number"),
            "version_id": source.get("version_id"),
            "page": source.get("page"),
            "score": source.get("score", 0.0),
        })

    response = {
        "ok": True,
        "question": request.question,
        "answer": result.get("answer", ""),
        "sources": sources,
        "confidence": result.get("evidence_confidence", 0.0),
        "evidence_sufficient": result.get("evidence_sufficient", False),
        "retrieved_count": result.get("retrieved_count", 0),
        "accepted_count": result.get("accepted_count", 0),
        "rejected_count": result.get("rejected_count", 0),
        "search_in_norms": request.search_in_norms,
        "search_in_docs": request.search_in_docs,
    }

    if request.diagnostics:
        try:
            response["diagnostics"] = RAGDiagnostics(pipeline).run(
                request.question,
                top_k=request.top_k,
            )
        except Exception as error:
            response["diagnostics_error"] = {
                "stage": "rag_diagnostics",
                "type": error.__class__.__name__,
                "message": str(error),
            }

    if request.search_in_docs:
        response["diagnostic_notice"] = (
            "Проектная документация пока обрабатывается только в PDF-пайплайне "
            "и ещё не подключена к отдельному векторному индексу RAG."
        )

    return response


@router.post("/diagnostics")
def diagnostics_database(request: KnowledgeQuery):
    """Run retrieval/evidence diagnostics without generating an LLM answer."""
    if not str(request.question or "").strip():
        raise HTTPException(status_code=400, detail="Вопрос не задан.")
    try:
        pipeline = _get_pipeline()
        return RAGDiagnostics(pipeline).run(request.question, top_k=request.top_k)
    except Exception as error:
        return _error_response("rag_diagnostics", error)
