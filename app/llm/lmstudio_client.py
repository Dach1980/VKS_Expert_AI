"""
VKS Expert AI
LM Studio Client v1.6

Purpose:
Communication with LM Studio local server.

Features:
- OpenAI compatible API
- Qwen3.5 thinking mode control
- reasoning_content protection
- RAG ready
- Production-safe output filtering
"""


from typing import Optional
import requests



class LMStudioClient:
    """
    Client for LM Studio OpenAI-compatible API.
    """


    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: Optional[str] = None,
        timeout: int = 300,
    ):

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout



    def get_models(self):
        """
        Get available models.
        """

        response = requests.get(
            f"{self.base_url}/models",
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()



    def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
    ) -> str:
        """
        Send request to LM Studio.

        Important:
        reasoning_content is NEVER returned.
        """


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


            # Qwen3/Qwen3.5 control
            # Disable internal reasoning
            "extra_body":
            {
                "chat_template_kwargs":
                {
                    "enable_thinking": enable_thinking
                }
            }

        }



        print("\nLM STUDIO REQUEST:")
        print(
            {
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "thinking": enable_thinking,
            }
        )



        response = requests.post(

            f"{self.base_url}/chat/completions",

            json=payload,

            timeout=self.timeout

        )


        response.raise_for_status()


        data = response.json()



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


        reasoning = (
            message.get(
                "reasoning_content",
                ""
            )
            or ""
        )



        # --------------------------------------------------
        # Security check
        # Never expose chain-of-thought
        # --------------------------------------------------

        if reasoning.strip():

            print(
                "WARNING:"
                " reasoning_content received from model"
            )



        # --------------------------------------------------
        # Normal answer
        # --------------------------------------------------

        if content.strip():

            return content.strip()



        # --------------------------------------------------
        # Empty answer protection
        # --------------------------------------------------

        if reasoning.strip():

            return (
                "LLM вернул только внутреннее рассуждение. "
                "Проверьте режим Qwen thinking в LM Studio."
            )


        return (
            "LLM вернул пустой ответ."
        )



def demo():


    print("=" * 70)
    print(
        "VKS Expert AI"
    )
    print(
        "LM Studio Client v1.6"
    )
    print("=" * 70)



    client = LMStudioClient(
        model="qwen3.5-4b-mtp"
    )



    print("\nAvailable models:")


    models = client.get_models()


    for model in models.get(
        "data",
        []
    ):

        print(
            "-",
            model["id"]
        )



    print("\nTest request...\n")



    answer = client.chat(

        """
Объясни назначение СП 30.13330.2020
для проектирования внутренних систем
водоснабжения.
""",

        system_prompt="""
Ты инженерный AI-ассистент VKS Expert AI.

Отвечай только на русском языке.
Используй инженерную терминологию.
Не показывай внутренние рассуждения модели.
""",

        temperature=0.1,

        max_tokens=2048,

        enable_thinking=False

    )



    print("\nANSWER:")
    print(answer)




if __name__ == "__main__":

    demo()
    