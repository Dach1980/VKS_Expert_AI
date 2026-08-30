"""
VKS Expert AI

Evidence Validator v1.2

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

v1.2 changes:

- FAISS similarity is the primary relevance signal.
- Engineering relevance is a secondary signal.
- Formula contexts receive a small additional bonus.
- Lower acceptance threshold for real normative fragments.
- Detailed validation diagnostics.
- Compatible with RAGPipeline v1.3.
"""


from dataclasses import dataclass
from typing import List


# ============================================================
# RESULT
# ============================================================


@dataclass
class EvidenceResult:
    """
    Result of evidence validation.
    """

    confidence: float

    accepted: List[dict]

    rejected: List[dict]

    sufficient: bool


# ============================================================
# VALIDATOR
# ============================================================


class EvidenceValidator:
    """
    Engineering evidence validator.

    v1.2

    Main principle:

        FAISS similarity
                +
        engineering relevance
                +
        optional formula bonus
                =
        evidence score

    FAISS similarity remains the primary signal.
    """

    def __init__(
        self,
        min_score: float = 0.55,
        min_confidence: float = 0.55,
    ):

        self.min_score = min_score

        self.min_confidence = min_confidence

    # ========================================================
    # ENGINEERING DICTIONARIES
    # ========================================================

    DOMAIN_KEYWORDS = {

        "internal_water_supply": [

            "водоснабж",
            "водопровод",
            "хвс",
            "гвс",
            "расход воды",
            "секундный расход",
            "расчетный расход",
            "давление",
            "напор",
            "трубопровод",
            "стояк",
            "водоразбор",
            "водоразборный",
            "система холодного водоснабжения",
            "система горячего водоснабжения",

        ],

        "sewerage": [

            "канализа",
            "сток",
            "водоотведение",
            "гидравлический затвор",
            "канализационный стояк",
            "расчетный расход стоков",

        ],

        "fire_water": [

            "пожар",
            "внутренний пожарный водопровод",
            "спринклер",
            "расход пожарный",
            "пожаротушение",
            "пожарный кран",

        ],

    }

    TOPIC_KEYWORDS = {

        "hydraulic_calculation": [

            "расход",
            "напор",
            "давление",
            "гидравличес",
            "диаметр",
            "потери",
            "формула",
            "скорость",
            "водоразбор",
            "расчетный",

        ],

        "pipe_selection": [

            "диаметр",
            "труба",
            "материал",
            "скорость",
            "трубопровод",

        ],

        "normative_requirement": [

            "требования",
            "должен",
            "следует",
            "нормы",
            "предусматривать",
            "допускается",
            "не допускается",
            "принимать",
            "предусматривается",

        ],

    }

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
        results: List[dict],
        intent=None,
        top_k: int = 5,
    ) -> EvidenceResult:
        """
        Validate retrieved fragments.

        Each result receives an evidence_score based on:

            75% FAISS similarity
            25% engineering relevance
            + formula bonus

        Results above min_score are accepted.
        """

        accepted = []

        rejected = []

        confidence_values = []

        # ----------------------------------------------------
        # Process every retrieved item
        # ----------------------------------------------------

        for item in results:

            content = item.get(
                "content",
                {}
            )

            # ------------------------------------------------
            # Extract text
            # ------------------------------------------------

            if isinstance(content, dict):

                text = content.get(
                    "text",
                    ""
                )

            else:

                text = str(content)

            text = str(
                text
            ).lower().strip()

            # ------------------------------------------------
            # FAISS score
            # ------------------------------------------------

            score = float(
                item.get(
                    "score",
                    0.0
                )
            )

            # ------------------------------------------------
            # Engineering relevance
            # ------------------------------------------------

            relevance = self._calculate_relevance(
                text,
                intent
            )

            # ------------------------------------------------
            # Formula bonus
            # ------------------------------------------------

            formula_bonus = 0.0

            if item.get("type") == "formula_context":

                formula_bonus = 0.10

            # ------------------------------------------------
            # Final evidence score
            # ------------------------------------------------

            final_score = (
                score * 0.75
                +
                relevance * 0.25
                +
                formula_bonus
            )

            # Prevent score above 1.0

            final_score = min(
                final_score,
                1.0
            )

            # ------------------------------------------------
            # Diagnostics
            # ------------------------------------------------

            item["evidence_score"] = round(
                final_score,
                3
            )

            item["relevance_score"] = round(
                relevance,
                3
            )

            item["faiss_score"] = round(
                score,
                3
            )

            item["formula_bonus"] = round(
                formula_bonus,
                3
            )

            # ------------------------------------------------
            # Accept / reject
            # ------------------------------------------------

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

        # ====================================================
        # CONFIDENCE
        # ====================================================

        if confidence_values:

            confidence = (
                sum(confidence_values)
                /
                len(confidence_values)
            )

        else:

            confidence = 0.0

        # ====================================================
        # SUFFICIENT EVIDENCE
        # ====================================================

        sufficient = (

            len(accepted) > 0

            and

            confidence >= self.min_confidence

        )

        # ====================================================
        # SORT ACCEPTED
        # ====================================================

        accepted = sorted(

            accepted,

            key=lambda x:
                x.get(
                    "evidence_score",
                    0.0
                ),

            reverse=True

        )[:top_k]

        # ====================================================
        # DIAGNOSTICS
        # ====================================================

        print()
        print(
            "===== EVIDENCE VALIDATION ====="
        )

        print(
            "Input:",
            len(results)
        )

        print(
            "Accepted:",
            len(accepted)
        )

        print(
            "Rejected:",
            len(rejected)
        )

        print(
            "Confidence:",
            round(
                confidence,
                3
            )
        )

        print(
            "Sufficient:",
            sufficient
        )

        for i, item in enumerate(
            accepted,
            1
        ):

            print()

            print(
                f"ACCEPTED #{i}"
            )

            print(
                "Page:",
                item.get("page")
            )

            print(
                "FAISS:",
                item.get("faiss_score")
            )

            print(
                "Relevance:",
                item.get("relevance_score")
            )

            print(
                "Evidence:",
                item.get("evidence_score")
            )

        print(
            "==============================="
        )

        # ====================================================
        # RETURN
        # ====================================================

        return EvidenceResult(

            confidence=round(
                confidence,
                3
            ),

            accepted=accepted,

            rejected=rejected,

            sufficient=sufficient

        )

    # ========================================================
    # RELEVANCE CALCULATION
    # ========================================================

    def _calculate_relevance(
        self,
        text: str,
        intent
    ) -> float:
        """
        Calculate engineering relevance.

        The value is between 0 and 1.

        System relevance contributes up to 0.55.
        Topic relevance contributes up to 0.45.
        """

        # ----------------------------------------------------
        # No intent
        # ----------------------------------------------------

        if intent is None:

            return 0.5

        score = 0.0

        # ====================================================
        # SYSTEM MATCH
        # ====================================================

        system_words = (
            self.DOMAIN_KEYWORDS.get(
                getattr(
                    intent,
                    "system",
                    ""
                ),
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

                system_hits * 0.15,

                0.55

            )

        # ====================================================
        # TOPIC MATCH
        # ====================================================

        topic_words = (
            self.TOPIC_KEYWORDS.get(
                getattr(
                    intent,
                    "topic",
                    ""
                ),
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

                topic_hits * 0.10,

                0.45

            )

        # ====================================================
        # NORMALIZE
        # ====================================================

        return min(
            score,
            1.0
        )


# ============================================================
# DEMO
# ============================================================


def demo():

    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Evidence Validator v1.2"
    )

    print("=" * 70)

    sample = [

        {
            "page": 27,

            "score": 0.81,

            "type": "text",

            "content": {

                "text":
                """
                Максимальный расчетный расход воды
                определяется по формуле.
                Гидравлический расчет внутренних
                систем водоснабжения.
                """

            }

        },

        {
            "page": 35,

            "score": 0.74,

            "type": "text",

            "content": {

                "text":
                """
                Канализационный стояк.
                Гидравлический затвор.
                """

            }

        }

    ]

    validator = EvidenceValidator()

    result = validator.validate(
        sample
    )

    print()

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


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":

    demo()
    