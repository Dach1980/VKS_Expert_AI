from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:1234/v1"
MODEL = "qwen3.5-4b"

PROMPT = """
Ответь одним коротким предложением на русском языке.
Напиши: "Проверка кодировки UTF-8 успешно выполнена."
Не используй английский язык.
"""


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir = Path("data") / "debug"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"vision_encoding_test_{timestamp}.json"

    url = f"{BASE_URL}/chat/completions"

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
            }
        ],
        "temperature": 0,
        "max_tokens": 100,
        "stream": False,
    }

    print("=" * 80)
    print("VISION / LM STUDIO UTF-8 DIAGNOSTIC TEST")
    print("=" * 80)
    print(f"URL:   {url}")
    print(f"MODEL: {MODEL}")
    print()

    print("1. Отправляем HTTP request...")

    response = requests.post(
        url,
        json=payload,
        timeout=120,
    )

    print(f"HTTP status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"requests encoding: {response.encoding}")
    print()

    response.raise_for_status()

    # ------------------------------------------------------------------
    # 1. RAW HTTP BYTES
    # ------------------------------------------------------------------

    raw_bytes = bytes(response.content or b"")

    print("2. RAW HTTP BYTES")
    print(f"raw_bytes length: {len(raw_bytes)}")
    print(f"raw_bytes first 100 bytes: {raw_bytes[:100]!r}")
    print()

    # ------------------------------------------------------------------
    # 2. RAW BYTES -> UTF-8
    # ------------------------------------------------------------------

    print("3. raw_bytes.decode('utf-8')")

    utf8_decode_ok = True
    utf8_decode_error = None
    raw_utf8_text = ""

    try:
        raw_utf8_text = raw_bytes.decode("utf-8")
        print("UTF-8 decode: OK")
        print("Preview:")
        print(raw_utf8_text[:1000])
        print()
        print("repr:")
        print(repr(raw_utf8_text[:1000]))
    except UnicodeDecodeError as exc:
        utf8_decode_ok = False
        utf8_decode_error = repr(exc)

        print("UTF-8 decode: FAILED")
        print(exc)

    print()

    # ------------------------------------------------------------------
    # 3. response.json()
    # ------------------------------------------------------------------

    print("4. response.json()")

    json_parse_ok = True
    json_parse_error = None
    data = None

    try:
        data = response.json()
        print("JSON parse: OK")
    except Exception as exc:
        json_parse_ok = False
        json_parse_error = repr(exc)

        print("JSON parse: FAILED")
        print(exc)

    print()

    # ------------------------------------------------------------------
    # 4. message.content
    # ------------------------------------------------------------------

    message_content = None
    message_content_repr = None

    if data is not None:
        try:
            message_content = (
                data["choices"][0]["message"].get("content")
            )

            message_content_repr = repr(message_content)

            print("5. response.json()['choices'][0]['message']['content']")
            print("content:")
            print(message_content)
            print()
            print("repr:")
            print(message_content_repr)

        except Exception as exc:
            print("Не удалось получить message.content:")
            print(repr(exc))

    print()

    # ------------------------------------------------------------------
    # COMPARISON
    # ------------------------------------------------------------------

    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(
        "raw_utf8_text contains message.content:",
        message_content is not None
        and isinstance(raw_utf8_text, str)
        and message_content in raw_utf8_text,
    )

    if isinstance(message_content, str):
        print(
            "message.content has mojibake marker 'Ð':",
            "Ð" in message_content,
        )

        print(
            "message.content has 'Ñ':",
            "Ñ" in message_content,
        )

        print(
            "message.content has replacement char '�':",
            "\ufffd" in message_content,
        )

        print(
            "message.content has question mark '?':",
            "?" in message_content,
        )

    print()

    # ------------------------------------------------------------------
    # SAVE RAW BYTES + ALL REPRESENTATIONS
    # ------------------------------------------------------------------

    result = {
        "test": {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "model": MODEL,
        },

        "http": {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "requests_encoding": response.encoding,
            "apparent_encoding": getattr(response, "apparent_encoding", None),
        },

        "raw_http": {
            "raw_bytes_length": len(raw_bytes),

            # Полные байты сохраняем безопасно в JSON через Base64.
            "raw_bytes_base64": base64.b64encode(raw_bytes).decode("ascii"),

            # И дополнительно первые 500 байт в hex для удобства анализа.
            "raw_bytes_hex_preview": raw_bytes[:500].hex(),
        },

        "raw_bytes_utf8": {
            "decode_ok": utf8_decode_ok,
            "decode_error": utf8_decode_error,
            "text": raw_utf8_text,
            "repr": repr(raw_utf8_text),
        },

        "response_json": {
            "parse_ok": json_parse_ok,
            "parse_error": json_parse_error,
        },

        "message_content": {
            "value": message_content,
            "repr": message_content_repr,
        },

        "comparison": {
            "message_content_in_raw_utf8": (
                message_content is not None
                and isinstance(raw_utf8_text, str)
                and isinstance(message_content, str)
                and message_content in raw_utf8_text
            ),
            "message_content_has_mojibake_D": (
                isinstance(message_content, str)
                and "Ð" in message_content
            ),
            "message_content_has_mojibake_N": (
                isinstance(message_content, str)
                and "Ñ" in message_content
            ),
            "message_content_has_replacement_char": (
                isinstance(message_content, str)
                and "\ufffd" in message_content
            ),
            "message_content_has_question_mark": (
                isinstance(message_content, str)
                and "?" in message_content
            ),
        },
    }

    output_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=" * 80)
    print(f"Результат сохранён:")
    print(output_file)
    print("=" * 80)


if __name__ == "__main__":
    main()
    