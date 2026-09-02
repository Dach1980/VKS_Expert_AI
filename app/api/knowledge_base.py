"""Project Expert AI — Knowledge Base API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_rag_pipeline
from app.rag.rag_diagnostics import RAGDiagnostics
from app.rag.rag_pipeline import RAGPipeline


router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


class KnowledgeQuery(BaseModel):
    question: str
    search_in_norms: bool = True
    search_in_docs: bool = False
    top_k: int = Field(default=5, ge=1, le=20)
    diagnostics: bool = False


@router.post("/query")
def query_database(
    request: KnowledgeQuery,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """Run the normal RAG answer and optionally expose retrieval diagnostics."""
    result = pipeline.ask(request.question, top_k=request.top_k)

    response = {
        "question": request.question,
        "answer": result.get("answer", ""),
        "sources": [
            {
                "document": item.get("document"),
                "page": item.get("page"),
                "score": item.get("score", 0.0),
            }
            for item in result.get("sources", [])
        ],
        "confidence": result.get("evidence_confidence", 0.0),
        "evidence_sufficient": result.get("evidence_sufficient", False),
        "search_in_norms": request.search_in_norms,
        "search_in_docs": request.search_in_docs,
    }

    if request.diagnostics:
        response["diagnostics"] = RAGDiagnostics(pipeline).run(
            request.question,
            top_k=request.top_k,
        )

    if request.search_in_docs:
        response["diagnostic_notice"] = (
            "Проектная документация пока обрабатывается только в PDF-пайплайне "
            "и ещё не подключена к отдельному векторному индексу RAG."
        )

    return response


@router.post("/diagnostics")
def diagnostics_database(
    request: KnowledgeQuery,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """Run retrieval/evidence diagnostics without generating an LLM answer."""
    return RAGDiagnostics(pipeline).run(request.question, top_k=request.top_k)
