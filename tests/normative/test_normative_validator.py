import copy
import json
from pathlib import Path

import pytest

from app.knowledge.normative import NormativeJSONValidator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "training/schemas/normative_document.schema.json"
FIXTURE = ROOT / "training/fixtures/normative_document_2_0_minimal.json"


@pytest.fixture
def document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def validator():
    return NormativeJSONValidator(SCHEMA)


def assert_error(result, code):
    assert not result.valid
    assert any(error.code == code for error in result.errors)


def test_valid_minimal_fixture_passes(validator, document):
    result = validator.validate(document)
    assert result.valid
    assert result.schema_valid
    assert result.integrity_valid
    assert result.errors == []


def test_missing_requirement_id_is_schema_error(validator, document):
    del document["requirements"][0]["requirement_id"]
    result = validator.validate(document)
    assert not result.schema_valid
    assert_error(result, "SCHEMA_INVALID")


def test_invalid_bbox_is_schema_error(validator, document):
    document["requirements"][0]["source"]["blocks"][0]["bbox"] = [10, 20, 30]
    result = validator.validate(document)
    assert not result.schema_valid
    assert_error(result, "SCHEMA_INVALID")


def test_unknown_requirement_type_is_schema_error(validator, document):
    document["requirements"][0]["type"] = "unknown"
    result = validator.validate(document)
    assert not result.schema_valid
    assert_error(result, "SCHEMA_INVALID")


def test_applicable_field_is_schema_error(validator, document):
    document["requirements"][0]["applicable"] = True
    result = validator.validate(document)
    assert not result.schema_valid
    assert_error(result, "SCHEMA_INVALID")


def test_invalid_values_structure_is_schema_error(validator, document):
    document["requirements"][0]["values"] = [100]
    result = validator.validate(document)
    assert not result.schema_valid
    assert_error(result, "SCHEMA_INVALID")


def test_nonexistent_clause_id_is_integrity_error(validator, document):
    document["requirements"][0]["clause_id"] = "18.999"
    result = validator.validate(document)
    assert result.schema_valid
    assert not result.integrity_valid
    assert_error(result, "REQ_CLAUSE_NOT_FOUND")


def test_duplicate_requirement_id_is_integrity_error(validator, document):
    duplicate = copy.deepcopy(document["requirements"][0])
    document["requirements"].append(duplicate)
    result = validator.validate(document)
    assert result.schema_valid
    assert not result.integrity_valid
    assert_error(result, "DUPLICATE_REQUIREMENT_ID")


def test_nonexistent_table_ref_is_integrity_error(validator, document):
    document["requirements"][0]["table_refs"] = ["TABLE-404"]
    result = validator.validate(document)
    assert result.schema_valid
    assert not result.integrity_valid
    assert_error(result, "TABLE_NOT_FOUND")


def test_out_of_range_provenance_page_is_integrity_error(validator, document):
    document["requirements"][0]["source"]["blocks"][0]["page"] = 2
    result = validator.validate(document)
    assert result.schema_valid
    assert not result.integrity_valid
    assert_error(result, "PAGE_OUT_OF_RANGE")
