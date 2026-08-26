"""
VKS Expert AI
API Dependencies v1

Purpose:
FastAPI dependency providers.

Architecture:

HTTP Request
      |
      v
FastAPI Dependency
      |
      v
RAG Pipeline instance
      |
      v
Retriever + LLM
"""


from functools import lru_cache


from app.rag.rag_pipeline import RAGPipeline



# ==========================================================
# RAG Pipeline provider
# ==========================================================


@lru_cache()
def get_rag_pipeline() -> RAGPipeline:
    """
    Returns shared RAG pipeline instance.

    Pipeline is created once and reused
    between API requests.
    """

    print(
        "Initializing shared RAG pipeline..."
    )


    pipeline = RAGPipeline()


    print(
        "Shared RAG pipeline ready"
    )


    return pipeline
