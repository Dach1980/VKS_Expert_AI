from app.checking.resilient import _multi_context


def test_multi_context_does_not_invent_numeric_value_for_relational_requirement():
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

    context, requirements = _multi_context(
        [result],
        {"parameter": "диаметр выпуска"},
    )

    assert requirements[0]["clause"] == "18.34"
    assert requirements[0]["operator"] == ">="
    assert requirements[0]["normative_value"] is None
    assert "оператор >=" in context
    assert "числовое нормативное значение не задано" in context
    assert "нормативное значение — м" not in context
