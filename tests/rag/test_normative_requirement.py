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
