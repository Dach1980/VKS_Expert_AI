"""Result contract for Normative JSON 2.0 validation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationError:
    """A machine-readable validation error."""

    code: str
    path: str
    message: str
    validator: str


@dataclass(frozen=True)
class ValidationWarning:
    """A non-blocking validation diagnostic."""

    code: str
    path: str
    message: str
    validator: str


@dataclass
class ValidationResult:
    """Aggregated result returned by NormativeJSONValidator."""

    valid: bool
    schema_valid: bool
    integrity_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)
