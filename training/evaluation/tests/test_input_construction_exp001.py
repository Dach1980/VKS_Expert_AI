from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

from run_experiment_001 import build_case_input, load_data


class InputConstructionExp001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.facts, cls.requirements, cls.cases = load_data()

    def candidate_ids(self, case_id: str) -> list[str]:
        payload = build_case_input(self.cases[case_id], self.facts, self.requirements)
        return [item["requirement_id"] for item in payload["candidate_normative_requirements"]]

    def payload(self, case_id: str) -> dict:
        return build_case_input(self.cases[case_id], self.facts, self.requirements)

    def test_g001_only_r001_is_passed(self) -> None:
        self.assertEqual(self.candidate_ids("EXP001-G001"), ["EXP001-R001"])
        serialized = json.dumps(self.payload("EXP001-G001"), ensure_ascii=False)
        self.assertIn("EXP001-R001", serialized)
        self.assertNotIn("EXP001-R002", serialized)
        self.assertNotIn("EXP001-R003", serialized)

    def test_g002_only_r002_is_passed(self) -> None:
        self.assertEqual(self.candidate_ids("EXP001-G002"), ["EXP001-R002"])
        serialized = json.dumps(self.payload("EXP001-G002"), ensure_ascii=False)
        self.assertNotIn("СП 30.13330.2012", serialized)
        self.assertNotIn("EXP001-R001", serialized)
        self.assertNotIn("EXP001-R003", serialized)

    def test_g003_only_r003_is_passed(self) -> None:
        self.assertEqual(self.candidate_ids("EXP001-G003"), ["EXP001-R003"])

    def test_control_cases_have_empty_candidate_pool(self) -> None:
        for case_id in ("EXP001-C001", "EXP001-N001", "EXP001-N002"):
            self.assertEqual(self.candidate_ids(case_id), [], case_id)

    def test_case_applicability_is_not_passed_to_llm(self) -> None:
        case = {
            "case_id": "EXP001-TEST",
            "discipline": "ВК",
            "check_id": "TEST",
            "project_evidence": [],
            "normative_evidence": [{"requirement_id": "EXP001-R002"}],
            "applicability": {
                "applicable": True,
                "reason": "SECRET_GOLDEN_ANSWER",
            },
        }
        payload = build_case_input(case, self.facts, self.requirements)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("SECRET_GOLDEN_ANSWER", serialized)
        self.assertNotIn('"applicable": true', serialized)

    def test_unknown_requirement_id_fails_loudly(self) -> None:
        case = {
            "case_id": "EXP001-TEST",
            "project_evidence": [],
            "normative_evidence": [{"requirement_id": "EXP001-R999"}],
        }
        with self.assertRaisesRegex(RuntimeError, "unknown normative requirement"):
            build_case_input(case, self.facts, self.requirements)


if __name__ == "__main__":
    unittest.main()
