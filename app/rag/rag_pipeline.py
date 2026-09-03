"""
VKS Expert AI
RAG Pipeline v1.7

Engineering RAG pipeline with evidence validation.
"""

from time import perf_counter

from app.rag.retriever import Retriever
from app.rag.context_builder import ContextBuilder
from app.rag.query_classifier import QueryClassifier
from app.rag.evidence_validator import EvidenceValidator
from app.llm.lmstudio_client import LMStudioClient


class RAGPipeline:
    """Main VKS Expert AI RAG pipeline."""

    def __init__(self):
        print("Loading components...")
        self.classifier = QueryClassifier()
        self.retriever = Retriever()
        self.validator = EvidenceValidator()
        self.context_builder = ContextBuilder()
        # Do not hard-code a model id: LM Studio may expose a different
        # installed Qwen/chat model. LMStudioClient selects a compatible model
        # from /v1/models when the first chat request is made.
        self.llm = LMStudioClient()
        print("Pipeline ready")

    def ask(self, question: str, top_k: int = 5):
        total_started = perf_counter()
        timings = {}
        question = str(question or "").strip()
        if not question:
            return {
                "question": "", "intent": None, "answer": "Вопрос не задан.",
                "sources": [], "evidence_confidence": 0.0,
                "evidence_sufficient": False, "retrieved_count": 0,
                "accepted_count": 0, "rejected_count": 0,
            }

        print("\nQUESTION:")
        print(question)

        started = perf_counter()
        intent = self.classifier.classify(question)
        timings["classifier"] = perf_counter() - started
        print("\nINTENT:")
        print(intent)
        enhanced_query = self._build_enhanced_query(question, intent)
        print("\n===== ENHANCED QUERY =====")
        print(enhanced_query)
        print("==========================")

        started = perf_counter()
        results = self.retriever.search(enhanced_query, top_k=top_k) or []
        timings["retrieval"] = perf_counter() - started
        print("\n===== RETRIEVER RESULTS =====")
        print("Retrieved:", len(results))
        for i, result in enumerate(results, 1):
            self._print_retriever_result(i, result)
        print("==============================")

        started = perf_counter()
        evidence = self.validator.validate(results, intent=intent, query=question, top_k=top_k)
        timings["validation"] = perf_counter() - started
        print("\n===== EVIDENCE RESULT =====")
        print("Confidence:", evidence.confidence)
        print("Sufficient:", evidence.sufficient)
        print("Accepted:", len(evidence.accepted))
        print("Rejected:", len(evidence.rejected))
        print("===========================")

        validated_results = self._prepare_validated_results(evidence.accepted)
        started = perf_counter()
        context = ""
        if validated_results:
            context = str(self.context_builder.build(validated_results) or "").strip()
        timings["context"] = perf_counter() - started
        if not context:
            print("\nWARNING: validated evidence produced an empty context.")

        version_label = self._current_version_label()
        system_prompt = self._build_system_prompt(evidence, version_label=version_label)
        user_prompt = self._build_user_prompt(
            question=question, context=context,
            confidence=evidence.confidence, sufficient=evidence.sufficient,
            version_label=version_label,
        )
        print("\n===== CONTEXT SENT TO LLM =====")
        print(context if context else "[EMPTY VERIFIED CONTEXT]")
        print("================================")

        started = perf_counter()
        answer = self.llm.chat(
            prompt=user_prompt, system_prompt=system_prompt,
            temperature=0.1, max_tokens=2048, enable_thinking=False,
        )
        timings["llm"] = perf_counter() - started
        timings["total"] = perf_counter() - total_started
        print("\n===== RAG TIMING =====")
        for stage in ("classifier", "retrieval", "validation", "context", "llm", "total"):
            print(f"{stage}: {timings[stage]:.3f}s")
        print("======================")

        return {
            "question": question, "intent": intent, "answer": answer,
            "sources": validated_results,
            "evidence_confidence": evidence.confidence,
            "evidence_sufficient": evidence.sufficient,
            "retrieved_count": len(results),
            "accepted_count": len(evidence.accepted),
            "rejected_count": len(evidence.rejected),
            "evidence_rejected": evidence.rejected,
            "context": context,
            "timings": timings,
            "normative_version": version_label,
        }

    def _current_version_label(self) -> str:
        """Return the authoritative label already resolved by Retriever."""
        label = str(getattr(self.retriever, "version_label", "") or "").strip()
        if label:
            document = str(getattr(self.retriever, "document_id", "") or "").strip()
            if " — " in label or not document:
                return label
            return f"{document} — {label}"
        return str(getattr(self.retriever, "document_id", "") or "")

    def _build_enhanced_query(self, question: str, intent) -> str:
        discipline = getattr(intent, "discipline", "")
        system = getattr(intent, "system", "")
        topic = getattr(intent, "topic", "")
        keywords = getattr(intent, "keywords", [])
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

    def _prepare_validated_results(self, accepted):
        validated = []
        for item in accepted:
            if not isinstance(item, dict):
                continue
            result = dict(item)
            result.setdefault("document", "unknown")
            result.setdefault("page", 0)
            result.setdefault("type", "text")
            result.setdefault("content", {})
            result.setdefault("score", result.get("faiss_score", 0.0))
            # Retriever is the authoritative source for the selected version.
            # Preserve a valid per-source label instead of replacing it with a
            # registry-only fallback that can lose amendment metadata.
            result["version_label"] = result.get("version_label") or self._current_version_label()
            document = str(result.get("document") or self.retriever.document_id)
            if "document_display_name" not in result or not result.get("document_display_name"):
                result["document_display_name"] = f"{document} — {result['version_label']}"
            validated.append(result)
        return validated

    def _build_system_prompt(self, evidence, version_label: str = ""):
        system_prompt = """
Ты являешься инженерным AI-ассистентом VKS Expert AI.

Отвечай только на русском языке и только на основании предоставленного
проверенного нормативного контекста. Не придумывай требования, формулы,
коэффициенты или номера пунктов СП. Если информация подтверждается найденным
фрагментом, обязательно используй это подтверждение в ответе.

Критически важно: если в проверенном контексте есть явная нормативная
формулировка вроде «следует принимать», «должен», «не менее», «не допускается»
или аналогичная, это является прямым нормативным требованием и его НЕЛЬЗЯ
заменять выводом «конкретное требование не найдено». Сначала извлеки такие
прямые требования из контекста и ответь по ним, даже если другие найденные
фрагменты являются общими или косвенными.

Особенно для вопросов о диаметрах труб: если контекст содержит слова
«диаметр/диаметры» вместе с нормативной формулировкой и числовым значением,
обязательно укажи это значение, область его применения и номер пункта, если
номер пункта присутствует в самом фрагменте. Не обобщай частное требование
на всю систему, если оно относится только к вводам, отдельным участкам или
конкретным приборам.

Отсутствие нужного требования в предоставленном контексте НЕ доказывает,
что такого требования нет во всём нормативном документе. Никогда не делай
вывод «в документе отсутствует», «СП не содержит» или аналогичное отрицательное
утверждение только потому, что часть релевантных фрагментов не была найдена.
Если прямого подтверждения действительно нет, формулируй вывод строго как:
«В проверенном нормативном контексте конкретное требование не найдено» и,
если это уместно, укажи, что для подтверждения необходимо расширить поиск.

Формулы из нормативного контекста воспроизводи точно: не сокращай, не
упрощай, не удаляй коэффициенты и не заменяй переменные.

Формат ответа:
Краткий вывод

Расчет / требования

Источник СП
"""
        if version_label:
            system_prompt += f"\n\nТекущая выбранная версия нормативного документа: {version_label}."
        if not evidence.sufficient:
            system_prompt += """

Проверенного нормативного контекста недостаточно. Не делай предположений,
не придумывай номера пунктов и нормативные значения. Укажи, какой информации
не хватает для надежного ответа. Не утверждай отсутствие требования во всём
документе: можно утверждать только то, что подтверждается найденным контекстом.
"""
        return system_prompt.strip()

    def _build_user_prompt(self, question: str, context: str, confidence: float, sufficient: bool, version_label: str = "") -> str:
        verified_context = context or "[Проверенный нормативный контекст отсутствует]"
        return f"""
Вопрос:
{question}

Проверенная версия нормативного документа:
{version_label or '[не определена]'}

Проверенный нормативный контекст:
{verified_context}

Evidence confidence:
{confidence}

Evidence sufficient:
{sufficient}

Правило ответа: сначала найди в контексте прямые нормативные формулировки
(например, «следует принимать», «не менее», «должен»). Если такая формулировка
есть, обязательно отрази её в ответе с числовым значением и номером пункта,
если они присутствуют. Не говори, что требование не найдено, когда оно прямо
приведено в проверенном контексте.

Ответ дай только на основании проверенного нормативного контекста.
Не интерпретируй отсутствие фрагмента как доказательство отсутствия требования
во всём нормативном документе.
"""

    def _print_retriever_result(self, index: int, result):
        if not isinstance(result, dict):
            print(f"#{index}: invalid result")
            return
        print(f"\n#{index}")
        print("PAGE:", result.get("page"))
        print("DOCUMENT:", result.get("document"))
        print("VERSION:", result.get("version"))
        print("VERSION LABEL:", result.get("version_label"))
        print("TYPE:", result.get("type"))
        print("SCORE:", result.get("score"))
        content = result.get("content", {})
        if isinstance(content, dict):
            for key in ("text", "formula", "after"):
                value = content.get(key, "")
                if value:
                    print(f"{key.upper()}:", str(value)[:250])
        else:
            print("CONTENT:", str(content)[:300])
        print("-" * 50)


def demo():
    pipeline = RAGPipeline()
    result = pipeline.ask("Как определяется максимальный расчетный расход воды на расчетном участке сети?")
    print("\nANSWER:\n", result["answer"])


if __name__ == "__main__":
    demo()
