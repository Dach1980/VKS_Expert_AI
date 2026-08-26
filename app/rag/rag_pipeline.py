"""
VKS Expert AI
RAG Pipeline v1.2

Engineering RAG pipeline.

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
Context Builder
    |
    v
LM Studio
    |
    v
Technical Answer
"""


from pathlib import Path


from app.rag.retriever import Retriever
from app.rag.context_builder import ContextBuilder
from app.rag.query_classifier import QueryClassifier

from app.llm.lmstudio_client import LMStudioClient



class RAGPipeline:
    """
    Main VKS Expert AI RAG pipeline.
    """


    def __init__(self):

        print("Loading components...")

        self.classifier = QueryClassifier()

        self.retriever = Retriever()

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
        # 2. Enhanced query
        # --------------------------------------------------

        enhanced_query = f"""

Инженерная область:
{intent.discipline}

Система:
{intent.system}

Тема:
{intent.topic}


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
        # 4. Context building
        # --------------------------------------------------

        context = (
            self.context_builder.build(
                results
            )
        )



        # --------------------------------------------------
        # 5. Prompt
        # --------------------------------------------------

        system_prompt = """

Ты являешься инженерным AI-ассистентом
VKS Expert AI.


Правила ответа:

1. Отвечай только на русском языке.
2. Используй только предоставленный нормативный контекст.
3. Не придумывай требований отсутствующих в СП.
4. Используй инженерную терминологию ВК.
5. Указывай источник ответа.
6. Если данных недостаточно — сообщи об этом.


Формат:

Краткий вывод

Расчет / требования

Источник СП

"""


        user_prompt = f"""

Вопрос:

{question}


Нормативный контекст:

{context}

"""


        # --------------------------------------------------
        # 6. LLM
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

            "sources": results

        }




def demo():


    print("=" * 70)
    print("VKS Expert AI")
    print("RAG Pipeline v1.2")
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

    print(result["answer"])



    print("\n")
    print("SOURCES:")
    

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
