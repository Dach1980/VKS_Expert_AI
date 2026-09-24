from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path

import requests

from app.checking import first_pass
from app.llm.lmstudio_client import LMStudioClient


IMAGE_PATH = (
    PROJECT_ROOT
    / "knowledge"
    / "project_documents"
    / "53c22e43fcc843ef81f950516e81e68d"
    / "checking"
    / "first_pass"
    / "page_0008.png"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_preview(value, limit=3000):
    if isinstance(value, bytes):
        return value[:limit].hex()

    text = str(value)
    return text[:limit]


def main():
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")

    print("=" * 80)
    print("REAL VISION ENCODING DIAGNOSTIC")
    print("=" * 80)
    print(f"Image: {IMAGE_PATH}")
    print(f"Image size: {IMAGE_PATH.stat().st_size} bytes")
    print()

    # Используем тот же клиент, который применяется в проекте.
    client = LMStudioClient(
        base_url="http://127.0.0.1:1234/v1",
        model="qwen3.5-4b",
    )

    if client.model is None:
        client.model = client._select_chat_model(client.get_models())

    prompt = (
        "Проанализируй изображение страницы проектной документации. "
        "Извлеки только проверяемые визуальные наблюдения. "
        "Особенно обрати внимание на обозначения, размеры, диаметры, "
        "текстовые подписи, таблицы и элементы схемы. "
        "Не выдумывай отсутствующие данные. "
        "Верни результат в JSON."
    )

    captured = {}

    original_post = requests.post

    def capture_post(*args, **kwargs):
        response = original_post(*args, **kwargs)

        # ------------------------------------------------------------
        # 1. HTTP transport
        # ------------------------------------------------------------
        raw_bytes = bytes(response.content or b"")

        captured["url"] = str(args[0]) if args else ""
        captured["http_status"] = response.status_code
        captured["content_type"] = response.headers.get("Content-Type", "")
        captured["encoding_from_requests"] = response.encoding
        captured["apparent_encoding"] = getattr(
            response,
            "apparent_encoding",
            None,
        )

        captured["raw_response_bytes_length"] = len(raw_bytes)

        # Первые байты в HEX — для контроля фактического HTTP payload.
        captured["raw_response_bytes_hex_preview"] = raw_bytes[:2000].hex()

        # ------------------------------------------------------------
        # 2. Независимый raw bytes -> UTF-8 decode
        # ------------------------------------------------------------
        try:
            decoded_utf8 = raw_bytes.decode("utf-8")

            captured["utf8_decode_ok"] = True
            captured["utf8_decoded_length"] = len(decoded_utf8)
            captured["utf8_decoded_preview"] = decoded_utf8[:3000]
            captured["utf8_decoded_repr"] = repr(decoded_utf8[:3000])

        except UnicodeDecodeError as exc:
            decoded_utf8 = None

            captured["utf8_decode_ok"] = False
            captured["utf8_decode_error"] = repr(exc)

        # ------------------------------------------------------------
        # 3. response.text
        # ------------------------------------------------------------
        captured["response_text_preview"] = response.text[:3000]
        captured["response_text_repr"] = repr(response.text[:3000])

        # ------------------------------------------------------------
        # 4. requests response.json()
        # ------------------------------------------------------------
        try:
            parsed_json = response.json()

            captured["response_json_ok"] = True
            captured["response_json_type"] = type(parsed_json).__name__

        except Exception as exc:
            parsed_json = None

            captured["response_json_ok"] = False
            captured["response_json_error"] = repr(exc)

        # ------------------------------------------------------------
        # 5. JSON -> choices -> message
        # ------------------------------------------------------------
        if isinstance(parsed_json, dict):
            choices = parsed_json.get("choices") or []

            if choices:
                message = choices[0].get("message") or {}

                content = message.get("content")
                reasoning_content = message.get("reasoning_content")

                captured["message_content_type"] = type(content).__name__
                captured["message_content_preview"] = safe_preview(content)
                captured["message_content_repr"] = repr(
                    str(content)[:3000]
                )

                captured["reasoning_content_type"] = (
                    type(reasoning_content).__name__
                )
                captured["reasoning_content_preview"] = safe_preview(
                    reasoning_content
                )
                captured["reasoning_content_repr"] = repr(
                    str(reasoning_content)[:3000]
                )

                captured["finish_reason"] = choices[0].get(
                    "finish_reason"
                )

        return response

    # ------------------------------------------------------------
    # Перехватываем РОВНО тот requests.post(), который использует
    # first_pass._vision_request().
    # ------------------------------------------------------------
    requests.post = capture_post

    try:
        result = first_pass._vision_request(
            client=client,
            prompt=prompt,
            image_path=IMAGE_PATH,
            max_tokens=1200,
        )

    finally:
        requests.post = original_post

    # ------------------------------------------------------------
    # 6. Что реально вернул _vision_request()
    # ------------------------------------------------------------
    captured["vision_request_return_type"] = type(result).__name__
    captured["vision_request_return_preview"] = result[:3000]
    captured["vision_request_return_repr"] = repr(result[:3000])

    # ------------------------------------------------------------
    # 7. Признаки mojibake
    # ------------------------------------------------------------
    def encoding_flags(text):
        text = str(text or "")

        return {
            "contains_Da": "Ð" in text,
            "contains_N": "Ñ" in text,
            "contains_replacement": "\ufffd" in text,
            "contains_question_mark": "?" in text,
        }

    captured["encoding_flags"] = {
        "utf8_decoded": encoding_flags(
            captured.get("utf8_decoded_preview", "")
        ),
        "response_text": encoding_flags(
            captured.get("response_text_preview", "")
        ),
        "message_content": encoding_flags(
            captured.get("message_content_preview", "")
        ),
        "vision_request_return": encoding_flags(
            captured.get("vision_request_return_preview", "")
        ),
    }

    # ------------------------------------------------------------
    # 8. Полезная контрольная информация
    # ------------------------------------------------------------
    image_bytes = IMAGE_PATH.read_bytes()

    captured["image"] = {
        "path": str(IMAGE_PATH),
        "size": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
    }

    captured["request_payload"] = {
        "model": client.model,
        "temperature": 0.1,
        "max_tokens": 1200,
        "extra_body": {
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        },
        "messages_structure": [
            {
                "role": "system",
                "content_type": "text",
            },
            {
                "role": "user",
                "content_types": [
                    "text",
                    "image_url",
                ],
            },
        ],
        "image_data_url": {
            "type": "data:image/png;base64",
            "base64_length": len(
                base64.b64encode(image_bytes).decode("ascii")
            ),
        },
    }

    captured["diagnostic_timestamp"] = datetime.now().isoformat()

    output_file = (
        OUTPUT_DIR
        / f"vision_encoding_real_{datetime.now():%Y%m%d_%H%M%S}.json"
    )

    output_file.write_text(
        json.dumps(
            captured,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(f"HTTP status: {captured.get('http_status')}")
    print(f"Content-Type: {captured.get('content_type')}")
    print(f"requests encoding: {captured.get('encoding_from_requests')}")
    print(
        f"Raw bytes: "
        f"{captured.get('raw_response_bytes_length')}"
    )
    print(
        f"UTF-8 decode OK: "
        f"{captured.get('utf8_decode_ok')}"
    )
    print(
        f"JSON parse OK: "
        f"{captured.get('response_json_ok')}"
    )
    print()

    print("--- raw bytes -> UTF-8 ---")
    print(captured.get("utf8_decoded_preview", "")[:1000])
    print()

    print("--- message.content ---")
    print(captured.get("message_content_preview", "")[:1000])
    print()

    print("--- _vision_request() return ---")
    print(captured.get("vision_request_return_preview", "")[:1000])
    print()

    print("--- encoding flags ---")
    print(
        json.dumps(
            captured.get("encoding_flags", {}),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(f"Diagnostic saved to:")
    print(output_file)


if __name__ == "__main__":
    main()
