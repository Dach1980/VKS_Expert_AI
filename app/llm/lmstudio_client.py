"""
VKS Expert AI
LM Studio Client v1

Purpose:
Communication with local LLM server
running in LM Studio.

Compatible with:
- Qwen GGUF
- Llama GGUF
- OpenAI-compatible API

Architecture:

Context Builder
        |
        v
LMStudioClient
        |
        v
LM Studio Local Server
        |
        v
LLM response
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
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout


    def get_models(self):
        """
        Get available models from LM Studio.
        """

        url = (
            f"{self.base_url}/models"
        )

        response = requests.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()



    def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Send prompt to local LLM.

        Args:
            prompt:
                User message

            system_prompt:
                Expert system instruction

            temperature:
                Generation randomness

        Returns:
            LLM answer
        """


        if self.model is None:

            models = self.get_models()

            if not models.get("data"):

                raise RuntimeError(
                    "No model loaded in LM Studio"
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

        }


        url = (
            f"{self.base_url}/chat/completions"
        )


        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout,
        )


        response.raise_for_status()


        data = response.json()


        return (
            data["choices"][0]
            ["message"]
            ["content"]
        )



def demo():

    print("=" * 70)
    print("VKS Expert AI")
    print("LM Studio Client v1")
    print("=" * 70)


    client = LMStudioClient()


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


    print("\nTest request...")


    answer = client.chat(
        """
Объясни назначение СП 30.13330.2020
для проектирования внутренних систем
водоснабжения.
        """
    )


    print("\nANSWER:")
    print(answer)



if __name__ == "__main__":

    demo()
    