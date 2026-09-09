"""Controlled Vision diagnostic through the production _vision_request() path."""
from __future__ import annotations

import argparse
from pathlib import Path

from app.checking.first_pass import _vision_request
from app.checking.vk_audit import build_vk_audit_prompt
from app.llm.lmstudio_client import LMStudioClient

DEFAULT_DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
DEFAULT_PAGE = 8
DEFAULT_MODEL = "qwen/qwen3.5-9b"
DEFAULT_MAX_TOKENS = 1400


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Controlled Vision test through the production _vision_request() path"
    )
    parser.add_argument("--document-id", default=DEFAULT_DOCUMENT_ID)
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
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

    client = LMStudioClient(model=args.model)
    available_models = [
        str(item.get("id"))
        for item in client.get_models().get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    if args.model not in available_models:
        raise SystemExit(
            f"Selected model is not available in LM Studio: {args.model}\n"
            f"Available models: {available_models}"
        )

    prompt = build_vk_audit_prompt(args.page, "vk_wastewater")

    print("=== VISION PRODUCTION REQUEST TEST ===")
    print()
    print("IMAGE:")
    print(f"  path: {image_path}")
    print(f"  exists: {image_path.exists()}")
    print(f"  size: {image_path.stat().st_size:,} bytes")
    print()
    print("PROMPT:")
    print("  source: app.checking.vk_audit.build_vk_audit_prompt")
    print("  skill_id: vk_wastewater")
    print(f"  page: {args.page}")
    print(f"  prompt_length: {len(prompt)}")
    print()
    print("PRODUCTION REQUEST PATH:")
    print("  client: LMStudioClient(model=<explicit model>)")
    print("  request: app.checking.first_pass._vision_request()")
    print("  parser: bypassed")
    print("  Skill filtering: bypassed")
    print("  RAG: bypassed")
    print("  normative decision: bypassed")
    print()
    print("PAYLOAD PARAMETERS:")
    print(f"  model: {args.model}")
    print(f"  max_tokens: {args.max_tokens}")
    print("  temperature: 0.1")
    print("  thinking: False")
    print(f"  available_models: {available_models}")
    print()
    print("NOTE:")
    print("  reproduces the production _vision_request() call path for one real page")
    print("  uses the explicit model parameter, as run_resilient_check() does")
    print("  uses the production default Vision budget of 1400 tokens")
    print("  raw content returned by _vision_request() is printed unchanged")
    print()

    raw = _vision_request(client, prompt, image_path, args.max_tokens)

    print("RAW RESPONSE FROM _vision_request():")
    print(raw)
    print()
    print("RESULT:")
    print(f"  raw_length: {len(raw)}")
    print(f"  starts_with_slashes: {raw.startswith('/')}")
    print(f"  contains_json_fence: {'```json' in raw}")
    print(f"  ends_with_json_array: {raw.rstrip().endswith(']')}")


if __name__ == "__main__":
    main()
