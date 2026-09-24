from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.checking.vk_audit import build_vk_audit_prompt
from app.checking.vision_structured import VISION_SYSTEM_PROMPT
from app.llm.lmstudio_client import LMStudioClient


DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
PAGE = 8
MODEL = "qwen3.5-4b"
URL = "http://127.0.0.1:1234/v1/chat/completions"


def flags(text: str) -> dict:
    return {
        "contains_Da": "Ð" in text,
        "contains_N": "Ñ" in text,
        "contains_replacement": "\ufffd" in text,
        "contains_question_mark": "?" in text,
    }


def main() -> None:
    image_path = (
        PROJECT_ROOT
        / "knowledge"
        / "project_documents"
        / DOCUMENT_ID
        / "checking"
        / "first_pass"
        / f"page_{PAGE:04d}.png"
    )

    if not image_path.exists():
        raise FileNotFoundError(image_path)

    image_data = (
        "data:image/png;base64,"
        + base64.b64encode(image_path.read_bytes()).decode("ascii")
    )

    prompt = build_vk_audit_prompt(PAGE, "vk_wastewater")

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": VISION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data,
                        },
                    },
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1400,
        "stream": True,
        "extra_body": {
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    }

    print("=" * 80)
    print("VISION STREAM ENCODING DIAGNOSTIC")
    print("=" * 80)
    print(f"Image: {image_path}")
    print(f"Image size: {image_path.stat().st_size}")
    print(f"Model: {MODEL}")
    print(f"URL: {URL}")
    print()

    session = requests.Session()

    response = session.post(
        URL,
        json=payload,
        timeout=120,
        stream=True,
    )
    response.encoding = "utf-8"

    try:
        print(f"HTTP status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"requests encoding: {response.encoding}")
        print(f"apparent encoding: {response.apparent_encoding}")
        print()

        response.raise_for_status()

        # ------------------------------------------------------------
        # 1. Read a small raw chunk WITHOUT decoding
        # ------------------------------------------------------------
        raw_chunk = next(response.iter_content(chunk_size=4096), b"")

        print("-" * 80)
        print("1. RAW HTTP BYTES")
        print("-" * 80)
        print(f"Raw bytes length: {len(raw_chunk)}")
        print("Raw bytes repr:")
        print(repr(raw_chunk[:1500]))
        print()

        try:
            raw_utf8 = raw_chunk.decode("utf-8")
            print("raw_chunk.decode('utf-8'): OK")
            print(repr(raw_utf8[:1500]))
            print("flags:", flags(raw_utf8))
        except UnicodeDecodeError as exc:
            print("raw_chunk.decode('utf-8'): FAILED")
            print(repr(exc))

        print()

        # We consumed the stream above, so issue the same request again.
        response.close()

        response = session.post(
            URL,
            json=payload,
            timeout=120,
            stream=True,
        )
        response.encoding = "utf-8"

        response.raise_for_status()

        # ------------------------------------------------------------
        # 2. requests iter_lines(decode_unicode=True)
        # ------------------------------------------------------------
        print("-" * 80)
        print("2. response.iter_lines(decode_unicode=True)")
        print("-" * 80)

        line_number = 0
        decoded_lines = []

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            line_number += 1
            text = str(line)

            print(f"\n--- LINE {line_number} ---")
            print("repr:")
            print(repr(text[:2000]))
            print("flags:", flags(text))

            decoded_lines.append(text)

            if line_number >= 20:
                break

        # ------------------------------------------------------------
        # 3. Parse SSE JSON chunks
        # ------------------------------------------------------------
        print()
        print("-" * 80)
        print("3. JSON / delta.content")
        print("-" * 80)

        content_parts: list[str] = []
        reasoning_parts: list[str] = []

        for text in decoded_lines:
            if text.startswith("data:"):
                text = text[5:].strip()

            if text == "[DONE]":
                continue

            try:
                chunk = json.loads(text)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices") or []
            if not choices:
                continue

            delta = (choices[0] or {}).get("delta") or {}

            content = delta.get("content")
            reasoning = delta.get("reasoning_content")

            if content:
                content_parts.append(str(content))

            if reasoning:
                reasoning_parts.append(str(reasoning))

        content = "".join(content_parts)
        reasoning = "".join(reasoning_parts)

        print("CONTENT:")
        print(repr(content[:3000]))
        print("flags:", flags(content))
        print()

        print("REASONING:")
        print(repr(reasoning[:3000]))
        print("flags:", flags(reasoning))
        print()

        # ------------------------------------------------------------
        # 4. Compare with actual LMStudioClient streaming path
        # ------------------------------------------------------------
        print("-" * 80)
        print("4. LMStudioClient._chat_stream()")
        print("-" * 80)

        client = LMStudioClient(model=MODEL)

        result = client._chat_stream(URL, payload)

        print("result repr:")
        print(repr(result[:3000]))
        print("flags:", flags(result))

        print()
        print("=" * 80)
        print("DIAGNOSTIC FINISHED")
        print("=" * 80)

    finally:
        response.close()


if __name__ == "__main__":
    main()
    