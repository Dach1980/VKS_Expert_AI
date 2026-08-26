"""
VKS Expert AI
LM Studio Client v1.5

Purpose:
Communication with LM Studio local server.

Features:
- OpenAI compatible API
- Qwen3.5 support
- thinking mode control
- reasoning diagnostics
- RAG ready
"""


from typing import Optional
import requests



DEFAULT_SYSTEM_PROMPT = """
Ты являешься инженерным AI-ассистентом VKS Expert AI.

Правила ответа:

1. Отвечай только на русском языке.
2. Не показывай внутренние рассуждения модели.
3. Не выводи chain-of-thought.
4. Формируй только итоговый технический ответ.
5. Используй инженерную и нормативную терминологию.
"""



class LMStudioClient:


    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: Optional[str] = None,
        timeout: int = 300,
        debug: bool = False,
    ):

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.debug = debug



    def get_models(self):

        response = requests.get(
            f"{self.base_url}/models",
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()



    def chat(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
    ):


        if self.model is None:

            models = self.get_models()

            if not models.get("data"):

                raise RuntimeError(
                    "No models available"
                )


            self.model = (
                models["data"][0]["id"]
            )



        messages = []


        if system_prompt:

            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )



        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )



        payload = {

            "model": self.model,

            "messages": messages,

            "temperature": temperature,

            "max_tokens": max_tokens,


            #
            # LM Studio engine parameters
            #
            "extra_body":
            {
                "chat_template_kwargs":
                {
                    "enable_thinking": enable_thinking
                }
            }

        }



        if self.debug:

            print("\nREQUEST:")
            print(payload)



        response = requests.post(

            f"{self.base_url}/chat/completions",

            json=payload,

            timeout=self.timeout,

        )


        response.raise_for_status()


        data = response.json()



        if self.debug:

            print("\nRAW RESPONSE:")

            print(data)



        message = (
            data["choices"][0]
            ["message"]
        )



        content = (
            message.get(
                "content",
                ""
            )
            or ""
        )



        if content.strip():

            return content.strip()



        #
        # Диагностика Qwen thinking
        #

        reasoning = (
            message.get(
                "reasoning_content",
                ""
            )
            or ""
        )


        if self.debug:

            print(
                "\nWARNING:"
            )

            print(
                "content is empty"
            )


            if reasoning:

                print(
                    "reasoning_content detected"
                )


            try:

                print(
                    "reasoning tokens:",
                    data["usage"]
                    ["completion_tokens_details"]
                    .get(
                        "reasoning_tokens"
                    )
                )

            except Exception:

                pass



        return (
            "LLM вернул пустой ответ. "
            "Модель использовала reasoning режим."
        )



def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "LM Studio Client v1.5"
    )

    print("=" * 70)



    client = LMStudioClient(

        model="qwen/qwen3.5-9b",

        debug=True

    )



    print(
        "\nAvailable models:"
    )


    models = client.get_models()


    for m in models.get(
        "data",
        []
    ):

        print(
            "-",
            m["id"]
        )



    print(
        "\nTest request...\n"
    )



    answer = client.chat(

        """
Объясни назначение СП 30.13330.2020
для проектирования внутренних систем
водоснабжения.
""",

        temperature=0.1,

        max_tokens=2048,

        enable_thinking=False,

    )



    print(
        "\nANSWER:"
    )

    print(answer)



if __name__ == "__main__":

    demo()
    