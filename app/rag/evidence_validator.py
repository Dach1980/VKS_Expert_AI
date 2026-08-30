"""
VKS Expert AI

Evidence Validator v1.4

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

v1.4 changes:

- FAISS similarity remains an important signal,
  but is not sufficient by itself.
- Added query-specific relevance.
- Intent/system/topic relevance is preserved.
- Formula contexts analyze text + formula + continuation.
- Added evidence completeness checks.
- Added diagnostic validation reasons.
- Added score breakdown diagnostics.
- Added explicit rejection reasons.
- Added source/document awareness.
- Confidence is calculated from the final
  accepted evidence actually passed downstream.
- Compatible with RAGPipeline v1.5.
"""


from dataclasses import dataclass
from typing import List
import re


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

    v1.4

    Main principle:

        FAISS similarity
                +
        engineering relevance
                +
        query relevance
                +
        evidence completeness
                +
        optional formula bonus
                =
        evidence score

    FAISS similarity is NOT sufficient by itself.

    A fragment must have meaningful relationship
    with the engineering query.
    """

    def __init__(
        self,
        min_score: float = 0.55,
        min_confidence: float = 0.55,
        min_relevance: float = 0.10,
        min_query_relevance: float = 0.05,
        min_faiss_score: float = 0.20,
    ):

        self.min_score = min_score

        self.min_confidence = min_confidence

        self.min_relevance = min_relevance

        self.min_query_relevance = min_query_relevance

        self.min_faiss_score = min_faiss_score

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
            "максимальный расчетный расход",
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
            "расчет",
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
    # STOP WORDS
    # ========================================================

    STOP_WORDS = {

        "как",
        "какой",
        "какая",
        "какие",
        "какое",
        "что",
        "где",
        "когда",
        "для",
        "при",
        "по",
        "на",
        "в",
        "во",
        "из",
        "и",
        "или",
        "а",
        "о",
        "об",
        "с",
        "со",
        "к",
        "у",
        "от",
        "до",
        "за",
        "не",
        "же",
        "ли",
        "это",

    }

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
        results: List[dict],
        intent=None,
        top_k: int = 5,
        query: str = "",
    ) -> EvidenceResult:
        """
        Validate retrieved fragments.

        Evidence score:

            60% FAISS similarity
            20% engineering relevance
            15% query relevance
            5% completeness
            + optional formula bonus

        The final score is combined with explicit
        relevance gates.

        A high FAISS score alone cannot make
        irrelevant evidence acceptable.
        """

        accepted_candidates = []

        rejected = []

        # ----------------------------------------------------
        # Process every retrieved item
        # ----------------------------------------------------

        for item in results:

            if not isinstance(item, dict):
                continue

            # ------------------------------------------------
            # Extract content
            # ------------------------------------------------

            text, formula, continuation = (
                self._extract_content(item)
            )

            searchable_text = self._normalize(
                " ".join(
                    part
                    for part in (
                        text,
                        formula,
                        continuation,
                    )
                    if part
                )
            )

            # ------------------------------------------------
            # FAISS score
            # ------------------------------------------------

            score = self._safe_float(
                item.get("score", 0.0)
            )

            # ------------------------------------------------
            # Engineering relevance
            # ------------------------------------------------

            relevance = self._calculate_relevance(
                searchable_text,
                intent
            )

            # ------------------------------------------------
            # Query relevance
            # ------------------------------------------------

            query_relevance = (
                self._calculate_query_relevance(
                    searchable_text,
                    query
                )
            )

            # ------------------------------------------------
            # Formula detection
            # ------------------------------------------------

            has_formula = bool(
                formula.strip()
            )

            is_formula_context = (
                item.get("type")
                == "formula_context"
            )

            formula_bonus = 0.0

            if is_formula_context and has_formula:

                formula_bonus = 0.10

            elif has_formula:

                formula_bonus = 0.05

            # ------------------------------------------------
            # Evidence completeness
            # ------------------------------------------------

            completeness = (
                self._calculate_completeness(
                    text=text,
                    formula=formula,
                    continuation=continuation,
                    item=item,
                )
            )

            # ------------------------------------------------
            # Final evidence score
            # ------------------------------------------------

            final_score = (

                score * 0.60

                +

                relevance * 0.20

                +

                query_relevance * 0.15

                +

                completeness * 0.05

                +

                formula_bonus

            )

            final_score = min(
                final_score,
                1.0
            )

            # ------------------------------------------------
            # Direct relevance
            # ------------------------------------------------

            has_relevance = (

                relevance >= self.min_relevance

                or

                query_relevance >= self.min_query_relevance

            )

            # ------------------------------------------------
            # Query-specific strong match
            # ------------------------------------------------

            strong_query_match = (
                query_relevance >= 0.35
            )

            # ------------------------------------------------
            # FAISS gate
            # ------------------------------------------------

            faiss_ok = (
                score >= self.min_faiss_score
            )

            # ------------------------------------------------
            # Validation decision
            # ------------------------------------------------

            reasons = []

            if not faiss_ok:

                reasons.append(
                    "faiss_score_below_threshold"
                )

            if not has_relevance:

                reasons.append(
                    "no_direct_relevance"
                )

            if final_score < self.min_score:

                reasons.append(
                    "evidence_score_below_threshold"
                )

            # ------------------------------------------------
            # Special case:
            #
            # A very strong direct query match can compensate
            # for a relatively weak engineering keyword score.
            # ------------------------------------------------

            if (

                not has_relevance

                and

                strong_query_match

                and

                faiss_ok

            ):

                has_relevance = True

                reasons = [
                    reason
                    for reason in reasons
                    if reason != "no_direct_relevance"
                ]

            accepted_flag = (

                faiss_ok

                and

                has_relevance

                and

                final_score >= self.min_score

            )

            # ------------------------------------------------
            # Diagnostic metadata
            # ------------------------------------------------

            item["evidence_score"] = round(
                final_score,
                3
            )

            item["relevance_score"] = round(
                relevance,
                3
            )

            item["query_relevance_score"] = round(
                query_relevance,
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

            item["completeness_score"] = round(
                completeness,
                3
            )

            item["direct_relevance"] = (
                has_relevance
            )

            item["has_formula"] = (
                has_formula
            )

            item["validation_reasons"] = (
                ["accepted"]
                if accepted_flag
                else reasons
            )

            # ------------------------------------------------
            # Score breakdown
            # ------------------------------------------------

            item["score_breakdown"] = {

                "faiss": round(
                    score * 0.60,
                    3
                ),

                "engineering_relevance": round(
                    relevance * 0.20,
                    3
                ),

                "query_relevance": round(
                    query_relevance * 0.15,
                    3
                ),

                "completeness": round(
                    completeness * 0.05,
                    3
                ),

                "formula_bonus": round(
                    formula_bonus,
                    3
                ),

            }

            # ------------------------------------------------
            # Accept / reject
            # ------------------------------------------------

            if accepted_flag:

                accepted_candidates.append(
                    item
                )

            else:

                rejected.append(
                    item
                )

        # ====================================================
        # SORT ACCEPTED
        # ====================================================

        accepted = sorted(

            accepted_candidates,

            key=lambda x:
                x.get(
                    "evidence_score",
                    0.0
                ),

            reverse=True

        )[:top_k]

        # ====================================================
        # CONFIDENCE
        # ====================================================

        confidence = (
            self._calculate_confidence(
                accepted
            )
        )

        # ====================================================
        # SUFFICIENT EVIDENCE
        # ====================================================

        sufficient = (

            len(accepted) > 0

            and

            confidence >= self.min_confidence

        )

        # ====================================================
        # DIAGNOSTICS
        # ====================================================

        print()

        print(
            "===== EVIDENCE VALIDATION v1.4 ====="
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
                "Document:",
                item.get("document")
            )

            print(
                "Page:",
                item.get("page")
            )

            print(
                "Type:",
                item.get("type")
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
                "Query relevance:",
                item.get(
                    "query_relevance_score"
                )
            )

            print(
                "Completeness:",
                item.get(
                    "completeness_score"
                )
            )

            print(
                "Evidence:",
                item.get(
                    "evidence_score"
                )
            )

            print(
                "Formula:",
                item.get(
                    "has_formula"
                )
            )

        if rejected:

            print()

            print(
                "REJECTED DIAGNOSTICS:"
            )

            for i, item in enumerate(
                rejected,
                1
            ):

                print(
                    f"#{i}",
                    "page=",
                    item.get("page"),
                    "score=",
                    item.get("evidence_score"),
                    "reasons=",
                    item.get(
                        "validation_reasons"
                    )
                )

        print(
            "===================================="
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
    # CONTENT EXTRACTION
    # ========================================================

    def _extract_content(
        self,
        item: dict
    ):
        """
        Extract text, formula and continuation
        from different supported content formats.
        """

        content = item.get(
            "content",
            {}
        )

        text = ""
        formula = ""
        continuation = ""

        if isinstance(
            content,
            dict
        ):

            text = str(
                content.get(
                    "text",
                    ""
                )
                or ""
            )

            formula = str(
                content.get(
                    "formula",
                    ""
                )
                or ""
            )

            continuation = str(
                content.get(
                    "after",
                    ""
                )
                or ""
            )

        else:

            text = str(
                content
                or ""
            )

        # ----------------------------------------------------
        # Some retrievers may expose text at the item level.
        # ----------------------------------------------------

        if not text:

            text = str(
                item.get(
                    "text",
                    ""
                )
                or ""
            )

        return (
            text,
            formula,
            continuation
        )

    # ========================================================
    # COMPLETENESS
    # ========================================================

    def _calculate_completeness(
        self,
        text: str,
        formula: str,
        continuation: str,
        item: dict,
    ) -> float:
        """
        Estimate whether the evidence contains enough
        material to be useful downstream.

        This is not semantic truth verification.
        It only evaluates structural completeness.
        """

        score = 0.0

        if text.strip():

            score += 0.40

        if formula.strip():

            score += 0.30

        if continuation.strip():

            score += 0.20

        if item.get("page") is not None:

            score += 0.10

        return min(
            score,
            1.0
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    def _calculate_confidence(
        self,
        accepted: List[dict]
    ) -> float:
        """
        Calculate confidence from the evidence
        actually passed downstream.

        Multiple strong independent fragments
        can increase confidence slightly.

        This does NOT mean that several copies
        of the same fragment represent independent
        evidence.
        """

        if not accepted:

            return 0.0

        scores = [

            float(
                item.get(
                    "evidence_score",
                    0.0
                )
            )

            for item in accepted

        ]

        base = sum(scores) / len(scores)

        # ----------------------------------------------------
        # Diversity bonus
        # ----------------------------------------------------

        documents = {

            str(
                item.get(
                    "document",
                    ""
                )
            )

            for item in accepted

            if item.get(
                "document"
            )

        }

        pages = {

            (
                str(
                    item.get(
                        "document",
                        ""
                    )
                ),

                item.get(
                    "page"
                )

            )

            for item in accepted

        }

        diversity_bonus = 0.0

        if len(documents) >= 2:

            diversity_bonus += 0.03

        if len(pages) >= 2:

            diversity_bonus += 0.02

        confidence = min(

            base
            +
            diversity_bonus,

            1.0

        )

        return confidence

    # ========================================================
    # NORMALIZATION
    # ========================================================

    def _normalize(
        self,
        text: str
    ) -> str:
        """
        Normalize text for keyword matching.
        """

        text = str(
            text
        ).lower()

        text = text.replace(
            "ё",
            "е"
        )

        text = re.sub(
            r"[^а-яa-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ========================================================
    # QUERY TOKENS
    # ========================================================

    def _query_tokens(
        self,
        query: str
    ) -> List[str]:
        """
        Extract meaningful query tokens.
        """

        normalized = self._normalize(
            query
        )

        tokens = normalized.split()

        result = []

        for token in tokens:

            if token in self.STOP_WORDS:

                continue

            if len(token) < 3:

                continue

            result.append(
                token
            )

        return result

    # ========================================================
    # QUERY RELEVANCE
    # ========================================================

    def _calculate_query_relevance(
        self,
        text: str,
        query: str
    ) -> float:
        """
        Calculate direct relevance between
        retrieved evidence and actual query.

        Exact phrases receive stronger weight.
        """

        if not query:

            return 0.0

        normalized_text = self._normalize(
            text
        )

        normalized_query = self._normalize(
            query
        )

        # ----------------------------------------------------
        # Important engineering phrases
        # ----------------------------------------------------

        important_phrases = [

            "максимальный расчетный расход воды",

            "расчетный расход воды",

            "расчетном участке сети",

            "максимальный расход воды",

            "расчетный участок сети",

            "гидравлический расчет",

            "внутренняя система водоснабжения",

            "внутренние системы водоснабжения",

        ]

        phrase_hits = 0

        for phrase in important_phrases:

            if phrase in normalized_query:

                if phrase in normalized_text:

                    phrase_hits += 1

        # ----------------------------------------------------
        # Token matching
        # ----------------------------------------------------

        tokens = self._query_tokens(
            query
        )

        if not tokens:

            return 0.0

        hits = 0

        for token in tokens:

            if token in normalized_text:

                hits += 1

                continue

            # ------------------------------------------------
            # Russian word-family approximation.
            # ------------------------------------------------

            if len(token) >= 6:

                stem = token[:6]

                if stem in normalized_text:

                    hits += 1

        token_score = (

            hits
            /
            len(tokens)

        )

        # ----------------------------------------------------
        # Phrase score
        # ----------------------------------------------------

        phrase_score = min(

            phrase_hits * 0.35,

            0.70

        )

        final = (

            token_score * 0.30

            +

            phrase_score

        )

        return min(
            final,
            1.0
        )

    # ========================================================
    # ENGINEERING RELEVANCE
    # ========================================================

    def _calculate_relevance(
        self,
        text: str,
        intent
    ) -> float:
        """
        Calculate engineering relevance.

        System relevance contributes up to 0.55.
        Topic relevance contributes up to 0.45.

        Intent keywords provide an additional
        limited signal.
        """

        if intent is None:

            return 0.5

        score = 0.0

        # ====================================================
        # SYSTEM MATCH
        # ====================================================

        system = getattr(
            intent,
            "system",
            ""
        )

        system_words = (
            self.DOMAIN_KEYWORDS.get(
                system,
                []
            )
        )

        system_hits = sum(

            1

            for word in system_words

            if self._normalize(word) in text

        )

        if system_hits:

            score += min(

                system_hits * 0.15,

                0.55

            )

        # ====================================================
        # TOPIC MATCH
        # ====================================================

        topic = getattr(
            intent,
            "topic",
            ""
        )

        topic_words = (
            self.TOPIC_KEYWORDS.get(
                topic,
                []
            )
        )

        topic_hits = sum(

            1

            for word in topic_words

            if self._normalize(word) in text

        )

        if topic_hits:

            score += min(

                topic_hits * 0.10,

                0.45

            )

        # ====================================================
        # INTENT KEYWORDS
        # ====================================================

        intent_keywords = getattr(
            intent,
            "keywords",
            []
        )

        keyword_hits = 0

        for word in intent_keywords:

            normalized_word = (
                self._normalize(word)
            )

            if normalized_word and (
                normalized_word in text
            ):

                keyword_hits += 1

        if keyword_hits:

            score += min(

                keyword_hits * 0.10,

                0.20

            )

        return min(
            score,
            1.0
        )

    # ========================================================
    # SAFE FLOAT
    # ========================================================

    def _safe_float(
        self,
        value
    ) -> float:
        """
        Safely convert score to float.
        """

        try:

            value = float(
                value
            )

        except (
            TypeError,
            ValueError
        ):

            return 0.0

        if value < 0:

            return 0.0

        return min(
            value,
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
        "Evidence Validator v1.4"
    )

    print("=" * 70)

    sample = [

        {
            "page": 27,

            "score": 0.81,

            "type": "text",

            "document":
                "SP_30.13330.2020",

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

            "document":
                "SP_30.13330.2020",

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

        sample,

        query=(
            "Как определяется максимальный "
            "расчетный расход воды "
            "на расчетном участке сети?"
        )

    )

    print()

    print(
        "confidence:",
        result.confidence
    )

    print(
        "accepted:",
        len(
            result.accepted
        )
    )

    print(
        "rejected:",
        len(
            result.rejected
        )
    )


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":

    demo()
    