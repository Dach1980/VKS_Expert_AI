"""
VKS Expert AI
Evidence Validator v1

Purpose:
Validate retrieved RAG evidence before sending
context to LLM.

Architecture:

Retriever results
        |
        v
Evidence Validator
        |
        +-- relevance check
        |
        +-- score filtering
        |
        +-- source validation
        |
        v
Validated evidence
        |
        v
Context Builder
        |
        v
LLM


Phase:
2 - RAG Quality Control
"""


from dataclasses import dataclass
from typing import List, Dict



@dataclass
class EvidenceResult:
    """
    Validation result.
    """

    accepted: list
    rejected: list
    confidence: float
    sufficient: bool



class EvidenceValidator:
    """
    Validate retrieved normative evidence.
    """


    def __init__(
        self,
        min_score: float = 0.65,
        min_results: int = 1,
    ):

        self.min_score = min_score
        self.min_results = min_results



    def validate(
        self,
        question: str,
        results: List[Dict],
    ) -> EvidenceResult:
        """
        Validate FAISS retrieval results.

        Args:

            question:
                User question

            results:
                Retriever output


        Returns:

            EvidenceResult
        """


        accepted = []
        rejected = []



        for item in results:


            score = item.get(
                "score",
                0
            )


            text = item.get(
                "text",
                ""
            )


            document = item.get(
                "document",
                ""
            )



            reason = None



            # -----------------------------------------
            # Score validation
            # -----------------------------------------

            if score < self.min_score:

                reason = (
                    f"low similarity score "
                    f"{score:.3f}"
                )


            # -----------------------------------------
            # Empty text
            # -----------------------------------------

            if not text.strip():

                reason = (
                    "empty evidence text"
                )


            # -----------------------------------------
            # Document validation
            # -----------------------------------------

            if not document:

                reason = (
                    "unknown document"
                )



            if reason:


                rejected.append(
                    {
                        "item": item,
                        "reason": reason
                    }
                )

            else:

                accepted.append(
                    item
                )



        confidence = (
            self._calculate_confidence(
                accepted
            )
        )


        sufficient = (
            len(accepted)
            >= self.min_results
        )



        return EvidenceResult(

            accepted=accepted,

            rejected=rejected,

            confidence=confidence,

            sufficient=sufficient

        )



    def _calculate_confidence(
        self,
        accepted: list
    ) -> float:
        """
        Calculate evidence confidence.
        """


        if not accepted:

            return 0.0



        scores = [

            item.get(
                "score",
                0
            )

            for item in accepted

        ]


        return round(
            sum(scores)
            /
            len(scores),

            3

        )



def print_validation(
    result: EvidenceResult
):

    print("=" * 70)
    print("EVIDENCE VALIDATION")
    print("=" * 70)


    print(
        "Accepted:",
        len(result.accepted)
    )


    print(
        "Rejected:",
        len(result.rejected)
    )


    print(
        "Confidence:",
        result.confidence
    )


    print(
        "Sufficient:",
        result.sufficient
    )



def demo():

    from app.rag.retriever import Retriever


    retriever = Retriever()


    question = (
        "Как определяется "
        "максимальный расчетный "
        "расход воды?"
    )


    results = retriever.search(
        question,
        top_k=5
    )


    validator = EvidenceValidator()


    validation = validator.validate(
        question,
        results
    )


    print_validation(
        validation
    )


    print("\nVALID SOURCES:")


    for item in validation.accepted:

        print(
            item["document"],
            "page=",
            item["page"],
            "score=",
            item["score"]
        )



if __name__ == "__main__":


    print("=" * 70)
    print(
        "VKS Expert AI"
    )
    print(
        "Evidence Validator v1"
    )
    print("=" * 70)


    demo()
    