"""JSON Schema validation for Normative JSON 2.0.

This layer validates structure only. It does not perform semantic
applicability or project-vs-norm comparisons.
"""

from pathlib import Path
import json

from .validation_codes import ValidationCode
from .validation_result import ValidationError


class SchemaValidator:
    """Validate a document against normative_document.schema.json."""

    def __init__(self, schema_path: str | Path):
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))

    def validate(self, document: dict) -> list[ValidationError]:
        try:
            import jsonschema
        except ImportError as exc:  # pragma: no cover - environment error
            raise RuntimeError("jsonschema package is required for schema validation") from exc

        validator = jsonschema.Draft202012Validator(self.schema)
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
        return [
            ValidationError(
                code=ValidationCode.SCHEMA_INVALID,
                path=self._path(error),
                message=error.message,
                validator="schema",
            )
            for error in errors
        ]

    @staticmethod
    def _path(error) -> str:
        path = "$"
        for part in error.absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        return path
