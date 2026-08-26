"""
VKS Expert AI

RAG Pipeline v1.1

Purpose:
Engineering RAG pipeline.

Flow:

User Question
        |
        v
Retriever
        |
        v
Relevant normative pages
        |
        v
Context Builder
        |
        v
LM Studio Client
        |
        v
Engineering answer
"""


from app.rag.retriever import Retriever
from app.rag.context_builder import ContextBuilder
from app.llm.lmstudio_client import LMStudioClient



SYSTEM_PROMPT = """
Ты являешься инженерным AI-ассистентом
VKS Expert AI.

Ты работаешь с нормативной документацией
в области проектирования инженерных систем.

Правила ответа:

1. Отвечай только на основании
предоставленного нормативного контекста.

2. Не используй знания из памяти модели,
если они отсутствуют в контексте.

3. Не показывай внутренние рассуждения.

4. Используй профессиональную инженерную
терминологию.

5. Если информации недостаточно,
укажи это явно.

6. Не объединяй требования разных систем.
Например:
- водоснабжение;
- канализация;
- внутренний водосток;
- пожарный водопровод

рассматривай отдельно.

7. В конце ответа обязательно укажи:

Источник:
документ
страницы
"""


class RAGPipeline:


    def __init__(

        self,

        retriever=None,

        context_builder=None,

        llm_client=None,

    ):


        self.retriever = (

            retriever

            if retriever

            else Retriever()

        )


        self.context_builder = (

            context_builder

            if context_builder

            else ContextBuilder()

        )


        self.llm = (

            llm_client

            if llm_client

            else LMStudioClient(
                model="qwen/qwen3.5-9b"
            )

        )



    def ask(

        self,

        question: str,

        top_k: int = 3,

    ):


        #
        # 1. Search knowledge base
        #

        results = self.retriever.search(

            question,

            top_k=top_k

        )



        #
        # 2. Prepare normative context
        #

        context = self.context_builder.build(

            question,

            results

        )



        #
        # 3. Create LLM prompt
        #

        prompt = f"""

Нормативный контекст:

====================

{context}

====================


Вопрос инженера:

{question}


Подготовь технический ответ.

Используй только приведённые
нормативные данные.

"""


        #
        # 4. Generate answer
        #

        answer = self.llm.chat(

            prompt,

            system_prompt=SYSTEM_PROMPT,

            temperature=0.1,

            max_tokens=2048,

            enable_thinking=False,

        )



        return {

            "question": question,

            "answer": answer,

            "context": context,

            "sources": results,

        }



def print_sources(results):


    print("\nSOURCES:")

    print("-" * 40)


    for item in results:


        page = item.get(
            "page",
            "?"
        )


        score = item.get(
            "score",
            0
        )


        print(

            f"СП 30.13330.2020 | "
            f"page={page} | "
            f"score={score:.4f}"

        )



def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "RAG Pipeline v1.1"
    )

    print("=" * 70)



    pipeline = RAGPipeline()



    question = """

Как определяется максимальный
расчетный расход воды
на расчетном участке сети?

"""



    print(
        "\nQUESTION:"
    )

    print(question)



    result = pipeline.ask(

        question,

        top_k=3

    )



    print(
        "\nANSWER:"
    )


    print(
        result["answer"]
    )



    print_sources(

        result["sources"]

    )



if __name__ == "__main__":

    demo()
    