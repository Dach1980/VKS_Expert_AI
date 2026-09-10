from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from run_experiment_001 import (
    DEFAULT_BASE_URL,
    evaluate,
    load_data,
    strip_fences,
)

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training"
EVAL = TRAINING / "evaluation"

EXPERIMENT_ID = "EXP006-G001-APPLICABILITY-RESOLVER-V1"
EXPERIMENT_MODEL = "qwen3.5-4b"
OUTPUT_DEFAULT = EVAL / "experiment_006_g001_applicability_resolver_v1_qwen35-4b.json"

# EXP006 is isolated. It must not modify the production runner, evaluator,
# benchmark, facts, requirements, RAG, or system prompt.
# The experiment moves applicability resolution out of the LLM path and tests
# whether the same Qwen3.5-4B model can classify the already-resolved case.

EXPERIMENT_SYSTEM_PROMPT = """Ты — AI Engineer для проверки проектно-строительной документации.

В этом эксперименте применимость нормативного требования уже ДОКАЗАНА внешним
детерминированным resolver и передана тебе как:
"applicability_resolved": "applicable".

НЕ переоценивай applicability и НЕ требуй дополнительных доказательств условия.
Считай R001 применимым. Твоя задача — определить только итоговое решение и тип
нарушения по уже применимому требованию.

Верни ТОЛЬКО JSON:
{
  "decision": "compliant|violation|unchecked",
  "violation_type": "obsolete_normative_reference|other|none",
  "reason": "краткое обоснование"
}

Для G001 проверь, нарушает ли проектная ссылка на СП 30.13330.2012 требование
R001 о действующей нормативной базе. Не придумывай факты и нормативные значения.
"""


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

    direct = bool(clause_match and marker_match)
    return {
        "reference_type": "direct" if direct else "mention",
        "reference_target": "project_decision" if direct else "unknown",
        "document": document_match.group(0),
        "clause": clause_match.group(1) if clause_match else None,
        "marker": marker_match.group(1) if marker_match else None,
    }


def resolve_applicability(reference: dict, requirement: dict) -> dict:
    """Deterministically resolve R001 applicability without using the golden answer."""
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


def build_experiment_input(case: dict, facts: dict[str, dict], requirements: dict[str, dict]) -> tuple[dict, dict]:
    fact_ref = case["project_evidence"][0]
    fact = facts[fact_ref["fact_id"]]
    requirement_id = case["normative_evidence"][0]["requirement_id"]
    requirement = requirements[requirement_id]

    evidence_resolution = resolve_normative_reference(
        fact.get("evidence_text", ""),
        fact.get("source_context", ""),
    )
    applicability_resolution = resolve_applicability(evidence_resolution, requirement)

    if not applicability_resolution["condition_proven"]:
        raise RuntimeError("EXP006 precondition failed: R001 applicability was not deterministically proven")

    payload = {
        "case_id": case["case_id"],
        "discipline": case.get("discipline"),
        "check_id": case.get("check_id"),
        "project_evidence": [{
            "fact_id": fact["fact_id"],
            "source_page": fact.get("source", {}).get("page"),
            "evidence_text": fact.get("evidence_text", ""),
            "context": fact.get("source_context", ""),
            "structured_fact": fact,
        }],
        "candidate_normative_requirements": [{
            "requirement_id": requirement["requirement_id"],
            "document": requirement["document"],
            "version": requirement.get("version"),
            "clause": requirement["clause"],
            "requirement": requirement["requirement"],
            "requirement_type": requirement["requirement_type"],
            "scope": {
                "system": requirement.get("system"),
                "segment": requirement.get("segment"),
                "object": requirement.get("object"),
                "parameter": requirement.get("parameter"),
            },
        }],
        "evidence_resolution": {
            "normative_reference": evidence_resolution,
        },
        "applicability_resolution": applicability_resolution,
        "applicability_resolved": "applicable",
        "task": "Определи только итоговое решение и тип нарушения по уже применимому требованию R001.",
    }

    metadata = {
        "fact_id": fact["fact_id"],
        "requirement_id": requirement["requirement_id"],
        "normative_reference": evidence_resolution,
        "applicability_resolution": applicability_resolution,
    }
    return payload, metadata


def call_experiment_qwen(base_url: str, model: str, payload: dict, timeout: int) -> tuple[str, dict]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXPERIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ],
        "temperature": 0.1,
        "max_tokens": 700,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_response = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach LM Studio at {base_url}: {exc}") from exc

    response_json = json.loads(raw_response)
    content = response_json["choices"][0]["message"].get("content") or ""
    return content, response_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated EXP006 G001 deterministic applicability resolver against local Qwen3.5-4B."
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

    raw, response_json = call_experiment_qwen(args.base_url, args.model, payload, args.timeout)

    try:
        model_output = json.loads(strip_fences(raw))
        parse_error = None
    except json.JSONDecodeError as exc:
        model_output = {}
        parse_error = str(exc)

    prediction = {
        "decision": model_output.get("decision"),
        "selected_requirement_id": resolver_meta["requirement_id"],
        "applicability": "applicable",
        "confidence": model_output.get("confidence", 1.0),
        "reason": model_output.get("reason", ""),
        "missing_evidence": [],
        "evidence_trace": [{
            "fact_id": resolver_meta["fact_id"],
            "requirement_id": resolver_meta["requirement_id"],
            "relation": "obsolete_normative_reference" if model_output.get("decision") == "violation" else "supports_compliance",
            "applicability": "applicable",
        }],
    }

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
            "input_construction": "isolated EXP006 only",
            "facts": ["EXP001-F009"],
            "candidate_requirements": ["EXP001-R001"],
            "deterministic_evidence_resolution": "enabled",
            "deterministic_applicability_resolution": "enabled",
            "condition_proven": True,
            "resolved_applicability": "applicable",
            "production_pipeline": "unchanged",
            "evaluator": "unchanged: training/evaluation/run_experiment_001.py",
            "benchmark": "unchanged",
            "model": "fixed qwen3.5-4b",
            "purpose": "test decision classification after applicability is resolved externally",
        },
        "expected": expected,
        "resolver": resolver_meta,
        "input_payload": payload,
        "model_output": model_output,
        "prediction_for_unchanged_evaluator": prediction,
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
    print(f"Evidence resolution: {json.dumps(resolver_meta['normative_reference'], ensure_ascii=False)}")
    print(f"Condition proven: {resolver_meta['applicability_resolution']['condition_proven']}")
    print(f"Applicability resolved: {resolver_meta['applicability_resolution']['resolved_applicability']}")
    if parse_error:
        print(f"Parse error: {parse_error}")
        return 1
    print(f"Model decision: {model_output.get('decision')}")
    print(f"Model violation type: {model_output.get('violation_type')}")
    print(f"Checks: {json.dumps(checks, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
