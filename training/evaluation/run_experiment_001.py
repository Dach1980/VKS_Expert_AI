from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training"
EXP = TRAINING / "datasets" / "experiment_001"
EVAL = TRAINING / "evaluation"

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "qwen3.5-9b"

TRACE_RELATIONS = {
    "supports_compliance",
    "supports_violation",
    "parameter_mismatch",
    "not_relevant",
    "missing_condition",
    "obsolete_normative_reference",
}
APPLICABILITY_VALUES = {"applicable", "not_applicable", "not_proven"}

SYSTEM_PROMPT = """Ты — AI Engineer для проверки проектно-строительной документации по нормативной базе.

Работай только с данными, которые переданы в текущем запросе.
Главное правило: семантическое сходство с нормативным текстом не доказывает применимость.

КРИТИЧЕСКИЙ ПОРЯДОК ПРОВЕРКИ:
1. Определи проектный факт и его точный параметр.
2. Выбери только кандидата, относящегося к тому же system, segment, object и parameter.
3. СНАЧАЛА проверь все обязательные applicability conditions кандидата.
4. Если хотя бы одно обязательное условие не доказано проектными фактами, applicability = not_proven и decision = unchecked.
5. Не выбирай благоприятную ветвь условного требования по предположению. Отсутствие доказательства условия не означает, что условие выполнено.
6. ТОЛЬКО после доказательства applicability сравнивай проектное значение с нормативным значением.
7. Если нормативная ссылка проекта является замененной/неактуальной и это отдельное требование, проверяй её независимо от числового совпадения других параметров.

Не превращай идентификаторы объектов, номера колодцев, листов или пунктов в измеряемые инженерные значения.
Не придумывай нормативные пункты, значения, условия или факты проекта.

ФОРМАТ:
Верни ТОЛЬКО JSON-объект следующего вида:
{
  "decision": "compliant|violation|unchecked",
  "selected_requirement_id": "EXP001-R... или null",
  "applicability": "applicable|not_applicable|not_proven",
  "confidence": 0.0,
  "reason": "краткое инженерное обоснование",
  "missing_evidence": ["..."],
  "evidence_trace": [
    {
      "fact_id": "EXP001-F...",
      "requirement_id": "EXP001-R...",
      "relation": "supports_compliance|supports_violation|parameter_mismatch|not_relevant|missing_condition|obsolete_normative_reference",
      "applicability": "applicable|not_applicable|not_proven",
      "missing_condition": "..." 
    }
  ]
}

Правила evidence_trace:
- Каждый элемент — объект, а не строка и не пара строк.
- fact_id и requirement_id должны быть точными ID из входных данных.
- relation описывает доказательную связь.
- missing_condition обязательно только для relation = missing_condition и должно содержать конкретное недоказанное условие.
- Не добавляй вымышленные ID.
- Для условного требования сначала фиксируй missing_condition, а не делай вывод по совпавшему числу.
"""


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL: {path}:{line_no}: {exc}") from exc
    return rows


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_data() -> tuple[dict, dict[str, dict], dict[str, dict], dict[str, dict]]:
    benchmark = read_json(EVAL / "experiment_001_benchmark.json")
    facts = {x["fact_id"]: x for x in read_jsonl(EXP / "facts.jsonl")}
    requirements = {x["requirement_id"]: x for x in read_jsonl(EXP / "requirements.jsonl")}
    cases = {x["case_id"]: x for x in read_jsonl(EXP / "cases.jsonl")}
    for x in read_jsonl(EXP / "negative_cases.jsonl"):
        cases[x["case_id"]] = x
    for x in read_jsonl(EVAL / "experiment_001_golden_cases.jsonl"):
        cases[x["case_id"]] = x
    return benchmark, facts, requirements, cases


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_qwen(base_url: str, model: str, payload: dict, timeout: int) -> tuple[str, dict]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ],
        "temperature": 0.1,
        "max_tokens": 1400,
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
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach LM Studio at {base_url}: {exc}") from exc

    response_json = json.loads(raw)
    content = response_json["choices"][0]["message"].get("content") or ""
    return content, response_json


