from __future__ import annotations

import sys
import unittest
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parents[1]
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from run_experiment_001 import evaluate  # noqa: E402


FACTS = {
    "EXP001-F-G001": {"fact_id": "EXP001-F-G001"},
    "EXP001-F-G002": {"fact_id": "EXP001-F-G002"},
    "EXP001-F-G003": {"fact_id": "EXP001-F-G003"},
}

REQUIREMENTS = {
    "EXP001-R001": {"requirement_id": "EXP001-R001"},
    "EXP001-R002": {"requirement_id": "EXP001-R002"},
    "EXP001-R003": {"requirement_id": "EXP001-R003"},
}


def trace(fact_id: str, requirement_id: str, relation: str, applicability: str, missing_condition: str | None = None) -> dict:
    item = {
        "fact_id": fact_id,
        "requirement_id": requirement_id,
        "relation": relation,
        "applicability": applicability,
    }
    if missing_condition is not None:
        item["missing_condition"] = missing_condition
    return item


def expected(case_id: str, decision: str, applicability: str, requirement_id: str, relation: str, negative_case: bool = False) -> dict:
    return {
        "case_id": case_id,
        "expected_decision": decision,
        "expected_applicability": applicability,
        "expected_selected_requirement_id": requirement_id,
        "expected_trace_relations": [relation],
        "negative_case": negative_case,
    }


class Exp001EvaluatorTests(unittest.TestCase):
    def assert_pass(self, prediction: dict, golden: dict) -> None:
        checks = evaluate(prediction, golden, FACTS, REQUIREMENTS)
        self.assertTrue(checks["decision_correct"], checks)
        self.assertTrue(checks["applicability_correct"], checks)
        self.assertTrue(checks["selected_requirement_correct"], checks)
        self.assertTrue(checks["evidence_trace_valid"], checks)
        self.assertTrue(checks["evidence_trace_complete"], checks)
        self.assertFalse(checks["unsupported_violation"], checks)

    def assert_fail(self, prediction: dict, golden: dict) -> None:
        checks = evaluate(prediction, golden, FACTS, REQUIREMENTS)
        self.assertFalse(
            checks["decision_correct"]
            and checks["applicability_correct"]
            and checks["selected_requirement_correct"]
            and checks["evidence_trace_valid"]
            and checks["evidence_trace_complete"]
        )

    def test_g003_correct_trace_passes(self) -> None:
        golden = expected(
            "EXP001-G003", "unchecked", "not_proven", "EXP001-R003", "missing_condition"
        )
        prediction = {
            "decision": "unchecked",
            "selected_requirement_id": "EXP001-R003",
            "applicability": "not_proven",
            "confidence": 0.95,
            "reason": "Roof type is not proven, so the conditional requirement cannot be applied.",
            "missing_evidence": ["roof_type"],
            "evidence_trace": [
                trace(
                    "EXP001-F-G003",
                    "EXP001-R003",
                    "missing_condition",
                    "not_proven",
                    "type of roof",
                )
            ],
        }
        self.assert_pass(prediction, golden)

    def test_g003_wrong_trace_fails(self) -> None:
        golden = expected(
            "EXP001-G003", "unchecked", "not_proven", "EXP001-R003", "missing_condition"
        )
        prediction = {
            "decision": "unchecked",
            "selected_requirement_id": "EXP001-R003",
            "applicability": "not_proven",
            "confidence": 0.95,
            "reason": "The value is 0.2 m.",
            "missing_evidence": [],
            "evidence_trace": [
                trace("EXP001-F-G003", "EXP001-R003", "supports_compliance", "applicable")
            ],
        }
        self.assert_fail(prediction, golden)

    def test_g002_correct_passes(self) -> None:
        golden = expected(
            "EXP001-G002", "compliant", "applicable", "EXP001-R002", "supports_compliance"
        )
        prediction = {
            "decision": "compliant",
            "selected_requirement_id": "EXP001-R002",
            "applicability": "applicable",
            "confidence": 0.95,
            "reason": "Polypropylene is permitted by the applicable requirement.",
            "missing_evidence": [],
            "evidence_trace": [
                trace("EXP001-F-G002", "EXP001-R002", "supports_compliance", "applicable")
            ],
        }
        self.assert_pass(prediction, golden)

    def test_g002_wrong_trace_fails(self) -> None:
        golden = expected(
            "EXP001-G002", "compliant", "applicable", "EXP001-R002", "supports_compliance"
        )
        prediction = {
            "decision": "violation",
            "selected_requirement_id": "EXP001-R002",
            "applicability": "applicable",
            "confidence": 0.95,
            "reason": "Wrong material.",
            "missing_evidence": [],
            "evidence_trace": [
                trace("EXP001-F-G002", "EXP001-R002", "supports_violation", "applicable")
            ],
        }
        self.assert_fail(prediction, golden)

    def test_g001_obsolete_reference_passes(self) -> None:
        golden = expected(
            "EXP001-G001", "violation", "applicable", "EXP001-R001", "obsolete_normative_reference"
        )
        prediction = {
            "decision": "violation",
            "selected_requirement_id": "EXP001-R001",
            "applicability": "applicable",
            "confidence": 0.98,
            "reason": "The project references superseded SP 30.13330.2012 instead of the current base.",
            "missing_evidence": [],
            "evidence_trace": [
                trace(
                    "EXP001-F-G001",
                    "EXP001-R001",
                    "obsolete_normative_reference",
                    "applicable",
                )
            ],
        }
        self.assert_pass(prediction, golden)

    def test_g001_ordinary_technical_trace_fails(self) -> None:
        golden = expected(
            "EXP001-G001", "violation", "applicable", "EXP001-R001", "obsolete_normative_reference"
        )
        prediction = {
            "decision": "violation",
            "selected_requirement_id": "EXP001-R001",
            "applicability": "applicable",
            "confidence": 0.98,
            "reason": "A technical parameter does not match.",
            "missing_evidence": [],
            "evidence_trace": [
                trace("EXP001-F-G001", "EXP001-R001", "supports_violation", "applicable")
            ],
        }
        self.assert_fail(prediction, golden)


if __name__ == "__main__":
    unittest.main(verbosity=2)
