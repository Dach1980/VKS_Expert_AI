"""
VKS Expert AI

Evidence Validator v1.1

Purpose:
Validate retrieved RAG evidence
before sending context to LLM.

Architecture:

Retriever results
        |
        v
Evidence Validator
        |
        +---- accepted evidence
        |
        +---- rejected evidence
        |
        v
Confidence score
"""


from dataclasses import dataclass
from typing import List, Dict



@dataclass
class EvidenceResult:
    """
    Evidence validation result.
    """

    confidence: float

    accepted: List[dict]

    rejected: List[dict]

    sufficient: bool



class EvidenceValidator:
    """
    Engineering evidence validator.

    Filters FAISS results according
    to engineering intent.
    """


    def __init__(
        self,
        min_score: float = 0.65,
        min_confidence: float = 0.55,
    ):

        self.min_score = min_score

        self.min_confidence = min_confidence



    # --------------------------------------------------
    # Engineering dictionaries
    # --------------------------------------------------

    DOMAIN_KEYWORDS = {


        "internal_water_supply":

        [
            "водоснабж",
            "водопровод",
            "хвс",
            "гвс",
            "расход воды",
            "секундный расход",
            "давление",
            "напор",
            "трубопровод",
            "стояк",
        ],



        "sewerage":

        [
            "канализа",
            "сток",
            "водоотведение",
            "гидравлический затвор",
        ],



        "fire_water":

        [
            "пожар",
            "внутренний пожарный водопровод",
            "спринклер",
            "расход пожарный",
        ],

    }



    TOPIC_KEYWORDS = {


        "hydraulic_calculation":

        [
            "расход",
            "напор",
            "давление",
            "гидравличес",
            "диаметр",
            "потери",
            "формула",
        ],


        "pipe_selection":

        [
            "диаметр",
            "труба",
            "материал",
            "скорость",
        ],


        "normative_requirement":

        [
            "требования",
            "должен",
            "следует",
            "нормы",
        ],

    }



    # --------------------------------------------------
    # Validation
    # --------------------------------------------------


    def validate(
        self,
        results: List[dict],
        intent=None,
    ) -> EvidenceResult:
        """
        Validate retrieved fragments.
        """


        accepted = []

        rejected = []


        confidence_values = []



        for item in results:


            text = (
                item.get(
                    "text",
                    ""
                )
                .lower()
            )


            score = float(
                item.get(
                    "score",
                    0
                )
            )



            relevance = self._calculate_relevance(
                text,
                intent
            )



            final_score = (
                score * 0.6
                +
                relevance * 0.4
            )



            item["evidence_score"] = round(
                final_score,
                3
            )



            if final_score >= self.min_score:

                accepted.append(
                    item
                )

                confidence_values.append(
                    final_score
                )


            else:

                rejected.append(
                    item
                )



        if confidence_values:

            confidence = sum(
                confidence_values
            ) / len(
                confidence_values
            )

        else:

            confidence = 0.0



        sufficient = (
            len(accepted) > 0
            and
            confidence >= self.min_confidence
        )



        return EvidenceResult(

            confidence=round(
                confidence,
                3
            ),

            accepted=accepted,

            rejected=rejected,

            sufficient=sufficient

        )



    # --------------------------------------------------
    # Relevance calculation
    # --------------------------------------------------


    def _calculate_relevance(
        self,
        text: str,
        intent
    ) -> float:
        """
        Calculate engineering relevance.
        """


        if intent is None:

            return 0.5



        score = 0.0



        # system match

        system_words = (
            self.DOMAIN_KEYWORDS
            .get(
                intent.system,
                []
            )
        )


        system_hits = sum(

            1

            for word in system_words

            if word in text

        )



        if system_hits:

            score += min(
                system_hits * 0.12,
                0.5
            )



        # topic match

        topic_words = (
            self.TOPIC_KEYWORDS
            .get(
                intent.topic,
                []
            )
        )


        topic_hits = sum(

            1

            for word in topic_words

            if word in text

        )



        if topic_hits:

            score += min(
                topic_hits * 0.08,
                0.4
            )



        return min(
            score,
            1.0
        )



# --------------------------------------------------
# Demo
# --------------------------------------------------


def demo():

    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Evidence Validator v1.1"
    )

    print("=" * 70)



    sample = [

        {
            "page": 27,
            "score": 0.81,
            "text":
            """
            Максимальный расчетный расход воды
            определяется по формуле.
            Гидравлический расчет внутренних
            систем водоснабжения.
            """
        },


        {
            "page": 35,
            "score": 0.74,
            "text":
            """
            Канализационный стояк.
            Гидравлический затвор.
            """
        }

    ]



    validator = EvidenceValidator()



    result = validator.validate(
        sample
    )



    print(
        "confidence:",
        result.confidence
    )

    print(
        "accepted:",
        len(result.accepted)
    )

    print(
        "rejected:",
        len(result.rejected)
    )



if __name__ == "__main__":

    demo()
    