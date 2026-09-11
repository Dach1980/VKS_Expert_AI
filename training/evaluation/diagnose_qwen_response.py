from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

from run_experiment_001 import (
    SYSTEM_PROMPT,
    build_case_input,
    load_data,
)


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "qwen3.5-4b"
DEFAULT_CASE_ID = "EXP001-C001"
DEFAULT_MAX_TOKENS = 3000


def print_value(label: str, value) -> None:
    print(f"\n--- {label} ---")

    if isinstance(value, str):
        print(f"length: {len(value)}")
        print(repr(value))
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2))


def call_qwen_diagnostic(
    base_url: str,
    model: str,
    payload: dict,
    timeout: int,
    max_tokens: int,
) -> dict:
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "extra_body": {
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    }

    data = json.dumps(
        body,
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=timeout,
        ) as response:
            raw = response.read().decode("utf-8")

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise RuntimeError(
            f"HTTP {exc.code}: {detail}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach LM Studio at "
            f"{base_url}: {exc}"
        ) from exc

    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Step 8.0.2 — diagnose Qwen response "
            "with increased max_tokens."
        )
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--case-id",
        default=DEFAULT_CASE_ID,
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
    )

    args = parser.parse_args()

    print(
        "=== Step 8.0.2 — Qwen 4B "
        "max_tokens diagnostic ==="
    )

    print(f"Model: {args.model}")
    print(f"Case: {args.case_id}")
    print(f"Endpoint: {args.base_url}")
    print(f"Timeout: {args.timeout}s")
    print(f"max_tokens: {args.max_tokens}")

    benchmark, facts, requirements, cases = load_data()

    print(f"\nBenchmark: {benchmark['benchmark_id']}")
    print(f"Loaded facts: {len(facts)}")
    print(f"Loaded requirements: {len(requirements)}")
    print(f"Loaded cases: {len(cases)}")

    case = cases.get(args.case_id)

    if case is None:
        print(
            f"\nERROR: case not found: "
            f"{args.case_id}"
        )
        return 1

    payload = build_case_input(
        case,
        facts,
        requirements,
    )

    print("\nRequest prepared successfully.")
    print(
        "Project evidence items: "
        f"{len(payload.get('project_evidence', []))}"
    )
    print(
        "Normative candidate items: "
        f"{len(payload.get('candidate_normative_requirements', []))}"
    )

    try:
        response_json = call_qwen_diagnostic(
            base_url=args.base_url,
            model=args.model,
            payload=payload,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )

    except Exception as exc:
        print("\n=== REQUEST ERROR ===")
        print(type(exc).__name__)
        print(str(exc))
        return 2

    print("\n=== HTTP RESPONSE RECEIVED ===")

    print_value(
        "top-level response keys",
        list(response_json.keys()),
    )

    choices = response_json.get("choices")

    if not isinstance(choices, list):
        print("\nERROR: choices is not a list.")
        print_value(
            "full response",
            response_json,
        )
        return 3

    print(f"\nchoices count: {len(choices)}")

    if not choices:
        print("\nERROR: choices is empty.")
        return 4

    choice = choices[0]

    print_value(
        "choices[0] keys",
        list(choice.keys()),
    )

    print_value(
        "finish_reason",
        choice.get("finish_reason"),
    )

    message = choice.get("message")

    if not isinstance(message, dict):
        print(
            "\nERROR: message is not an object."
        )
        print_value(
            "choices[0]",
            choice,
        )
        return 5

    print_value(
        "message keys",
        list(message.keys()),
    )

    content = message.get("content")

    reasoning_content = message.get(
        "reasoning_content"
    )

    print_value(
        "message.content",
        content,
    )

    if "reasoning_content" in message:
        print_value(
            "message.reasoning_content",
            reasoning_content,
        )
    else:
        print(
            "\n--- message.reasoning_content ---"
        )
        print("FIELD NOT PRESENT")

    print_value(
        "usage",
        response_json.get("usage"),
    )

    print("\n=== FULL RAW RESPONSE JSON ===")

    print(
        json.dumps(
            response_json,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== STEP 8.0.2 SUMMARY ===")

    print(
        f"max_tokens requested: "
        f"{args.max_tokens}"
    )

    print(
        f"content length: "
        f"{len(content) if isinstance(content, str) else 'n/a'}"
    )

    print(
        "reasoning_content length: "
        f"{len(reasoning_content) if isinstance(reasoning_content, str) else 'n/a'}"
    )

    print(
        f"finish_reason: "
        f"{choice.get('finish_reason')!r}"
    )

    print(
        "\nNo benchmark result file was "
        "created or modified."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
