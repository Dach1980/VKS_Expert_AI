"""Validation codes for Normative JSON 2.0."""


class ValidationCode:
    """Stable machine-readable validation codes."""

    # Schema validation
    SCHEMA_INVALID = "SCHEMA_INVALID"

    # Identifier integrity
    DUPLICATE_REQUIREMENT_ID = "DUPLICATE_REQUIREMENT_ID"
    DUPLICATE_TABLE_ID = "DUPLICATE_TABLE_ID"
    DUPLICATE_REFERENCE_ID = "DUPLICATE_REFERENCE_ID"

    # Internal references
    REQ_CLAUSE_NOT_FOUND = "REQ_CLAUSE_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    REFERENCE_NOT_FOUND = "REFERENCE_NOT_FOUND"

    # Provenance / structure
    PAGE_OUT_OF_RANGE = "PAGE_OUT_OF_RANGE"
    INVALID_PAGE_RANGE = "INVALID_PAGE_RANGE"
    BBOX_OUT_OF_PAGE = "BBOX_OUT_OF_PAGE"
