from app.rag.normative_requirement import extract_requirement, select_normative_requirements


def test_extract_requirement_recovers_two_component_clause_from_json20_metadata():
    result = {
        "norm_number": "СП 30.13330.2020",
        "version": "SP_30_test",
        "page": 57,
        "content": {
            "text": (
                "18.34 Диаметр и уклон выпуска следует определять расчетом. "
                "Конструктивно диаметр выпуска должен быть не меньше диаметра "
                "наибольшего из стояков, присоединяемых к выпуску."
            )
        },
        "metadata": {
            "normative_json": {
                "clause_ids": ["18.34"],
                "requirement_ids": ["SP_30:req:18.34:1"],
                "reference_ids": [],
            }
        },
    }

    item = extract_requirement(result, "диаметр выпуска")

    assert item["clause"] == "18.34"
    assert item["norm"] == "СП 30.13330.2020"
    assert item["requirement"]
    assert item["operator"] == ">="


def test_select_normative_requirements_keeps_clause_1834():
    result = {
        "norm_number": "СП 30.13330.2020",
        "version": "SP_30_test",
        "page": 57,
        "content": {
            "text": (
                "18.34 Диаметр и уклон выпуска следует определять расчетом. "
                "Конструктивно диаметр выпуска должен быть не меньше диаметра "
                "наибольшего из стояков, присоединяемых к выпуску."
            )
        },
        "metadata": {
            "normative_json": {
                "clause_ids": ["18.34"],
                "requirement_ids": ["SP_30:req:18.34:1"],
                "reference_ids": [],
            }
        },
    }

    selected = select_normative_requirements([result], "диаметр выпуска")

    assert len(selected) == 1
    assert selected[0]["clause"] == "18.34"
    assert selected[0]["has_concrete_clause"] is True


def test_extract_requirement_uses_chunk_clause_over_page_scope():
    result = {
        "norm_number": "СП 30.13330.2020",
        "version": "SP_30_test",
        "page": 57,
        "content": {
            "text": (
                "18.34 Диаметр и уклон выпуска следует определять расчетом. "
                "Конструктивно диаметр выпуска должен быть не меньше диаметра "
                "наибольшего из стояков, присоединяемых к выпуску."
            )
        },
        "metadata": {
            "normative_json": {
                "clause_ids": ["18.33", "18.34", "18.35", "18.36"],
                "requirement_ids": [],
                "reference_ids": [],
            }
        },
    }

    item = extract_requirement(result, "диаметр выпуска")

    assert item["clause"] == "18.34"
    assert item["requirement"].startswith("18.34 ")
    assert "18.33" not in item["requirement"]


def test_extract_requirement_splits_multi_clause_chunk():
    result = {
        "norm_number": "СП 30.13330.2020",
        "version": "SP_30_test",
        "page": 57,
        "content": {
            "text": (
                "18.33 Общие положения выпуска. "
                "18.34 Диаметр и уклон выпуска следует определять расчетом. "
                "Конструктивно диаметр выпуска должен быть не меньше диаметра "
                "наибольшего из стояков, присоединяемых к выпуску. "
                "18.36 Длина выпуска определяется условиями."
            )
        },
        "metadata": {
            "normative_json": {
                "clause_ids": ["18.33", "18.34", "18.36"],
                "requirement_ids": [],
                "reference_ids": [],
            }
        },
    }

    item = extract_requirement(result, "диаметр выпуска")

    assert item["clause"] == "18.34"
    assert item["requirement"].startswith("18.34 ")
    assert "18.36" not in item["requirement"]


def test_extract_requirement_uses_exact_segment_for_numeric_rule():
    result = {
        "norm_number": "СП 30.13330.2020",
        "version": "SP_30_test",
        "page": 57,
        "content": {
            "text": (
                "18.33 Общий текст без числа. "
                "18.34 Диаметр выпуска должен быть не меньше 110 мм. "
                "18.36 Длина выпуска 12 м."
            )
        },
        "metadata": {
            "normative_json": {
                "clause_ids": ["18.33", "18.34", "18.36"],
                "requirement_ids": [],
                "reference_ids": [],
            }
        },
    }

    item = extract_requirement(result, "диаметр выпуска")

    assert item["clause"] == "18.34"
    assert item["operator"] == ">="
    assert item["normative_value"] == 110.0
    assert item["normative_unit"] == "мм"
