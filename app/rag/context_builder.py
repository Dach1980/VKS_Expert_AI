"""
VKS Expert AI
Context Builder v1

Purpose:
Prepare retrieved FAISS results for LLM prompt.

Pipeline:

Question
    ↓
Retriever
    ↓
Retrieved records
    ↓
Context Builder
    ↓
Structured LLM context
"""


from pathlib import Path
from datetime import datetime


class ContextBuilder:
    """
    Builds clean context from Retriever results.
    """

    def __init__(
        self,
        document="СП 30.13330.2020",
        max_chars=12000,
    ):
        self.document = document
        self.max_chars = max_chars


    def build(
        self,
        query: str,
        results: list,
    ) -> str:
        """
        Build LLM-ready context.

        Args:
            query:
                User question

            results:
                Retriever output list

        Returns:
            formatted context string
        """

        context_parts = []

        header = f"""
DOCUMENT:
{self.document}

QUERY:
{query}

RELEVANT CONTEXT:
""".strip()

        context_parts.append(header)


        current_length = len(header)


        for item in results:

            page = item.get(
                "page",
                "?"
            )

            score = item.get(
                "score",
                0
            )

            text = item.get(
                "text",
                ""
            )


            if not text.strip():
                continue


            block = (
                f"\n\n"
                f"=== Page {page} "
                f"(score={score:.4f}) ===\n\n"
                f"{text.strip()}"
            )


            if (
                current_length
                + len(block)
                > self.max_chars
            ):
                break


            context_parts.append(block)

            current_length += len(block)


        return "".join(context_parts)



def print_context(context: str):

    print("=" * 70)
    print("GENERATED CONTEXT")
    print("=" * 70)
    print(context)
    print("=" * 70)



def demo():

    """
    Small standalone test.
    """

    from app.rag.retriever import Retriever


    retriever = Retriever()


    query = (
        "расчетный расход воды "
        "внутреннего водоснабжения"
    )


    results = retriever.search(
        query=query,
        top_k=5,
    )


    builder = ContextBuilder()


    context = builder.build(
        query=query,
        results=results,
    )


    print_context(context)



if __name__ == "__main__":

    print("=" * 70)
    print("VKS Expert AI")
    print("Context Builder v1")
    print("=" * 70)

    demo()
    