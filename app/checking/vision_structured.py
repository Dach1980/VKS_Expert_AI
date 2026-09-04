"""Structured JSON request helper for multimodal LM Studio vision models."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from app.llm.lmstudio_client import LMStudioClient


# LM Studio's local structured-output implementation is more portable when the
# root schema is an object. The page parser already accepts {"findings": [...]}.
VISION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "vk_visual_evidence",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "check_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "parameter": {"type": "string"},
                            "project_value": {"type": "string"},
                            "unit": {"type": "string"},
                            "source_row": {"type": "string"},
                            "source_context": {"type": "string"},
                            "evidence_text": {"type": "string"},
                            "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": [
                            "check_id", "title", "description", "parameter", "project_value", "unit",
                            "source_row", "source_context", "evidence_text", "bbox", "confidence",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["findings"],
            "additionalProperties": False,
        },
    },
}


def structured_vision_request(
    client: LMStudioClient,
    prompt: str,
    image_path: Path,
    max_tokens: int = 1400,
) -> str:
    """Call LM Studio with a strict object schema so the page pipeline gets parseable evidence."""
    if client.model is None:
        client.model = client._select_chat_model(client.get_models())
    image_data = "data:image/png;base64," + base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload: dict[str, Any] = {
        "model": client.model,
        "messages": [
            {
                "role": "system",
                "content": "Ты выполняешь строгий визуальный анализ проектной документации. Не выдумывай факты, координаты или нарушения. Возвращай только наблюдения, которые можно проверить по изображению.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        "response_format": VISION_RESPONSE_FORMAT,
    }
    response = requests.post(f"{client.base_url}/chat/completions", json=payload, timeout=client.timeout)
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    content = message.get("content", "") or ""
    if isinstance(content, list):
        content = "".join(str(item.get("text") or "") if isinstance(item, dict) else str(item) for item in content)
    content = str(content).strip()
    if content:
        return content
    print(
        f"[NORMCONTROL] VISION_STRUCTURED_EMPTY model={client.model} reasoning_present={int(bool(str(message.get('reasoning_content') or '').strip()))}",
        flush=True,
    )
    return ""
