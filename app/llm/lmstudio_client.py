"""
VKS Expert AI
LM Studio Client v2.0

Communication with LM Studio local server.
"""

from typing import Optional
import json
import requests


PREFERRED_CHAT_MODELS = (
    "qwen3-vl-4b-instruct",
    "qwen/qwen3-vl-4b-instruct",
    "qwen3.5-4b-mtp",
    "qwen3.5-9b-mtp",
    "qwen/qwen3.5-9b",
    "qwen3.5-9b",
    "qwen/qwen3.5-4b",
)


class LMStudioClient:
    """Client for LM Studio OpenAI-compatible API.

    timeout=None is intentional: long local-document checks must not be
    terminated by an arbitrary wall-clock limit. The API exposes checks as
    background jobs, so the browser no longer waits for the model request.
    """

    def __init__(self, base_url: str = "http://localhost:1234/v1", model: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def get_models(self):
        response = requests.get(f"{self.base_url}/models", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _select_chat_model(models: dict) -> str:
        available = [
            str(item.get("id", ""))
            for item in models.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]
        if not available:
            raise RuntimeError("No models available")
        for preferred in PREFERRED_CHAT_MODELS:
            if preferred in available:
                return preferred
        candidates = [
            model for model in available
            if "embedding" not in model.lower()
            and any(token in model.lower() for token in ("qwen", "llama", "mistral", "gemma"))
        ]
        if candidates:
            return candidates[0]
        candidates = [model for model in available if "embedding" not in model.lower()]
        if candidates:
            return candidates[0]
        raise RuntimeError("No chat-capable model available; only embedding models are loaded")

    @staticmethod
    def _extract_json_array(text: str) -> str:
        raw = str(text or "").strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1).replace("```", "", 1).strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
            if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
                return json.dumps(parsed["results"], ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            candidate = raw[start:end + 1].strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return raw

    def chat(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, max_tokens: int = 2048, enable_thinking: bool = False) -> str:
        if self.model is None:
            self.model = self._select_chat_model(self.get_models())
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}},
        }
        if "JSON-массив" in prompt or "JSON-массив" in str(system_prompt or ""):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "document_check_results", "strict": True,
                    "schema": {"type": "array", "items": {"type": "object", "properties": {
                        "type": {"type": "string", "enum": ["violation", "compliant", "unchecked"]},
                        "title": {"type": "string"}, "description": {"type": "string"}, "recommendation": {"type": "string"},
                        "sheet": {"type": "string"}, "norm": {"type": "string"},
                        "severity": {"type": "string", "enum": ["critical", "major", "minor"]},
                        "page": {"type": "integer"}, "bbox": {"type": ["array", "null"]},
                    }, "required": ["type", "title", "description", "recommendation", "sheet", "norm", "severity", "page", "bbox"], "additionalProperties": False}}
                }
            }
        print("\nLM STUDIO REQUEST:")
        print({"model": self.model, "temperature": temperature, "max_tokens": max_tokens, "thinking": enable_thinking, "structured_json": "response_format" in payload, "timeout": self.timeout})
        response = requests.post(f"{self.base_url}/chat/completions", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        content = message.get("content", "") or ""
        reasoning = message.get("reasoning_content", "") or ""
        if reasoning.strip():
            print("WARNING: reasoning_content received from model")
        if content.strip():
            return self._extract_json_array(content) if "JSON-массив" in prompt else content.strip()
        if reasoning.strip():
            return "LLM вернул только внутреннее рассуждение. Проверьте режим Qwen thinking в LM Studio."
        return "LLM вернул пустой ответ."


def demo():
    client = LMStudioClient(model="qwen3-vl-4b-instruct")
    print("Available models:")
    for model in client.get_models().get("data", []):
        print("-", model["id"])
    answer = client.chat(
        "Объясни назначение СП 30.13330.2020 для проектирования внутренних систем водоснабжения.",
        system_prompt="Ты инженерный AI-ассистент VKS Expert AI. Отвечай только на русском языке. Не показывай внутренние рассуждения модели.",
        temperature=0.1, max_tokens=2048, enable_thinking=False,
    )
    print("\nANSWER:\n", answer)


if __name__ == "__main__":
    demo()
