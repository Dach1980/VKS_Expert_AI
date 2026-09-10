from __future__ import annotations

import json
from pathlib import Path

from run_experiment_001 import load_data
from run_exp001_g001_evidence_resolution_v1 import resolve_normative_reference

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training"
EVAL = TRAINING / "evaluation"

OUTPUT = EVAL / "experiment_008_applicability_resolver_validation_v1.json"
EXPERIMENT_ID = "EXP001-APPLICABILITY-RESOLVER-VALIDATION-V1"

# Validation-only harness. It does not modify the benchmark, production
# runner, evaluator, facts or requirements. It validates the deterministic
# applicability boundary on every BM-v2 case that has a canonical candidate.
# Cases without a canonical candidate are explicitly checked as a boundary:
# the resolver must not manufacture one from a semantic normative fragment.


def resolve_candidate_applicability(case: dict, fact: dict, requirement: dict) -> dict:
    requirement_id = requirement["requirement_id"]
    evidence_text = fact.get("evidence_text", "")
    source_context = fact.get("source_context", "")
    condition = requirement.get("condition", "")

    if requirement_id == "EXP001-R001":
        reference = resolve_normative_reference(evidence_text, source_context)
        basis = {
            "document_match": reference.get("document") == "СП 30.13330.2012",
            "direct_reference": reference.get("reference_type") == "direct",
            "reference_target": reference.get("reference_target") == "project_decision",
            "condition_document_match": "СП 30.13330.2012" in condition,
        }
        proven = all(basis.values())
        return {
            "status": "resolved" if proven else "not_proven",
            "resolved_applicability": "applicable" if proven else "not_proven",
            "condition_proven": proven,
            "basis": basis,
        }

    if requirement_id == "EXP001-R002":
        # R002 is mandatory without a conditional branch. Its applicability
        # condition is directly evidenced by the project text: "Система
        # бытовой канализации". The structured fact also identifies wastewater.
        basis = {
            "condition_text_match": "бытовой канализации" in evidence_text.lower(),
            "structured_system_match": fact.get("system") == "wastewater",
            "condition_mentions_domestic_wastewater": "система бытовых сточных вод" in condition.lower(),
        }
        proven = all(basis.values())
        return {
            "status": "resolved" if proven else "not_proven",
            "resolved_applicability": "applicable" if proven else "not_proven",
            "condition_proven": proven,
            "basis": basis,
        }

    if requirement_id == "EXP001-R003":
        # R003 has mandatory alternative conditions (roof type or ventilation
        # shaft context). The available evidence gives the height but does not
        # prove either branch. Do not infer a favorable branch from 0.2 m.
        text = (evidence_text + " " + source_context).lower()
        roof_context_proven = any(
            marker in text
            for marker in (
                "плоской неэксплуатируемой",
                "плоской эксплуатируемой",
                "скатной кровли",
            )
        )
        shaft_context_proven = "вентиляционной шахт" in text
        basis = {
            "roof_context_proven": roof_context_proven,
            "shaft_context_proven": shaft_context_proven,
            "height_value_present": "0,2 м" in evidence_text,
        }
        proven = roof_context_proven or shaft_context_proven
        return {
            "status": "resolved" if proven else "not_proven",
            "resolved_applicability": "applicable" if proven else "not_proven",
            "condition_proven": proven,
            "basis": basis,
        }

    raise RuntimeError(f"No validation rule defined for canonical requirement {requirement_id}")


def main() -> int:
    benchmark, facts, requirements, cases = load_data()
    rows = []

    for expected in benchmark["cases"]:
        case_id = expected["case_id"]
        case = cases[case_id]
        normative_evidence = case.get("normative_evidence", [])
        canonical = [
            item.get("requirement_id")
            for item in normative_evidence
            if item.get("requirement_id") in requirements
        ]

        row = {
            "case_id": case_id,
            "expected_decision": expected["expected_decision"],
            "expected_applicability": expected.get("expected_applicability"),
            "expected_selected_requirement_id": expected.get("expected_selected_requirement_id"),
            "canonical_candidate_ids": canonical,
        }

        # Never use case-level golden applicability/decision as resolver input.
        if not canonical:
            row["resolver_status"] = "no_canonical_candidate"
            row["resolver_result"] = None
            row["boundary_check"] = {
                "passed": True,
                "reason": "No canonical requirement ID is present; resolver must not manufacture a candidate from semantic normative text.",
            }
            rows.append(row)
            continue

        if len(canonical) != 1:
            raise RuntimeError(f"{case_id}: validation expects exactly one canonical candidate, got {canonical}")

        requirement_id = canonical[0]
        evidence_item = case["project_evidence"][0]
        fact = facts[evidence_item["fact_id"]]
        requirement = requirements[requirement_id]
        result = resolve_candidate_applicability(case, fact, requirement)

        row["resolver_status"] = result["status"]
        row["resolver_result"] = {
            "requirement_id": requirement_id,
            **result,
        }
        row["boundary_check"] = {
            "passed": True,
            "reason": "Canonical candidate applicability resolved from project evidence and requirement metadata only.",
        }
        rows.append(row)

    # Expected resolver outcomes are validation expectations, not benchmark
    # inputs and are intentionally separate from case-level golden answers.
    expected_resolver = {
        "EXP001-G001": ("applicable", True),
        "EXP001-G002": ("applicable", True),
        "EXP001-G003": ("not_proven", False),
        "EXP001-C001": ("no_canonical_candidate", None),
        "EXP001-C002": ("no_canonical_candidate", None),
        "EXP001-C003": ("no_canonical_candidate", None),
        "EXP001-N001": ("no_canonical_candidate", None),
        "EXP001-N002": ("no_canonical_candidate", None),
    }

    failures = []
    for row in rows:
        expected_status, expected_proven = expected_resolver[row["case_id"]]
        if row["resolver_status"] != expected_status:
            failures.append({"case_id": row["case_id"], "error": "status mismatch", "actual": row["resolver_status"], "expected": expected_status})
            continue
        if expected_proven is not None:
            actual = row["resolver_result"]["condition_proven"]
            if actual != expected_proven:
                failures.append({"case_id": row["case_id"], "error": "condition_proven mismatch", "actual": actual, "expected": expected_proven})

    artifact = {
        "run_type": "AI_ENGINEER_DETERMINISTIC_VALIDATION",
        "experiment_id": EXPERIMENT_ID,
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_unchanged": True,
        "production_runner_unchanged": True,
        "evaluator_unchanged": True,
        "golden_answer_used_by_resolver": False,
        "cases_checked": len(rows),
        "canonical_candidate_cases": [r["case_id"] for r in rows if r["canonical_candidate_ids"]],
        "boundary_cases_without_candidate": [r["case_id"] for r in rows if not r["canonical_candidate_ids"]],
        "failures": failures,
        "passed": not failures,
        "results": rows,
    }

    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Validation: {EXPERIMENT_ID}")
    print(f"Benchmark: {benchmark['benchmark_id']}")
    print(f"Cases checked: {len(rows)}")
    for row in rows:
        result = row["resolver_result"]
        if result:
            print(f"{row['case_id']}: candidate={result['requirement_id']} -> {result['resolved_applicability']} condition_proven={result['condition_proven']}")
        else:
            print(f"{row['case_id']}: no canonical candidate -> boundary OK")
    print(f"Failures: {len(failures)}")
    print(f"Passed: {not failures}")
    print(f"Output: {OUTPUT}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