def build_case_input(case: dict, facts: dict[str, dict], requirements: dict[str, dict]) -> dict:
    project_evidence = []
    for item in case.get("project_evidence", []):
        fact = facts.get(item.get("fact_id"))
        project_evidence.append({
            "fact_id": item.get("fact_id"),
            "source_page": item.get("source_page", item.get("page")),
            "evidence_text": item.get("evidence_text", ""),
            "context": item.get("context", item.get("source_context", "")),
            "structured_fact": fact,
        })

    normative_pool = []
    for req in requirements.values():
        conditional = req.get("requirement_type") == "conditional"
        conditions = []
        if req.get("condition"):
            conditions.append({
                "condition_id": f"{req['requirement_id']}-COND-01",
                "description": req["condition"],
                "required_for_applicability": True,
            })
        value_rules = []
        if req.get("normative_value") is not None:
            value_rules.append({
                "value": req.get("normative_value"),
                "unit": req.get("normative_unit"),
            })
        normative_pool.append({
            "requirement_id": req["requirement_id"],
            "document": req["document"],
            "version": req.get("version"),
            "clause": req["clause"],
            "requirement": req["requirement"],
            "requirement_type": req["requirement_type"],
            "scope": {
                "system": req.get("system"),
                "segment": req.get("segment"),
                "object": req.get("object"),
                "parameter": req.get("parameter"),
            },
            "applicability": {
                "conditions": conditions,
                "exceptions": [req["exception"]] if req.get("exception") else [],
                "must_be_proven": conditional or bool(conditions),
            },
            "value_rules": value_rules,
        })

    return {
        "case_id": case["case_id"],
        "discipline": case.get("discipline"),
        "check_id": case.get("check_id"),
        "project_evidence": project_evidence,
        "candidate_normative_requirements": normative_pool,
        "task": "Определи применимое нормативное требование и решение по проектному факту. Сначала докажи applicability, затем сравнивай нормативное значение. Если обязательное условие не доказано, выбери unchecked.",
    }


