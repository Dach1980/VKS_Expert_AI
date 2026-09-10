from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "training" / "evaluation"

# Reuse the production benchmark runner's data loading, input construction,
# Qwen call parameters and evaluator. Only SYSTEM_PROMPT is replaced below.
sys.path.insert(0, str(EVAL))
import run_experiment_001 as base  # noqa: E402


EVIDENCE_CONTRACT_V1 = base.SYSTEM_PROMPT.replace(
    "Правила evidence_trace:\n",
    """ПРАВИЛА ДОКАЗАТЕЛЬСТВА ПРИМЕНИМОСТИ:\n
Applicability condition считается доказанным, если project evidence содержит
прямое текстовое указание на выполнение этого условия.

Прямая нормативная ссылка является достаточным доказательством того, что
проект использует нормативный документ как нормативное основание конкретного
проектного решения, если evidence одновременно:
1. явно указывает нормативный документ;
2. содержит ссылку на его пункт, раздел или требование либо использует
   формулировку "согласно", "в соответствии с", "на основании" или
   "по требованиям";
3. ссылка относится к конкретному проектному решению, описанному в evidence.

Например, фраза:
"согласно п. 8.2.15 СП 30.13330.2012"
является прямой нормативной ссылкой и доказывает условие:
"проект прямо использует СП 30.13330.2012 как нормативное основание".

Если такая прямая нормативная ссылка присутствует, НЕ требуй отдельной
фразы "нормативное основание" и НЕ переводи applicability в not_proven.

Отличай прямую нормативную ссылку от простого упоминания документа.
Простое упоминание СП в перечне нормативных документов, литературе,
описании документа или без связи с конкретным проектным решением само по
себе не доказывает applicability.

Если прямой нормативной ссылкой доказано обязательное applicability condition,
установи applicability = applicable и продолжай проверку требования.

Правила evidence_trace:\n""",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="EXP001 G001: evidence-contract-only experiment against local Qwen."
    )
    parser.add_argument("--base-url", default=base.DEFAULT_BASE_URL)
    parser.add_argument("--model", default="qwen3.5-4b")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--output",
        default=str(EVAL / "experiment_004_g001_evidence_contract_v1_qwen35-4b.json"),
    )
    args = parser.parse_args()

    benchmark, facts, requirements, cases = base.load_data()
    expected = next(x for x in benchmark["cases"] if x["case_id"] == "EXP001-G001")
    case = cases["EXP001-G001"]

    payload = base.build_case_input(case, facts, requirements)

    # Critical experimental isolation: use the same call_qwen(), which keeps
    # temperature=0.1 and enable_thinking=False. Only the system prompt changes.
    base.SYSTEM_PROMPT = EVIDENCE_CONTRACT_V1
    raw, response_json = base.call_qwen(args.base_url, args.model, payload, args.timeout)

    try:
        prediction = json.loads(base.strip_fences(raw))
        parse_error = None
    except json.JSONDecodeError as exc:
        prediction = {}
        parse_error = str(exc)

    checks = base.evaluate(prediction, expected, facts, requirements)

    result = {
        "run_type": "AI_ENGINEER_SINGLE_CASE_EXPERIMENT",
        "experiment_id": "EXP001-G001-EVIDENCE-CONTRACT-V1",
        "benchmark_id": benchmark["benchmark_id"],
        "case_id": "EXP001-G001",
        "model": args.model,
        "endpoint": args.base_url,
        "temperature": 0.1,
        "enable_thinking": False,
        "scope": {
            "input_construction": "unchanged from EXP001 v2.1",
            "facts": ["EXP001-F009"],
            "candidate_requirements": ["EXP001-R001"],
            "evaluator": "unchanged: training/evaluation/run_experiment_001.py",
            "changed_component": "SYSTEM_PROMPT evidence contract only",
        },
        "expected": expected,
        "system_prompt": EVIDENCE_CONTRACT_V1,
        "input_payload": payload,
        "prediction": prediction,
        "checks": checks,
        "raw_response": raw,
        "response_json": response_json,
        "parse_error": parse_error,
    }

    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Experiment: EXP001-G001-EVIDENCE-CONTRACT-V1")
    print(f"Model: {args.model}")
    print(f"Endpoint: {args.base_url}")
    print("Input: F009 + R001")
    print("Evaluator: unchanged")
    print(f"decision: {prediction.get('decision')}")
    print(f"applicability: {prediction.get('applicability')}")
    print(f"selected_requirement_id: {prediction.get('selected_requirement_id')}")
    trace = prediction.get("evidence_trace") or []
    relations = [x.get("relation") for x in trace if isinstance(x, dict)]
    print(f"trace_relations: {relations}")
    print(f"checks: {json.dumps(checks, ensure_ascii=False)}")
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
