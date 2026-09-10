from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "datasets" / "experiment_001"
EVAL = ROOT / "evaluation"

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "qwen3.5-9b"

SYSTEM_PROMPT = """Ты — AI Engineer для проверки проектно-строительной документации по нормативной базе.

Работай только с данными, которые переданы в текущем запросе.
Главное правило: семантическое сходство с нормативным текстом не доказывает применимость.
Перед решением отдельно проверь system, segment, object, parameter и условия/исключения.
Если применимое требование не доказано или не хватает условия для выбора требования, решение должно быть unchecked.
Не превращай идентификаторы объектов, номера колодцев, листов или пунктов в измеряемые инженерные значения.
Не придумывай нормативные пункты, значения, условия или факты проекта.

Верни ТОЛЬКО JSON-объект следующего вида:
{
  "decision": "compliant|violation|unchecked",
  "selected_requirement_id": "EXP001-R... или null",
  "applicability": "applicable|not_applicable|not_proven",
  "confidence": 0.0,
  "reason": "краткое инженерное обоснование",
  "missing_evidence": ["..."],
  "evidence_trace": ["fact_id", "requirement_id"]
}
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

    # Deliberately expose the normative pool without revealing which requirement,
    # if any, is the expected answer. This tests applicability selection.
    normative_pool = []
    for req in requirements.values():
        normative_pool.append({
            "requirement_id": req["requirement_id"],
            "document": req["document"],
            "clause": req["clause"],
            "requirement": req["requirement"],
            "requirement_type": req["requirement_type"],
            "system": req.get("system"),
            "segment": req.get("segment"),
            "object": req.get("object"),
            "parameter": req.get("parameter"),
            "condition": req.get("condition"),
            "exception": req.get("exception"),
            "normative_value": req.get("normative_value"),
            "normative_unit": req.get("normative_unit"),
        })

    return {
        "case_id": case["case_id"],
        "discipline": case.get("discipline"),
        "check_id": case.get("check_id"),
        "project_evidence": project_evidence,
        "candidate_normative_requirements": normative_pool,
        "task": "Определи применимое нормативное требование и решение по проектному факту. Если доказательств недостаточно, выбери unchecked.",
    }


def evaluate(prediction: dict, expected: dict) -> dict:
    expected_decision = expected["expected_decision"]
    actual = prediction.get("decision")
    return {
        "decision_correct": actual == expected_decision,
        "false_violation_critical": expected.get("negative_case", False) and actual == "violation",
        "applicability_present": prediction.get("applicability") in {"applicable", "not_applicable", "not_proven"},
        "evidence_trace_complete": bool(prediction.get("evidence_trace")),
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

        checks = evaluate(prediction, expected) if prediction.get("decision") else {
            "decision_correct": False,
            "false_violation_critical": False,
            "applicability_present": False,
            "evidence_trace_complete": False,
        }
        results.append({
            "case_id": case_id,
            "expected_decision": expected["expected_decision"],
            "negative_case": expected.get("negative_case", False),
            "prediction": prediction,
            "checks": checks,
            "raw_response": raw,
            "parse_error": parse_error,
        })
        status = "OK" if checks["decision_correct"] else "FAIL"
        print(f"    {status}: expected={expected['expected_decision']} actual={prediction.get('decision')}")

    total = len(results)
    correct = sum(r["checks"]["decision_correct"] for r in results)
    critical = sum(r["checks"]["false_violation_critical"] for r in results)
    applicable = sum(r["checks"]["applicability_present"] for r in results)
    traced = sum(r["checks"]["evidence_trace_complete"] for r in results)
    summary = {
        "benchmark_id": benchmark["benchmark_id"],
        "model": args.model,
        "endpoint": args.base_url,
        "total_cases": total,
        "decision_accuracy": correct / total if total else 0.0,
        "false_violation_rate": critical / sum(1 for r in results if r["negative_case"]) if any(r["negative_case"] for r in results) else 0.0,
        "applicability_field_valid_rate": applicable / total if total else 0.0,
        "evidence_trace_completeness": traced / total if total else 0.0,
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
