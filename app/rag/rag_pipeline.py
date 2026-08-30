
"""
VKS Expert AI
RAG Pipeline v1.5

Engineering RAG pipeline
with evidence validation.

Architecture:

Question
    |
    v
Query Classifier
    |
    v
Engineering Intent
    |
    v
Query Enrichment
    |
    v
Retriever
    |
    v
FAISS Search
    |
    v
Evidence Validator
    |
    +---- accepted evidence
    |
    +---- rejected evidence
    |
    v
Context Builder
    |
    v
Engineering Prompt
    |
    v
LM Studio
    |
    v
Technical Answer


v1.5 changes:

- EvidenceValidator v1.4 integration.
- Original Retriever results are passed directly
  to EvidenceValidator.
- Evidence diagnostics are preserved.
- Formula / continuation metadata is preserved.
- Context is built only from validated evidence.
- Explicit insufficient-evidence mode.
- Improved source metadata returned to caller.
- Added validation diagnostics to pipeline result.
- Added context-empty protection.
- LLM is not allowed to compensate for missing evidence.
"""


from app.rag.retriever import Retriever
from app.rag.context_builder import ContextBuilder
from app.rag.query_classifier import QueryClassifier
from app.rag.evidence_validator import EvidenceValidator

from app.llm.lmstudio_client import LMStudioClient


