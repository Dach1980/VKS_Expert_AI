"""
VKS Expert AI
API Server v1

Purpose:
HTTP interface for VKS Expert AI RAG system.

Architecture:

Browser / UI
      |
      v
 FastAPI
      |
      v
 RAG Pipeline
      |
      v
 Retriever + Validator + LLM
"""


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


from app.rag.rag_pipeline import RAGPipeline



# --------------------------------------------------
# Application
# --------------------------------------------------

app = FastAPI(
    title="VKS Expert AI",
    description=
    """
    Local engineering AI assistant
    for construction documentation analysis.

    Stack:
    - FAISS RAG
    - Query Classification
    - Evidence Validation
    - LM Studio LLM
    """,
    version="0.1",
)



# --------------------------------------------------
# Global pipeline instance
# --------------------------------------------------

pipeline = None



@app.on_event("startup")
def startup_event():

    global pipeline

    print("=" * 70)
    print("Starting VKS Expert AI API")
    print("=" * 70)

    pipeline = RAGPipeline()



# --------------------------------------------------
# Schemas
# --------------------------------------------------


class QuestionRequest(BaseModel):

    question: str

    top_k: int = 5



class SourceInfo(BaseModel):

    document: str

    page: int | str

    score: float



class AnswerResponse(BaseModel):

    question: str

    answer: str

    evidence_confidence: float | None

    evidence_sufficient: bool | None

    sources: list[SourceInfo]



# --------------------------------------------------
# Health check
# --------------------------------------------------


@app.get("/")
def root():

    return {

        "application":
            "VKS Expert AI",

        "status":
            "running",

        "version":
            "0.1"

    }



# --------------------------------------------------
# Ask endpoint
# --------------------------------------------------


@app.post(
    "/ask",
    response_model=AnswerResponse
)
def ask_question(
    request: QuestionRequest
):


    if pipeline is None:

        raise HTTPException(
            status_code=503,
            detail=
            "RAG Pipeline is not initialized"
        )



    try:

        result = pipeline.ask(
            question=request.question,
            top_k=request.top_k,
        )



        sources = []


        for item in result["sources"]:

            sources.append(
                SourceInfo(

                    document=
                        item.get(
                            "document",
                            "unknown"
                        ),

                    page=
                        item.get(
                            "page",
                            "?"
                        ),

                    score=
                        float(
                            item.get(
                                "score",
                                0
                            )
                        )

                )
            )



        return AnswerResponse(

            question=
                result["question"],

            answer=
                result["answer"],

            evidence_confidence=
                result.get(
                    "evidence_confidence"
                ),

            evidence_sufficient=
                result.get(
                    "evidence_sufficient"
                ),

            sources=sources

        )



    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    