def validate_trace(trace: object, facts: dict[str, dict], requirements: dict[str, dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(trace, list):
        return False, ["evidence_trace must be an array"]
    for index, item in enumerate(trace):
        if not isinstance(item, dict):
            errors.append(f"trace[{index}] must be an object")
            continue
        required = {"fact_id", "requirement_id", "relation", "applicability"}
        missing = required - set(item)
        if missing:
            errors.append(f"trace[{index}] missing fields: {sorted(missing)}")
        if set(item) - required - {"missing_condition"}:
            errors.append(f"trace[{index}] contains unsupported fields")
        if item.get("fact_id") not in facts:
            errors.append(f"trace[{index}] unknown fact_id: {item.get('fact_id')}")
        if item.get("requirement_id") not in requirements:
            errors.append(f"trace[{index}] unknown requirement_id: {item.get('requirement_id')}")
        if item.get("relation") not in TRACE_RELATIONS:
            errors.append(f"trace[{index}] invalid relation: {item.get('relation')}")
        if item.get("applicability") not in APPLICABILITY_VALUES:
            errors.append(f"trace[{index}] invalid applicability: {item.get('applicability')}")
        if item.get("relation") == "missing_condition":
            if not isinstance(item.get("missing_condition"), str) or not item["missing_condition"].strip():
                errors.append(f"trace[{index}] missing_condition is required for missing_condition relation")
        elif "missing_condition" in item and item["missing_condition"] is not None:
            errors.append(f"trace[{index}] missing_condition is only allowed for missing_condition relation")
    return not errors, errors


def evaluate(prediction: dict, expected: dict, facts: dict[str, dict], requirements: dict[str, dict]) -> dict:
    expected_decision = expected["expected_decision"]
    expected_applicability = expected.get("expected_applicability")
    expected_selected = expected.get("expected_selected_requirement_id")
    expected_relations = set(expected.get("expected_trace_relations", []))
    actual = prediction.get("decision")
    actual_applicability = prediction.get("applicability")
    actual_selected = prediction.get("selected_requirement_id")
    trace = prediction.get("evidence_trace", [])
    trace_valid, trace_errors = validate_trace(trace, facts, requirements)

    selected_correct = actual_selected == expected_selected
    applicability_correct = expected_applicability is None or actual_applicability == expected_applicability

    trace_items = trace if isinstance(trace, list) else []
    selected_trace = [x for x in trace_items if isinstance(x, dict) and x.get("requirement_id") == expected_selected]
    relation_ok = True
    if expected_relations:
        relation_ok = any(x.get("relation") in expected_relations for x in selected_trace)
    if expected_selected is not None and not selected_trace:
        relation_ok = False
    if expected_applicability == "not_proven" and expected_selected is not None:
        relation_ok = relation_ok and any(
            x.get("relation") == "missing_condition" and x.get("applicability") == "not_proven"
            for x in selected_trace
        )

    trace_complete = trace_valid and relation_ok
    unsupported_violation = actual == "violation" and actual_applicability != "applicable"

    return {
        "decision_correct": actual == expected_decision,
        "false_violation_critical": expected.get("negative_case", False) and actual == "violation",
        "applicability_correct": applicability_correct,
        "selected_requirement_correct": selected_correct,
        "evidence_trace_valid": trace_valid,
        "evidence_trace_complete": trace_complete,
        "unsupported_violation": unsupported_violation,
        "trace_errors": trace_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Project Expert AI Experiment 001 against local Qwen.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default=str(EVAL / "experiment_001_run_latest.json"))
    args = parser.parse_args()

    benchmark, facts, requirements, cases = load_data()
    selected = benchmark["cases"]
    results = []

    print(f"Benchmark: {benchmark['benchmark_id']}")
    print(f"Model: {args.model}")
    print(f"Endpoint: {args.base_url}")
    print(f"Cases: {len(selected)}")

    for index, expected in enumerate(selected, 1):
        case_id = expected["case_id"]
        case = cases.get(case_id)
        if not case:
            raise RuntimeError(f"Case not found: {case_id}")
        print(f"[{index}/{len(selected)}] {case_id} ...", flush=True)
        payload = build_case_input(case, facts, requirements)
        try:
            raw, response_json = call_qwen(args.base_url, args.model, payload, args.timeout)
            try:
                prediction = json.loads(strip_fences(raw))
                parse_error = None
            except Exception as exc:
                prediction = {"decision": None, "raw_response": raw}
                parse_error = str(exc)
        except Exception as exc:
            prediction = {"decision": None}
            response_json = {}
            parse_error = str(exc)
            raw = ""

        checks = evaluate(prediction, expected, facts, requirements) if prediction.get("decision") else {
            "decision_correct": False,
            "false_violation_critical": False,
            "applicability_correct": False,
            "selected_requirement_correct": False,
            "evidence_trace_valid": False,
            "evidence_trace_complete": False,
            "unsupported_violation": False,
            "trace_errors": [],
        }
        results.append({
            "case_id": case_id,
            "expected_decision": expected["expected_decision"],
            "expected_applicability": expected.get("expected_applicability"),
            "expected_selected_requirement_id": expected.get("expected_selected_requirement_id"),
            "negative_case": expected.get("negative_case", False),
            "prediction": prediction,
            "checks": checks,
            "raw_response": raw,
            "parse_error": parse_error,
        })
        status = "OK" if checks["decision_correct"] and checks["applicability_correct"] and checks["evidence_trace_complete"] else "FAIL"
        print(f"    {status}: expected={expected['expected_decision']} actual={prediction.get('decision')}")

    total = len(results)
    correct = sum(r["checks"]["decision_correct"] for r in results)
    critical = sum(r["checks"]["false_violation_critical"] for r in results)
    applicability_correct = sum(r["checks"]["applicability_correct"] for r in results)
    selected_correct = sum(r["checks"]["selected_requirement_correct"] for r in results)
    traced = sum(r["checks"]["evidence_trace_complete"] for r in results)
    trace_valid = sum(r["checks"]["evidence_trace_valid"] for r in results)
    unsupported = sum(r["checks"]["unsupported_violation"] for r in results)
    expected_unchecked = sum(r["expected_decision"] == "unchecked" for r in results)
    actual_unchecked = sum(r["prediction"].get("decision") == "unchecked" for r in results)
    correct_unchecked = sum(r["checks"]["decision_correct"] and r["expected_decision"] == "unchecked" for r in results)
    negative_total = sum(1 for r in results if r["negative_case"])

    summary = {
        "benchmark_id": benchmark["benchmark_id"],
        "model": args.model,
        "endpoint": args.base_url,
        "total_cases": total,
        "decision_accuracy": correct / total if total else 0.0,
        "false_violation_rate": critical / negative_total if negative_total else 0.0,
        "unsupported_violation_rate": unsupported / total if total else 0.0,
        "unchecked_precision": correct_unchecked / actual_unchecked if actual_unchecked else 0.0,
        "unchecked_recall": correct_unchecked / expected_unchecked if expected_unchecked else 0.0,
        "normative_applicability_accuracy": applicability_correct / total if total else 0.0,
        "selected_requirement_accuracy": selected_correct / total if total else 0.0,
        "evidence_trace_completeness": traced / total if total else 0.0,
        "evidence_trace_validity": trace_valid / total if total else 0.0,
        "critical_failure": critical > 0,
    }
    output = {
        "run_type": "AI_ENGINEER_BENCHMARK",
        "benchmark": benchmark,
        "summary": summary,
        "results": results,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved: {output_path}")
    return 2 if summary["critical_failure"] else 0


if __name__ == "__main__":
    sys.exit(main())
