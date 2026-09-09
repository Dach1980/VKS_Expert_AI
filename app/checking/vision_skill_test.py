"""Controlled Vision diagnostic using the exact production VK Skill prompt."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import requests

from app.checking.vk_audit import build_vk_audit_prompt
from app.llm.lmstudio_client import LMStudioClient

DEFAULT_DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
DEFAULT_PAGE = 8
DEFAULT_MAX_TOKENS = 1400


def _image_data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled Vision test with the exact production VK Skill prompt")
    parser.add_argument("--document-id", default=DEFAULT_DOCUMENT_ID)
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    image_path = args.image or (
        root
        / "knowledge"
        / "project_documents"
        / args.document_id
        / "checking"
        / "first_pass"
        / f"page_{args.page:04d}.png"
    )

    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    client = LMStudioClient(model=None)
    if client.model is None:
        client.model = client._select_chat_model(client.get_models())
    if not client.model:
        raise SystemExit("No LM Studio chat model selected")

    prompt = build_vk_audit_prompt(args.page, "vk_wastewater")
    image_bytes = image_path.read_bytes()
    image_url = _image_data_url(image_path)

    payload = {
        "model": client.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты выполняешь строгий визуальный анализ проектной документации. "
                    "Не выдумывай факты, координаты или нарушения. "
                    "Возвращай только наблюдения, которые можно проверить по изображению."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": args.max_tokens,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }

    print("=== VISION SKILL TEST ===")
    print()
    print("IMAGE:")
    print(f"  path: {image_path}")
    print(f"  exists: {image_path.exists()}")
    print(f"  size: {len(image_bytes):,} bytes")
    print()
    print("PROMPT:")
    print("  source: app.checking.vk_audit.build_vk_audit_prompt")
    print("  skill_id: vk_wastewater")
    print(f"  page: {args.page}")
    print(f"  prompt_length: {len(prompt)}")
    print()
    print("PAYLOAD:")
    print(f"  model: {client.model}")
    print(f"  image_base64_length: {len(image_url.split(',', 1)[1])}")
    print(f"  endpoint: {client.base_url}/chat/completions")
    print("  temperature: 0.1")
    print(f"  max_tokens: {args.max_tokens}")
    print("  thinking: False")
    print()
    print("NOTE:")
    print("  bypasses run_resilient_check() / run_first_pass_api()")
    print("  bypasses _json_array(), _strict_candidates(), RAG and normative decision")
    print("  uses the exact production Skill prompt from vk_audit.py")
    print()

    response = requests.post(
        f"{client.base_url}/chat/completions",
        json=payload,
        timeout=client.timeout,
    )
    print("HTTP:")
    print(f"  status: {response.status_code}")
    print(f"  response_length: {len(response.text)}")
    print(f"  content_type: {response.headers.get('content-type', '')}")
    print()
    print("RAW HTTP RESPONSE:")
    print(response.text)
    print()

    response.raise_for_status()
    data = response.json()
    message = data.get("choices", [{}])[0].get("message", {})
    content = str(message.get("content") or "")
    reasoning = str(message.get("reasoning_content") or "")

    print("RESPONSE:")
    print(f"  model: {data.get('model')}")
    print(f"  finish_reason: {data.get('choices', [{}])[0].get('finish_reason')}")
    print(f"  content_length: {len(content)}")
    print(f"  reasoning_content_length: {len(reasoning)}")
    print()
    print("RAW RESPONSE CONTENT:")
    print(content)


if __name__ == "__main__":
    main()
