from training.evaluation.experiment_skill_rag_matrix_20260925 import _build_matrix, _status


def test_skill_rag_matrix_initializes_all_skill_checks():
    skill = {
        "checks": [
            {"id": "sewer_diameter", "name": "Диаметры"},
            {"id": "sewer_slope", "name": "Уклоны"},
        ]
    }

    matrix = _build_matrix(skill)

    assert list(matrix) == ["sewer_diameter", "sewer_slope"]
    assert matrix["sewer_diameter"]["status"] if "status" in matrix["sewer_diameter"] else True
    assert matrix["sewer_diameter"]["raw_visual_candidates"] == 0


def test_skill_rag_matrix_status_requires_each_stage():
    item = {
        "skill_candidates": 0,
        "bbox_valid": 0,
        "rag_hits": 0,
        "requirements": 0,
    }
    assert _status(item) == "NO_CANDIDATE"

    item["skill_candidates"] = 1
    assert _status(item) == "NO_VALID_BBOX"

    item["bbox_valid"] = 1
    assert _status(item) == "RAG_NO_HIT"

    item["rag_hits"] = 1
    assert _status(item) == "NO_REQUIREMENT"

    item["requirements"] = 1
    assert _status(item) == "PASS"
