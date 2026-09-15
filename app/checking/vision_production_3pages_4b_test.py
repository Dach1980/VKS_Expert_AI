from __future__ import annotations

import json
from pathlib import Path

from app.checking.first_pass import _vision_request
from app.llm.lmstudio_client import LMStudioClient
from app.checking.vk_audit import build_vk_audit_prompt


ROOT = Path(__file__).resolve().parents[2]

IMAGE_DIR = (
    ROOT
    / "knowledge"
    / "project_documents"
    / "53c22e43fcc843ef81f950516e81e68d"
    / "checking"
    / "first_pass"
)

PAGES = [8, 9, 10]

MODEL = "qwen3.5-4b"
MAX_TOKENS = 3000


def page_path(page_number: int) -> Path:
    return IMAGE_DIR / f"page_{page_number:04d}.png"


def diagnose_raw(raw: str) -> dict:
    stripped = raw.strip()

    return {
        "raw_length": len(raw),
        "starts_with_slashes": stripped.startswith("/"),
        "contains_json_fence": "```json" in raw.lower(),
        "ends_with_json_array": stripped.endswith("]"),
        "starts_with_json_array": stripped.startswith("["),
        "preview_start": raw[:500],
        "preview_end": raw[-500:] if raw else "",
    }


def main() -> None:
    print("=" * 80)
    print("TEST #7 — PRODUCTION VISION, 3 PAGES, QWEN 3.5 4B")
    print("=" * 80)

    print(f"Model: {MODEL}")
    print(f"Pages: {PAGES}")
    print(f"max_tokens: {MAX_TOKENS}")
    print()

    client = LMStudioClient(model=MODEL)

    print("Available models:")
    try:
        print(client.list_models())
    except Exception as exc:
        print(f"Could not list models: {exc}")

    print()
    print(f"Using explicit model: {client.model}")
    print()

    results = []

    for page_number in PAGES:
        image_path = page_path(page_number)

        print("-" * 80)
        print(f"PAGE {page_number}")
        print("-" * 80)

        if not image_path.exists():
            print(f"ERROR: image not found: {image_path}")
            results.append(
                {
                    "page": page_number,
                    "error": f"Image not found: {image_path}",
                }
            )
            continue

        image_size = image_path.stat().st_size
        prompt = build_vk_audit_prompt(page_number, "vk_wastewater")

        print(f"Image: {image_path}")
        print(f"Image size: {image_size} bytes")
        print(f"Prompt length: {len(prompt)}")
        print(f"Model: {client.model}")
        print(f"max_tokens: {MAX_TOKENS}")
        print()

        try:
            raw = _vision_request(
                client,
                prompt,
                image_path,
                MAX_TOKENS,
            )

            diagnosis = diagnose_raw(raw)

            result = {
                "page": page_number,
                "model": client.model,
                "image_size": image_size,
                "prompt_length": len(prompt),
                "raw": raw,
                **diagnosis,
            }

            results.append(result)

            print("RAW RESPONSE:")
            print(raw)
            print()

            print("DIAGNOSTICS:")
            print(json.dumps(diagnosis, ensure_ascii=False, indent=2))
            print()

        except Exception as exc:
            print(f"ERROR on page {page_number}: {type(exc).__name__}: {exc}")

            results.append(
                {
                    "page": page_number,
                    "model": client.model,
                    "image_size": image_size,
                    "prompt_length": len(prompt),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

        print()

    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    for result in results:
        page = result["page"]

        if "error" in result:
            print(f"Page {page}: ERROR — {result['error']}")
            continue

        print(
            f"Page {page}: "
            f"raw_length={result['raw_length']}, "
            f"slashes={result['starts_with_slashes']}, "
            f"json_fence={result['contains_json_fence']}, "
            f"ends_with_array={result['ends_with_json_array']}"
        )

    output_path = ROOT / "vision_production_3pages_4b_test_result.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print()
    print(f"Full diagnostic saved to:")
    print(output_path)


if __name__ == "__main__":
    main()
    