class RAGPipeline:
    """
    Main VKS Expert AI RAG pipeline.

    v1.5
    """

    def __init__(self):

        print("Loading components...")

        # --------------------------------------------------
        # Query classification
        # --------------------------------------------------

        self.classifier = QueryClassifier()

        # --------------------------------------------------
        # Retriever
        # --------------------------------------------------

        self.retriever = Retriever()

        # --------------------------------------------------
        # Evidence validation
        # --------------------------------------------------

        self.validator = EvidenceValidator()

        # --------------------------------------------------
        # Context builder
        # --------------------------------------------------

        self.context_builder = ContextBuilder()

        # --------------------------------------------------
        # Local LLM
        # --------------------------------------------------

        self.llm = LMStudioClient(
            model="qwen/qwen3.5-9b-mtp"
        )

        print("Pipeline ready")

    # ========================================================
    # ASK
    # ========================================================

    def ask(
        self,
        question: str,
        top_k: int = 5
    ):
        """
        Execute complete engineering RAG pipeline.
        """

        # ====================================================
        # 0. Validate question
        # ====================================================

        question = str(
            question
            or ""
        ).strip()

        if not question:

            return {

                "question": "",

                "intent": None,

                "answer": (
                    "Вопрос не задан."
                ),

                "sources": [],

                "evidence_confidence": 0.0,

                "evidence_sufficient": False,

                "retrieved_count": 0,

                "accepted_count": 0,

                "rejected_count": 0,

            }

        print("\nQUESTION:")
        print(question)

        # ====================================================
        # 1. Query classification
        # ====================================================

        intent = (
            self.classifier.classify(
                question
            )
        )

        print("\nINTENT:")
        print(intent)

        # ====================================================
        # 2. Engineering query enrichment
        # ====================================================

        enhanced_query = self._build_enhanced_query(
            question,
            intent
        )

        print(
            "\n===== ENHANCED QUERY ====="
        )

        print(
            enhanced_query
        )

        print(
            "=========================="
        )

        # ====================================================
        # 3. Retrieval
        # ====================================================

        results = (
            self.retriever.search(
                enhanced_query,
                top_k=top_k
            )
        )

        if results is None:

            results = []

        print(
            "\n===== RETRIEVER RESULTS ====="
        )

        print(
            "Retrieved:",
            len(results)
        )

        for i, result in enumerate(
            results,
            1
        ):

            self._print_retriever_result(
                i,
                result
            )

        print(
            "=============================="
        )

        # ====================================================
        # 4. Evidence validation
        # ====================================================

        evidence = (
            self.validator.validate(

                results,

                intent=intent,

                query=question,

                top_k=top_k

            )
        )

        print(
            "\n===== EVIDENCE RESULT ====="
        )

        print(
            "Confidence:",
            evidence.confidence
        )

        print(
            "Sufficient:",
            evidence.sufficient
        )

        print(
            "Accepted:",
            len(
                evidence.accepted
            )
        )

        print(
            "Rejected:",
            len(
                evidence.rejected
            )
        )

        print(
            "==========================="
        )

        # ====================================================
        # 5. Validated evidence
        # ====================================================

        validated_results = (
            self._prepare_validated_results(
                evidence.accepted
            )
        )

        # ====================================================
        # 6. Context building
        # ====================================================

        context = ""

        if validated_results:

            context = (
                self.context_builder.build(
                    validated_results
                )
            )

        context = str(
            context
            or ""
        ).strip()

        # ----------------------------------------------------
        # Context protection
        # ----------------------------------------------------

        if not context:

            print(
                "\nWARNING:"
                " validated evidence produced"
                " an empty context."
            )

        # ====================================================
        # 7. Engineering system prompt
        # ====================================================

        system_prompt = self._build_system_prompt(
            evidence
        )

        # ====================================================
        # 8. User prompt
        # ====================================================

        user_prompt = self._build_user_prompt(

            question=question,

            context=context,

            confidence=evidence.confidence,

            sufficient=evidence.sufficient

        )

        # ====================================================
        # 9. Diagnostics before LLM
        # ====================================================

        print(
            "\n===== CONTEXT SENT TO LLM ====="
        )

        if context:

            print(
                context
            )

        else:

            print(
                "[EMPTY VERIFIED CONTEXT]"
            )

        print(
            "================================"
        )

        # ====================================================
        # 10. LLM generation
        # ====================================================

        answer = (
            self.llm.chat(

                prompt=user_prompt,

                system_prompt=system_prompt,

                temperature=0.1,

                max_tokens=2048,

                enable_thinking=False

            )
        )

        # ====================================================
        # 11. Return structured result
        # ====================================================

        return {

            "question":
                question,

            "intent":
                intent,

            "answer":
                answer,

            "sources":
                validated_results,

            "evidence_confidence":
                evidence.confidence,

            "evidence_sufficient":
                evidence.sufficient,

            "retrieved_count":
                len(results),

            "accepted_count":
                len(
                    evidence.accepted
                ),

            "rejected_count":
                len(
                    evidence.rejected
                ),

            "evidence_rejected":
                evidence.rejected,

            "context":
                context,

        }

    # ========================================================
    # ENHANCED QUERY
    # ========================================================

    def _build_enhanced_query(
        self,
        question: str,
        intent
    ) -> str:
        """
        Build engineering-aware retrieval query.
        """

        discipline = getattr(
            intent,
            "discipline",
            ""
        )

        system = getattr(
            intent,
            "system",
            ""
        )

        topic = getattr(
            intent,
            "topic",
            ""
        )

        keywords = getattr(
            intent,
            "keywords",
            []
        )

        return f"""

Инженерная область:
{discipline}

Система:
{system}

Тема:
{topic}

Ключевые слова:
{keywords}

Запрос:
{question}

""".strip()

    # ========================================================
    # VALIDATED RESULTS
    # ========================================================

    def _prepare_validated_results(
        self,
        accepted
    ):
        """
        Prepare validated evidence for ContextBuilder.

        Important:
        preserve original content and metadata.

        Evidence diagnostics are also preserved,
        so they remain available to the caller.
        """

        validated = []

        for item in accepted:

            if not isinstance(
                item,
                dict
            ):

                continue

            result = dict(
                item
            )

            # ------------------------------------------------
            # Ensure ContextBuilder receives expected fields.
            # ------------------------------------------------

            result.setdefault(
                "document",
                "unknown"
            )

            result.setdefault(
                "page",
                0
            )

            result.setdefault(
                "type",
                "text"
            )

            result.setdefault(
                "content",
                {}
            )

            result.setdefault(
                "score",
                result.get(
                    "faiss_score",
                    0.0
                )
            )

            validated.append(
                result
            )

        return validated

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    def _build_system_prompt(
        self,
        evidence
    ):
        """
        Build strict engineering system prompt.
        """

        system_prompt = """

Ты являешься инженерным AI-ассистентом
VKS Expert AI.

Твоя задача — отвечать на вопросы
по проектно-строительной документации
на основании проверенного нормативного
контекста.

Правила ответа:

1. Отвечай только на русском языке.

2. Используй только предоставленный
проверенный нормативный контекст.

3. Не придумывай требований,
формул, коэффициентов, обозначений,
пунктов СП или других нормативных данных.

4. Если информации недостаточно,
прямо сообщи об этом.

5. Используй инженерную терминологию ВК.

6. Указывай источник ответа,
если он присутствует в контексте.

7. КРИТИЧЕСКОЕ ПРАВИЛО ДЛЯ ФОРМУЛ:

Если в нормативном контексте
присутствует расчетная формула,
воспроизводи ее ТОЧНО в том виде,
в котором она приведена в контексте.

Не сокращай формулу.

Не упрощай формулу.

Не удаляй коэффициенты.

Не заменяй переменные.

Не меняй числовые множители.

Не восстанавливай отсутствующие
части формулы самостоятельно.

Если формула представлена несколькими
частями, учитывай все предоставленные
части формулы.

Если формулу невозможно полностью
восстановить из предоставленного
контекста, сообщи об этом вместо того,
чтобы придумывать недостающую часть.

8. Нельзя заменять нормативную формулу
собственной инженерной интерпретацией.

9. Если нормативный контекст содержит
несколько фрагментов, используй только
те фрагменты, которые непосредственно
относятся к вопросу.

10. Нерелевантные сведения не используй
для формирования ответа.

11. Не используй собственные знания
взамен отсутствующих нормативных данных.

12. Не считай высокий FAISS score
доказательством достоверности сам по себе.

13. Проверенный контекст является
единственным нормативным источником
для данного ответа.

Формат ответа:

Краткий вывод

Расчет / требования

Источник СП

"""

        # ----------------------------------------------------
        # Insufficient evidence mode
        # ----------------------------------------------------

        if not evidence.sufficient:

            system_prompt += """

КРИТИЧЕСКИЙ РЕЖИМ:

Проверенного нормативного контекста
недостаточно для надежного ответа.

Не делай предположений.

Не достраивай отсутствующие требования.

Не восстанавливай отсутствующие
формулы.

Не придумывай номера пунктов СП.

Если вопрос требует конкретного
нормативного значения, формулы,
коэффициента или требования, а оно
отсутствует в проверенном контексте,
так и сообщи пользователю.

Можно объяснить, какой именно информации
не хватает для надежного ответа.

"""

        return system_prompt.strip()

    # ========================================================
    # USER PROMPT
    # ========================================================

    def _build_user_prompt(
        self,
        question: str,
        context: str,
        confidence: float,
        sufficient: bool
    ) -> str:
        """
        Build user prompt for local LLM.
        """

        if context:

            verified_context = context

        else:

            verified_context = (
                "[Проверенный нормативный "
                "контекст отсутствует]"
            )

        return f"""

Вопрос:

{question}


Проверенный нормативный контекст:

{verified_context}


Evidence confidence:

{confidence}


Evidence sufficient:

{sufficient}

Ответ дай только на основании
проверенного нормативного контекста.

"""

    # ========================================================
    # RETRIEVER DIAGNOSTICS
    # ========================================================

    def _print_retriever_result(
        self,
        index: int,
        result
    ):
        """
        Print compact retrieval diagnostics.
        """

        if not isinstance(
            result,
            dict
        ):

            print(
                f"#{index}: invalid result"
            )

            return

        print()

        print(
            f"#{index}"
        )

        print(
            "PAGE:",
            result.get(
                "page"
            )
        )

        print(
            "DOCUMENT:",
            result.get(
                "document"
            )
        )

        print(
            "TYPE:",
            result.get(
                "type"
            )
        )

        print(
            "SCORE:",
            result.get(
                "score"
            )
        )

        content = result.get(
            "content",
            {}
        )

        if isinstance(
            content,
            dict
        ):

            text = content.get(
                "text",
                ""
            )

            formula = content.get(
                "formula",
                ""
            )

            after = content.get(
                "after",
                ""
            )

            if text:

                print(
                    "TEXT:",
                    str(text)[:250]
                )

            if formula:

                print(
                    "FORMULA:",
                    str(formula)[:250]
                )

            if after:

                print(
                    "AFTER:",
                    str(after)[:250]
                )

        else:

            print(
                "CONTENT:",
                str(content)[:300]
            )

        print(
            "-" * 50
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
        "RAG Pipeline v1.5"
    )

    print("=" * 70)

    pipeline = RAGPipeline()

    question = """

Как определяется максимальный
расчетный расход воды
на расчетном участке сети?

"""

    result = (
        pipeline.ask(
            question
        )
    )

    print("\n")
    print("=" * 70)

    print(
        "ANSWER:"
    )

    print(
        result["answer"]
    )

    print("\n")

    print(
        "EVIDENCE CONFIDENCE:",
        result[
            "evidence_confidence"
        ]
    )

    print(
        "EVIDENCE SUFFICIENT:",
        result[
            "evidence_sufficient"
        ]
    )

    print(
        "RETRIEVED:",
        result[
            "retrieved_count"
        ]
    )

    print(
        "ACCEPTED:",
        result[
            "accepted_count"
        ]
    )

    print(
        "REJECTED:",
        result[
            "rejected_count"
        ]
    )

    print(
        "\nSOURCES:"
    )

    for item in result["sources"]:

        print(
            f"""
{item.get('document')}
page={item.get('page')}
faiss={item.get('faiss_score')}
evidence={item.get('evidence_score')}
relevance={item.get('relevance_score')}
query_relevance={item.get('query_relevance_score')}
completeness={item.get('completeness_score')}
"""
        )

    print(
        "=" * 70
    )


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":

    demo()
