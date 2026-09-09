"""Controlled one-page Vision smoke test.

This script intentionally does NOT run run_first_pass_api().
It sends exactly one existing rendered project page to the configured
LM Studio multimodal endpoint and prints the raw HTTP response before
any candidate filtering/parsing logic is applied.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

import requests

from app.llm.lmstudio_client import LMStudioClient
from app.checking.first_pass import _json_array

DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
DEFAULT_PAGE = 8
DEFAULT_MAX_TOKENS = 1000

PROMPT = """Ты выполняешь строгий первый визуальный проход нормоконтроля страницы PDF №8.

Ищи ТОЛЬКО конкретные визуально проверяемые факты, которые потенциально могут быть сопоставлены с требованиями СП 30.13330.2020: реальные размеры и расстояния, отметки, диаметры, уклоны, параметры таблиц, видимые элементы схем, подключения, обозначения и другие инженерные параметры.

НЕ возвращай:
- просто названия проекта, раздела или тома;
- номера документов сами по себе;
- декоративный или организационный текст;
- утверждение «это нарушение» без нормы;
- предположения о невидимых данных.

Для каждого кандидата ОБЯЗАТЕЛЬНО укажи точный видимый факт в evidence_text, кратко объясни, что именно на странице нужно проверить, confidence от 0 до 1 и bbox в пикселях [x1,y1,x2,y2]. Если точный bbox определить нельзя — не возвращай кандидата.

Верни только JSON-массив:
[{"title":"конкретный объект проверки","description":"какой конкретный факт виден и что именно проверяется","evidence_text":"точный видимый текст/значение/обозначение","bbox":[x1,y1,x2,y2],"confidence":0.0}]
Если конкретных фактов нет, верни []."""


def image_data_url(path: Path) -> tuple[str, int]:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/png;base64," + encoded, len(encoded)


def main() -> int:
    parser = argparse.ArgumentParser(description="One-page Vision smoke test")
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    if args.image:
        image_path = args.image.resolve()
    else:
        evidence_dir = project_root / "knowledge" / "project_documents" / DOCUMENT_ID / "checking" / "first_pass"
        image_path = evidence_dir / f"page_{args.page:04d}.png"

    print("=== VISION SMOKE TEST ===")
    print()
    print("IMAGE:")
    print(f"  path: {image_path}")
    print(f"  exists: {image_path.exists()}")
    if not image_path.exists():
        print("  size: —")
        print("  bytes: —")
        return 2
    print(f"  size: {image_path.stat().st_size:,} bytes")
    print(f"  bytes: {image_path.stat().st_size}")

    data_url, b64_len = image_data_url(image_path)
    client = LMStudioClient(model=None)
    if client.model is None:
        client.model = client._select_chat_model(client.get_models())

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
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": args.max_tokens,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }

    print()
    print("PAYLOAD:")
    print(f"  model: {payload['model']}")
    print("  image_data_url: data:image/png;base64,...")
    print(f"  image_base64_length: {b64_len}")
    print(f"  prompt_length: {len(PROMPT)}")
    print(f"  endpoint: {client.base_url}/chat/completions")
    print(f"  temperature: {payload['temperature']}")
    print(f"  max_tokens: {payload['max_tokens']}")
    print("  thinking: False")

    print()
    print("HTTP:")
    try:
        response = requests.post(
            f"{client.base_url}/chat/completions",
            json=payload,
            timeout=client.timeout,
        )
    except Exception as exc:
        print(f"  request_error: {type(exc).__name__}: {exc}")
        return 3

    print(f"  status: {response.status_code}")
    print(f"  response_length: {len(response.text)}")
    print(f"  content_type: {response.headers.get('content-type', '—')}")

    print()
    print("RAW HTTP RESPONSE:")
    print(response.text)

    raw_content = ""
    response_json: dict[str, Any] | None = None
    try:
        response_json = response.json()
        print()
        print("RESPONSE JSON KEYS:")
        print(f"  keys: {list(response_json.keys()) if isinstance(response_json, dict) else type(response_json).__name__}")
        if isinstance(response_json, dict):
            choices = response_json.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
                if isinstance(message, dict):
                    raw_content = str(message.get("content") or "")
                    print(f"  choices[0].message.keys: {list(message.keys())}")
                    print(f"  content_length: {len(raw_content)}")
                    if "reasoning_content" in message:
                        reasoning = str(message.get("reasoning_content") or "")
                        print(f"  reasoning_content_length: {len(reasoning)}")
    except json.JSONDecodeError as exc:
        print()
        print(f"RESPONSE JSON PARSE ERROR: {exc}")

    print()
    print("RAW RESPONSE:")
    print(raw_content)

    parsed = _json_array(raw_content)
    print()
    print("PARSE:")
    print(f"  json_array: {bool(parsed) or raw_content.strip() == '[]'}")
    print(f"  candidates: {len(parsed)}")
    if parsed:
        print("  parsed_candidates:")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))

    if response.status_code >= 400:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
