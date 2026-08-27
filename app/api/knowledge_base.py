"""
VKS Expert AI

Knowledge Base API

Frontend -> RAG Pipeline bridge
"""


from fastapi import APIRouter, Depends
from pydantic import BaseModel


from app.api.dependencies import get_rag_pipeline
from app.rag.rag_pipeline import RAGPipeline



router = APIRouter(
    prefix="/api/knowledge-base",
    tags=["knowledge-base"]
)



# -------------------------------------------------
# Shared pipeline
# -------------------------------------------------

# print("Initializing shared RAG pipeline...")

# pipeline = RAGPipeline()

# print("Shared RAG pipeline ready")



# -------------------------------------------------
# Request model
# -------------------------------------------------


class KnowledgeQuery(BaseModel):

    question: str

    search_in_norms: bool = True

    search_in_docs: bool = False



# -------------------------------------------------
# Response
# -------------------------------------------------


@router.post("/query")
def query_database(
    request: KnowledgeQuery,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):


    print("\n===== KNOWLEDGE QUERY =====")

    print(
        request.question
    )


    result = pipeline.ask(
        request.question
    )


    sources = []


    for item in result.get(
        "sources",
        []
    ):


        sources.append(

            {

                "document":
                    item.get(
                        "document"
                    ),

                "page":
                    item.get(
                        "page"
                    ),

                "score":
                    item.get(
                        "score"
                    )

            }

        )



    return {

        "question":
            request.question,


        "answer":
            result["answer"],


        "sources":
            sources,


        "confidence":
            result.get(
                "evidence_confidence",
                False
            )

    }
