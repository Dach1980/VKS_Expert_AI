from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from run_experiment_001 import (
    DEFAULT_BASE_URL,
    build_case_input,
    call_qwen,
    evaluate,
    load_data,
    strip_fences,
)

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training"
EXP = TRAINING / "datasets" / "experiment_001"
EVAL = TRAINING / "evaluation"

EXPERIMENT_ID = "EXP001-G001-EVIDENCE-RESOLUTION-V1"
EXPERIMENT_MODEL = "qwen3.5-4b"
OUTPUT_DEFAULT = EVAL / "experiment_005_g001_evidence_resolution_v1_qwen35-4b.json"

# This experiment tests whether deterministic normalization of an observed
# normative reference helps the same Qwen3.5-4B reasoning pipeline resolve
# applicability. It must never emit the golden answer itself.


def resolve_normative_reference(evidence_text: str, context: str = "") -> dict:
    text = f"{evidence_text} {context}".strip()

    document_match = re.search(r"СП\s*30\.13330\.2012", text, flags=re.IGNORECASE)
    clause_match = re.search(r"п\.?\s*([0-9]+(?:\.[0-9]+)+)", text, flags=re.IGNORECASE)
    marker_match = re.search(
        r"\b(согласно|в\s+соответствии\s+с|на\s+основании|по\s+требованиям)\b",
        text,
        flags=re.IGNORECASE,
    )

    if not document_match:
        return {
            "reference_type": "none",
            "reference_target": "unknown",
            "document": None,
            "clause": None,
            "marker": None,
        }

    # 'direct' and 'project_decision' describe only observable linguistic
    # evidence: a named normative document, a clause marker, and a normative
    # marker in the same evidence. No applicability/decision is assigned here.
    direct = bool(clause_match and marker_match)
    return {
        "reference_type": "direct" if direct else "mention",
        "reference_target": "project_decision" if direct else "unknown",
        "document": document_match.group(0),
        "clause": clause_match.group(1) if clause_match else None,
        "marker": marker_match.group(1) if marker_match else None,
    }


def build_resolution_input(case: dict, facts: dict[str, dict], requirements: dict[str, dict]) -> tuple[dict, dict]:
    payload = build_case_input(case, facts, requirements)

    resolutions = []
    for item in payload["project_evidence"]:
        resolution = resolve_normative_reference(
            item.get("evidence_text", ""),
            item.get("context", ""),
        )
        item["evidence_resolution"] = {"normative_reference": resolution}
        resolutions.append({
            "fact_id": item.get("fact_id"),
            "normative_reference": resolution,
        })

    payload["evidence_resolution"] = resolutions
    return payload, {"facts": resolutions}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated EXP001 G001 evidence-resolution experiment against local Qwen3.5-4B."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    # Keep the experiment model fixed for reproducibility. Do not inherit
    # DEFAULT_MODEL from the base runner, which may target another model.
    parser.add_argument("--model", default=EXPERIMENT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT))
    args = parser.parse_args()

    benchmark, facts, requirements, cases = load_data()
    expected = next(x for x in benchmark["cases"] if x["case_id"] == "EXP001-G001")
    case = cases["EXP001-G001"]

    payload, resolution_meta = build_resolution_input(case, facts, requirements)
    raw, response_json = call_qwen(args.base_url, args.model, payload, args.timeout)

    try:
        prediction = json.loads(strip_fences(raw))
        parse_error = None
    except json.JSONDecodeError as exc:
        prediction = {}
        parse_error = str(exc)

    checks = evaluate(prediction, expected, facts, requirements) if not parse_error else None

    artifact = {
        "run_type": "AI_ENGINEER_SINGLE_CASE_EXPERIMENT",
        "experiment_id": EXPERIMENT_ID,
        "benchmark_id": benchmark["benchmark_id"],
        "case_id": case["case_id"],
        "model": args.model,
        "endpoint": args.base_url,
        "temperature": 0.1,
        "enable_thinking": False,
        "scope": {
            "input_construction": "unchanged from EXP001 v2.1",
            "facts": ["EXP001-F009"],
            "candidate_requirements": ["EXP001-R001"],
            "evaluator": "unchanged: training/evaluation/run_experiment_001.py",
            "system_prompt": "unchanged from base runner",
            "changed_component": "deterministic evidence-resolution layer only",
        },
        "expected": expected,
        "evidence_resolution": resolution_meta,
        "input_payload": payload,
        "prediction": prediction,
        "checks": checks,
        "raw_response": raw,
        "response_json": response_json,
        "parse_error": parse_error,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Experiment: {EXPERIMENT_ID}")
    print(f"Model: {args.model}")
    print(f"Case: EXP001-G001")
    print(f"Output: {output}")
    print(f"Resolved normative reference: {resolution_meta['facts'][0]['normative_reference']}")
    if parse_error:
        print(f"Parse error: {parse_error}")
        return 1
    print(f"Decision: {prediction.get('decision')}")
    print(f"Applicability: {prediction.get('applicability')}")
    print(f"Selected requirement: {prediction.get('selected_requirement_id')}")
    print(f"Checks: {json.dumps(checks, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())