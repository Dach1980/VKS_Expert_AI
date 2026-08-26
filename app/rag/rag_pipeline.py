"""
VKS Expert AI
RAG Pipeline v1.3

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
Retriever
    |
    v
FAISS Search
    |
    v
Evidence Validator
    |
    v
Context Builder
    |
    v
LM Studio
    |
    v
Technical Answer
"""


from app.rag.retriever import Retriever
from app.rag.context_builder import ContextBuilder
from app.rag.query_classifier import QueryClassifier
from app.rag.evidence_validator import EvidenceValidator

from app.llm.lmstudio_client import LMStudioClient



class RAGPipeline:
    """
    Main VKS Expert AI RAG pipeline.
    """


    def __init__(self):

        print("Loading components...")


        self.classifier = QueryClassifier()

        self.retriever = Retriever()

        self.validator = EvidenceValidator()

        self.context_builder = ContextBuilder()


        self.llm = LMStudioClient(
            model="qwen/qwen3.5-9b-mtp"
        )


        print("Pipeline ready")



    def ask(
        self,
        question: str,
        top_k: int = 5
    ):


        print("\nQUESTION:")
        print(question)



        # --------------------------------------------------
        # 1. Query classification
        # --------------------------------------------------

        intent = (
            self.classifier.classify(
                question
            )
        )


        print("\nINTENT:")
        print(intent)



        # --------------------------------------------------
        # 2. Engineering query enrichment
        # --------------------------------------------------

        enhanced_query = f"""

Инженерная область:
{intent.discipline}

Система:
{intent.system}

Тема:
{intent.topic}

Ключевые слова:
{intent.keywords}

Запрос:
{question}

"""



        # --------------------------------------------------
        # 3. Retrieval
        # --------------------------------------------------

        results = (
            self.retriever.search(
                enhanced_query,
                top_k=top_k
            )
        )



        # --------------------------------------------------
        # 4. Evidence validation
        # --------------------------------------------------

        evidence = (
            self.validator.validate(
                question,
                results
            )
        )


        print("\nEVIDENCE:")

        print(
            "confidence=",
            evidence.confidence
        )

        print(
            "accepted=",
            len(evidence.accepted)
        )

        print(
            "rejected=",
            len(evidence.rejected)
        )



        validated_results = (
            evidence.accepted
        )



        # --------------------------------------------------
        # 5. Context building
        # --------------------------------------------------

        context = (
            self.context_builder.build(
                query=question,
                results=validated_results,
            )
        )



        # --------------------------------------------------
        # 6. Engineering prompt
        # --------------------------------------------------

        system_prompt = """

Ты являешься инженерным AI-ассистентом
VKS Expert AI.


Правила ответа:

1. Отвечай только на русском языке.

2. Используй только предоставленный
нормативный контекст.

3. Не придумывай требований,
формул и пунктов СП.

4. Если информации недостаточно,
сообщи об этом.

5. Используй инженерную терминологию ВК.

6. Указывай источник ответа.


Формат ответа:

Краткий вывод

Расчет / требования

Источник СП

"""



        if not evidence.sufficient:


            system_prompt += """

Внимание:
Нормативного контекста недостаточно.
Не делай предположений.
"""




        user_prompt = f"""

Вопрос:

{question}


Проверенный нормативный контекст:

{context}


Уровень уверенности Evidence:

{evidence.confidence}

"""



        # --------------------------------------------------
        # 7. LLM generation
        # --------------------------------------------------

        answer = (
            self.llm.chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=2048,
                enable_thinking=False
            )
        )



        return {

            "question": question,

            "intent": intent,

            "answer": answer,

            "sources": validated_results,

            "evidence_confidence":
                evidence.confidence,

            "evidence_sufficient":
                evidence.sufficient,

        }




def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "RAG Pipeline v1.3"
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

    print("ANSWER:")

    print(
        result["answer"]
    )


    print("\n")

    print(
        "EVIDENCE CONFIDENCE:",
        result["evidence_confidence"]
    )


    print(
        "SOURCES:"
    )


    for item in result["sources"]:

        print(
            f"""
{item['document']}
page={item['page']}
score={item['score']}
"""
        )



if __name__ == "__main__":

    demo()
    