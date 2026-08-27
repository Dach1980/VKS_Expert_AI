"""
VKS Expert AI
API Routes v1

Purpose:
FastAPI endpoints.

Endpoints:

GET  /
GET  /health
POST /ask

Architecture:

HTTP Request
      |
      v
API Routes
      |
      v
RAG Pipeline
      |
      v
Technical Answer
"""


from fastapi import APIRouter, HTTPException
from fastapi import Depends

from app.api.dependencies import get_rag_pipeline
from app.rag.rag_pipeline import RAGPipeline

from app.api.schemas import (
    QuestionRequest,
    AnswerResponse,
    HealthResponse,
    SourceInfo,
    EvidenceInfo,
)


# ==========================================================
# Router
# ==========================================================


router = APIRouter()



# ==========================================================
# Root
# ==========================================================


@router.get("/")
def root():

    return {
        "service": "VKS Expert AI",
        "status": "running",
        "version": "phase3-api-v1",
    }



# ==========================================================
# Health
# ==========================================================


@router.get(
    "/health",
    response_model=HealthResponse
)
def health():

    return HealthResponse()



# ==========================================================
# Ask
# ==========================================================


@router.post(
    "/ask",
    response_model=AnswerResponse
)
def ask(
    request: QuestionRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    try:

        result = pipeline.ask(
            question=request.question,
            top_k=request.top_k,
        )


        sources = []


        for item in result.get(
            "sources",
            []
        ):

            sources.append(
                SourceInfo(

                    document=item.get(
                        "document",
                        "unknown"
                    ),

                    page=item.get(
                        "page",
                        0
                    ),

                    score=item.get(
                        "score",
                        0.0
                    ),

                )
            )



        evidence = None


        if (
            "evidence_confidence"
            in result
        ):

            evidence = EvidenceInfo(

                confidence=result.get(
                    "evidence_confidence",
                    0.0
                ),

                accepted=result.get(
                    "accepted",
                    0
                ),

                rejected=result.get(
                    "rejected",
                    0
                ),

                sufficient=result.get(
                    "evidence_sufficient",
                    False
                ),
            )



        return AnswerResponse(

            question=result["question"],

            answer=result["answer"],

            evidence_confidence=result.get(
                "evidence_confidence"
            ),

            evidence_sufficient=result.get(
                "evidence_sufficient"
            ),

            evidence=evidence,

            sources=sources,

        )

    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )
        