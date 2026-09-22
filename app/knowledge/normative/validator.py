"""Public Validator API for Normative JSON 2.0."""

from pathlib import Path

from .integrity_validator import IntegrityValidator
from .schema_validator import SchemaValidator
from .validation_result import ValidationResult


class NormativeJSONValidator:
    """Run schema validation first, then semantic integrity validation."""

    def __init__(self, schema_path: str | Path):
        self.schema_validator = SchemaValidator(schema_path)
        self.integrity_validator = IntegrityValidator()

    def validate(self, document: dict) -> ValidationResult:
        schema_errors = self.schema_validator.validate(document)
        if schema_errors:
            return ValidationResult(
                valid=False,
                schema_valid=False,
                integrity_valid=False,
                errors=schema_errors,
            )

        integrity_errors = self.integrity_validator.validate(document)
        return ValidationResult(
            valid=not integrity_errors,
            schema_valid=True,
            integrity_valid=not integrity_errors,
            errors=integrity_errors,
        )
