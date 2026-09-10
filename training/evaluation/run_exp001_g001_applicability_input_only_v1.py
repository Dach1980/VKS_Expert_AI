from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_experiment_001 import (
    DEFAULT_BASE_URL,
    build_case_input,
    call_qwen,
    evaluate,
    load_data,
    strip_fences,
)
from run_exp001_g001_evidence_resolution_v1 import resolve_normative_reference

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training"
EXP = TRAINING / "datasets" / "experiment_001"
EVAL = TRAINING / "evaluation"

EXPERIMENT_ID = "EXP001-G001-APPLICABILITY-INPUT-ONLY-V1"
EXPERIMENT_MODEL = "qwen3.5-4b"
OUTPUT_DEFAULT = EVAL / "experiment_007_g001_applicability_input_only_v1_qwen35-4b.json"

# EXP007 is a strict control experiment against EXP005.
# Only the user-input payload is changed: a deterministic applicability
# resolution is added. System prompt, model, call parameters, output schema,
# evaluator, benchmark, facts and requirements remain those of EXP005/base.


def resolve_applicability(reference: dict, requirement: dict) -> dict:
    """Resolve R001 applicability deterministically without using the golden answer."""
    condition = requirement.get("condition", "")
    document_match = reference.get("document") == "СП 30.13330.2012"
    direct_reference = reference.get("reference_type") == "direct"
    project_decision_target = reference.get("reference_target") == "project_decision"
    condition_text_match = "СП 30.13330.2012" in condition

    condition_proven = bool(
        document_match
        and direct_reference
        and project_decision_target
        and condition_text_match
    )

    return {
        "condition_id": f"{requirement['requirement_id']}-COND-01",
        "condition_proven": condition_proven,
        "resolved_applicability": "applicable" if condition_proven else "not_proven",
        "basis": {
            "document_match": document_match,
            "direct_reference": direct_reference,
            "reference_target": project_decision_target,
            "condition_document_match": condition_text_match,
        },
    }


def build_experiment_input(
    case: dict,
    facts: dict[str, dict],
    requirements: dict[str, dict],
) -> tuple[dict, dict]:
    # Start from the exact EXP005/base input construction.
    payload = build_case_input(case, facts, requirements)

    fact_ref = case["project_evidence"][0]
    fact = facts[fact_ref["fact_id"]]
    requirement_id = case["normative_evidence"][0]["requirement_id"]
    requirement = requirements[requirement_id]

    # EXP005 deterministic evidence resolution: same observed-evidence layer.
    evidence_resolution = resolve_normative_reference(
        fact.get("evidence_text", ""),
        fact.get("source_context", ""),
    )

    # EXP007 adds exactly one new input-level factor: deterministic
    # applicability resolution. It does not write the golden answer into the
    # case and does not alter the evaluator or system prompt.
    applicability_resolution = resolve_applicability(
        evidence_resolution,
        requirement,
    )
    if not applicability_resolution["condition_proven"]:
        raise RuntimeError(
            "EXP007 precondition failed: R001 applicability was not deterministically proven"
        )

    payload["evidence_resolution"] = [
        {
            "fact_id": fact["fact_id"],
            "normative_reference": evidence_resolution,
        }
    ]
    payload["project_evidence"][0]["evidence_resolution"] = {
        "normative_reference": evidence_resolution,
    }
    payload["applicability_resolution"] = applicability_resolution
    payload["applicability_resolved"] = "applicable"

    metadata = {
        "fact_id": fact["fact_id"],
        "requirement_id": requirement["requirement_id"],
        "normative_reference": evidence_resolution,
        "applicability_resolution": applicability_resolution,
    }
    return payload, metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run strict EXP007 G001 input-only applicability experiment against local Qwen3.5-4B."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=EXPERIMENT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT))
    args = parser.parse_args()

    benchmark, facts, requirements, cases = load_data()
    expected = next(x for x in benchmark["cases"] if x["case_id"] == "EXP001-G001")
    case = cases["EXP001-G001"]

    payload, resolver_meta = build_experiment_input(case, facts, requirements)

    # Critical isolation: use the unchanged production call_qwen(). This means
    # EXP007 inherits EXP005/base SYSTEM_PROMPT, temperature=0.1,
    # max_tokens=1400 and thinking-disabled settings.
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
        "max_tokens": 1400,
        "scope": {
            "baseline_experiment": "EXP001-G001-EVIDENCE-RESOLUTION-V1",
            "input_construction": "EXP005/base input plus applicability resolution fields only",
            "facts": ["EXP001-F009"],
            "candidate_requirements": ["EXP001-R001"],
            "evidence_resolution": "same as EXP005",
            "applicability_resolution": "new deterministic input factor",
            "system_prompt": "unchanged from EXP005/base runner",
            "evaluator": "unchanged: training/evaluation/run_experiment_001.py",
            "output_schema": "unchanged from EXP005/base runner",
            "production_pipeline": "unchanged",
            "benchmark": "unchanged",
            "model": "fixed qwen3.5-4b",
            "purpose": "test whether applicability resolution alone, as input, changes G001 classification",
        },
        "expected": expected,
        "resolver": resolver_meta,
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
    print("Case: EXP001-G001")
    print(f"Output: {output}")
    print(f"Condition proven: {resolver_meta['applicability_resolution']['condition_proven']}")
    print(f"Applicability resolved: {resolver_meta['applicability_resolution']['resolved_applicability']}")
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
