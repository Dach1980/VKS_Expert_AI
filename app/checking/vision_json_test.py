"""Diagnostic one-page Vision + JSON test.

This test intentionally bypasses the Skill prompt, candidate schema, RAG,
and the first-pass pipeline. It uses the same real project page as the
controlled Vision read test and changes only the requested output format:
strict JSON.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

import requests

from app.llm.lmstudio_client import LMStudioClient

DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
DEFAULT_PAGE = 8
DEFAULT_MAX_TOKENS = 500

PROMPT = """Проанализируй изображение страницы.
Укажи 3–5 конкретных визуально наблюдаемых фрагментов: текст, обозначения, числа или элементы чертежа.
Не делай нормативных выводов.
Верни результат строго как JSON-массив объектов следующего вида:
[{"type":"text","value":"..."}]
Не добавляй пояснений, Markdown и ```json."""

SYSTEM_PROMPT = """Ты выполняешь простой диагностический тест зрения модели.
Твоя задача — определить, что модель действительно может визуально увидеть и прочитать на изображении.
Не выдумывай сведения и не делай нормативных выводов.
Ответ должен быть только валидным JSON-массивом."""


def image_data_url(path: Path) -> tuple[str, int]:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/png;base64," + encoded, len(encoded)


def try_parse_json_array(raw_content: str) -> tuple[bool, Any]:
    text = raw_content.strip()
    if text.startswith("```json"):
        text = text[len("```json") :].strip()
    elif text.startswith("```"):
        text = text[len("```") :].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False, None

    return isinstance(parsed, list), parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="One-page Vision + JSON diagnostic test")
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    if args.image:
        image_path = args.image.resolve()
    else:
        evidence_dir = (
            project_root
            / "knowledge"
            / "project_documents"
            / DOCUMENT_ID
            / "checking"
            / "first_pass"
        )
        image_path = evidence_dir / f"page_{args.page:04d}.png"

    print("=== VISION JSON TEST ===")
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
            {"role": "system", "content": SYSTEM_PROMPT},
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
    try:
        response_json = response.json()
        print()
        print("RESPONSE JSON KEYS:")
        print(
            f"  keys: {list(response_json.keys()) if isinstance(response_json, dict) else type(response_json).__name__}"
        )
        if isinstance(response_json, dict):
            choices = response_json.get("choices")
            if isinstance(choices, list) and choices:
                choice = choices[0] if isinstance(choices[0], dict) else {}
                message = choice.get("message", {}) if isinstance(choice, dict) else {}
                if isinstance(message, dict):
                    print(f"  choices[0].message.keys: {list(message.keys())}")
                    raw_content = str(message.get("content") or "")
                    print(f"  content_length: {len(raw_content)}")
                    reasoning = str(message.get("reasoning_content") or "")
                    print(f"  reasoning_content_length: {len(reasoning)}")
                print(f"  finish_reason: {choice.get('finish_reason', '—')}")
    except json.JSONDecodeError as exc:
        print()
        print(f"RESPONSE JSON PARSE ERROR: {exc}")

    print()
    print("RAW RESPONSE CONTENT:")
    print(raw_content)

    parsed_ok, parsed = try_parse_json_array(raw_content)
    print()
    print("JSON DIAGNOSTIC:")
    print(f"  valid_json_array: {parsed_ok}")
    if parsed_ok:
        print(f"  items: {len(parsed)}")
        print(f"  parsed: {json.dumps(parsed, ensure_ascii=False)}")
    else:
        print("  parsed: —")

    if response.status_code >= 400:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
