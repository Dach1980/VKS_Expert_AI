"""
VKS Expert AI
LM Studio Client v2.3
"""

from typing import Optional
import json
import requests

from app.checking.scope import CheckCancelled


PREFERRED_CHAT_MODELS = (
    "qwen/qwen3.5-9b", "qwen3.5-9b", "qwen3.5-9b-mtp", "qwen3-vl-4b-instruct",
    "qwen/qwen3-vl-4b-instruct", "qwen3.5-4b-mtp", "qwen/qwen3.5-4b",
)


class LMStudioClient:
    """Client for LM Studio OpenAI-compatible API with explicit model control."""

    def __init__(self, base_url: str = "http://localhost:1234/v1", model: Optional[str] = None, timeout: Optional[float] = None, cancel_event=None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.cancel_event = cancel_event
        self.actual_model: Optional[str] = None

    def get_models(self):
        response = requests.get(f"{self.base_url}/models", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _select_chat_model(models: dict) -> str:
        available = [str(item.get("id", "")) for item in models.get("data", []) if isinstance(item, dict) and item.get("id")]
        if not available:
            raise RuntimeError("No models available")
        for preferred in PREFERRED_CHAT_MODELS:
            if preferred in available:
                return preferred
        candidates = [m for m in available if "embedding" not in m.lower() and any(t in m.lower() for t in ("qwen", "llama", "mistral", "gemma"))]
        if candidates:
            return candidates[0]
        candidates = [m for m in available if "embedding" not in m.lower()]
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
        start, end = raw.find("["), raw.rfind("]")
        if start >= 0 and end > start:
            candidate = raw[start:end + 1].strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return raw

    def _cancelled(self) -> bool:
        return bool(self.cancel_event is not None and self.cancel_event.is_set())

    def _verify_actual_model(self, actual: Optional[str]) -> None:
        if actual:
            self.actual_model = str(actual)
            if self.model and self.actual_model != self.model:
                raise RuntimeError(f"LM Studio вернул другую модель: запрошена «{self.model}», фактически «{self.actual_model}»")

    def _chat_stream(self, url: str, payload: dict) -> str:
        response = requests.Session().post(url, json=payload, timeout=self.timeout, stream=True)
        response.encoding = "utf-8"
        try:
            response.raise_for_status()
            parts: list[str] = []
            reasoning_parts: list[str] = []
            for line in response.iter_lines(decode_unicode=True):
                if self._cancelled():
                    raise CheckCancelled("Проверка отменена пользователем")
                if not line:
                    continue
                text = str(line)
                if text.startswith("data:"):
                    text = text[5:].strip()
                if text == "[DONE]":
                    break
                try:
                    chunk = json.loads(text)
                except json.JSONDecodeError:
                    continue
                self._verify_actual_model(chunk.get("model"))
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0] or {}).get("delta") or {}
                if delta.get("content"):
                    parts.append(str(delta["content"]))
                if delta.get("reasoning_content"):
                    reasoning_parts.append(str(delta["reasoning_content"]))
            content = "".join(parts).strip()
            reasoning = "".join(reasoning_parts).strip()
            if content:
                return self._extract_json_array(content) if "JSON-массив" in payload["messages"][-1].get("content", "") else content
            if reasoning:
                return "LLM вернул только внутреннее рассуждение. Проверьте режим Qwen thinking в LM Studio."
            return "LLM вернул пустой ответ."
        finally:
            response.close()

    def chat(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, max_tokens: int = 2048, enable_thinking: bool = False) -> str:
        if self._cancelled():
            raise CheckCancelled("Проверка отменена пользователем")
        if self.model is None:
            self.model = self._select_chat_model(self.get_models())
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}}}
        if "JSON-массив" in prompt or "JSON-массив" in str(system_prompt or ""):
            payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "document_check_results", "strict": True, "schema": {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string", "enum": ["violation", "compliant", "unchecked"]}, "title": {"type": "string"}, "description": {"type": "string"}, "recommendation": {"type": "string"}, "sheet": {"type": "string"}, "norm": {"type": "string"}, "severity": {"type": "string", "enum": ["critical", "major", "minor"]}, "page": {"type": "integer"}, "bbox": {"type": ["array", "null"]}}, "required": ["type", "title", "description", "recommendation", "sheet", "norm", "severity", "page", "bbox"], "additionalProperties": False}}}}
        print("\nLM STUDIO REQUEST:")
        print({"model": self.model, "temperature": temperature, "max_tokens": max_tokens, "thinking": enable_thinking, "structured_json": "response_format" in payload, "timeout": self.timeout})
        if self.cancel_event is not None:
            payload["stream"] = True
            return self._chat_stream(f"{self.base_url}/chat/completions", payload)
        response = requests.post(f"{self.base_url}/chat/completions", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        self._verify_actual_model(data.get("model"))
        message = data["choices"][0]["message"]
        content = message.get("content", "") or ""
        reasoning = message.get("reasoning_content", "") or ""
        if content.strip():
            return self._extract_json_array(content) if "JSON-массив" in prompt else content.strip()
        if reasoning.strip():
            return "LLM вернул только внутреннее рассуждение. Проверьте режим Qwen thinking в LM Studio."
        return "LLM вернул пустой ответ."
