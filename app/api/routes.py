"""Project Expert AI — API Routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.knowledge_base import router as knowledge_router
from app.api.dependencies import get_rag_pipeline
from app.rag.rag_pipeline import RAGPipeline
from app.api.schemas import (
    QuestionRequest,
    AnswerResponse,
    HealthResponse,
    SourceInfo,
    EvidenceInfo,
)


router = APIRouter()
router.include_router(knowledge_router)


@router.get("/")
def root():
    return {
        "service": "Project Expert AI",
        "status": "running",
        "version": "phase3-api-v1",
    }


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@router.post("/ask", response_model=AnswerResponse)
def ask(
    request: QuestionRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    try:
        result = pipeline.ask(
            question=request.question,
            top_k=request.top_k,
        )

        sources = [
            SourceInfo(
                document=item.get("document", "unknown"),
                page=item.get("page", 0),
                score=item.get("score", 0.0),
            )
            for item in result.get("sources", [])
        ]

        evidence = None
        if "evidence_confidence" in result:
            evidence = EvidenceInfo(
                confidence=result.get("evidence_confidence", 0.0),
                accepted=result.get("accepted", 0),
                rejected=result.get("rejected", 0),
                sufficient=result.get("evidence_sufficient", False),
            )

        return AnswerResponse(
            question=result["question"],
            answer=result["answer"],
            evidence_confidence=result.get("evidence_confidence"),
            evidence_sufficient=result.get("evidence_sufficient"),
            evidence=evidence,
            sources=sources,
        )

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(error)) from error
