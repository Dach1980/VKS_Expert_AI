from app.knowledge.filename_parser import parse_normative_filename


def test_sp_amendment_and_effective_date():
    parsed = parse_normative_filename("СП_30.13330.2020 Изм.5 01.03.2025.pdf")
    assert parsed.document_number == "СП 30.13330.2020"
    assert parsed.amendment_number == "5"
    assert parsed.effective_date == "2025-03-01"
    assert parsed.version_id == "СП_30_13330_2020_20250301_amendment_5"


def test_date_only_federal_law():
    parsed = parse_normative_filename("ФЗ_123 01.01.2026.pdf")
    assert parsed.document_number == "ФЗ 123"
    assert parsed.amendment_number is None
    assert parsed.effective_date == "2026-01-01"
    assert parsed.version_id == "ФЗ_123_20260101"


def test_date_only_government_resolution():
    parsed = parse_normative_filename("Постановление_Правительства_123 01.01.2026.pdf")
    assert parsed.document_number == "Постановление Правительства 123"
    assert parsed.amendment_number is None
    assert parsed.effective_date == "2026-01-01"


def test_sp_without_amendment():
    parsed = parse_normative_filename("СП_30.13330.2020 01.03.2025.pdf")
    assert parsed.document_number == "СП 30.13330.2020"
    assert parsed.amendment_number is None
    assert parsed.effective_date == "2025-03-01"


def test_iso_date_is_supported():
    parsed = parse_normative_filename("ГОСТ_Р_123.4 2026-01-01.pdf")
    assert parsed.document_number == "ГОСТ Р 123.4"
    assert parsed.effective_date == "2026-01-01"
