"""Portable JSON request helper for multimodal LM Studio vision models."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from app.llm.lmstudio_client import LMStudioClient


# Qwen3-VL in some LM Studio builds rejects OpenAI response_format/json_schema
# even though the endpoint itself is OpenAI-compatible. Keep the request
# portable: enforce the contract in the prompt and let the existing parser
# validate/extract the JSON object afterwards.
VISION_SYSTEM_PROMPT = (
    "Ты выполняешь строгий визуальный анализ проектной документации. "
    "Не выдумывай факты, координаты или нарушения. Возвращай только наблюдения, "
    "которые можно проверить по изображению. "
    "Ответ должен быть только одним валидным JSON-объектом без markdown и пояснений "
    'в формате {"findings":[...]}. Каждый элемент findings обязан содержать поля: '
    "check_id, title, description, parameter, project_value, unit, source_row, "
    "source_context, evidence_text, bbox, confidence. bbox — массив из 4 чисел "
    "[x1,y1,x2,y2], confidence — число от 0 до 1. Если проверяемых наблюдений нет, "
    'верни {"findings":[]}. '
)


def structured_vision_request(
    client: LMStudioClient,
    prompt: str,
    image_path: Path,
    max_tokens: int = 1400,
) -> str:
    """Call LM Studio with a portable prompt-level JSON contract."""
    if client.model is None:
        client.model = client._select_chat_model(client.get_models())

    image_data = "data:image/png;base64," + base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload: dict[str, Any] = {
        "model": client.model,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
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
    }

    response = requests.post(
        f"{client.base_url}/chat/completions",
        json=payload,
        timeout=client.timeout,
    )
    if not response.ok:
        # Keep the real LM Studio response visible in the terminal. This is
        # essential for diagnosing model/API compatibility instead of hiding
        # the reason behind requests.HTTPError and the retry loop.
        body = response.text.strip().replace("\n", " ")
        if len(body) > 1000:
            body = body[:1000] + "..."
        print(
            f"[NORMCONTROL] VISION_HTTP_ERROR status={response.status_code} "
            f"model={client.model} body={body}",
            flush=True,
        )
    response.raise_for_status()

    message = response.json()["choices"][0]["message"]
    content = message.get("content", "") or ""
    if isinstance(content, list):
        content = "".join(
            str(item.get("text") or "") if isinstance(item, dict) else str(item)
            for item in content
        )
    content = str(content).strip()
    if content:
        return content

    print(
        f"[NORMCONTROL] VISION_STRUCTURED_EMPTY model={client.model} "
        f"reasoning_present={int(bool(str(message.get('reasoning_content') or '').strip()))}",
        flush=True,
    )
    return ""
