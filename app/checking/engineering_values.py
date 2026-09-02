"""Normalization of engineering values without losing source representation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class NormalizedEngineeringValue:
    raw: str
    value: float | None
    unit: str
    kind: str
    operator: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_UNIT_ALIASES = {
    "мм": "мм", "mm": "мм",
    "м": "м", "m": "м",
    "л/с": "л/с", "лс": "л/с", "l/s": "л/с",
    "м3/ч": "м³/ч", "м³/ч": "м³/ч", "м3/час": "м³/ч", "м³/час": "м³/ч",
    "м3/сут": "м³/сут", "м³/сут": "м³/сут",
    "кпа": "кПа", "мпа": "МПа", "бар": "бар",
    "%": "%", "град": "°", "°": "°",
}


def _number(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:[\s\u00a0]\d{3})*(?:[,.]\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0).replace(" ", "").replace("\u00a0", "").replace(",", "."))
    except ValueError:
        return None


def _unit(value: str, parameter: str) -> str:
    low = value.lower().replace("³", "3").replace("²", "2")
    for alias, normalized in _UNIT_ALIASES.items():
        if re.search(rf"(?<!\w){re.escape(alias.replace('³', '3').replace('²', '2'))}(?!\w)", low):
            return normalized
    p = parameter.lower()
    if "диаметр" in p or "dn" in low or "ø" in low or "⌀" in low:
        return "мм"
    if "уклон" in p or re.search(r"\bi\s*=", low):
        return ""
    return ""


def normalize_engineering_value(raw: Any, parameter: str = "", source: str = "") -> NormalizedEngineeringValue:
    """Return machine-comparable value while keeping the exact raw project string."""
    text = str(raw or "").strip()
    low = text.lower().replace("⌀", "ø")
    unit = _unit(text, parameter)
    number = _number(text)
    kind = "text"
    if re.search(r"(?:^|\s)(?:ø|dn)\s*\d", low) or "диаметр" in parameter.lower():
        kind = "diameter"
    elif re.search(r"\bi\s*=", low) or "уклон" in parameter.lower():
        kind = "slope"
    elif unit in {"л/с", "м³/ч", "м³/сут"} or "расход" in parameter.lower():
        kind = "flow"
    elif unit in {"кПа", "МПа", "бар"} or "давлен" in parameter.lower():
        kind = "pressure"
    elif unit in {"мм", "м"} or "длина" in parameter.lower():
        kind = "length"
    elif number is not None and ("колич" in parameter.lower() or "число" in parameter.lower()):
        kind = "count"
    if number is not None and kind == "text":
        kind = "number"
    operator = ""
    op = re.match(r"\s*(>=|<=|>|<|=|≥|≤)", text)
    if op:
        operator = op.group(1)
    return NormalizedEngineeringValue(text, number, unit, kind, operator, source)


def extract_engineering_values(text: Any, parameter: str = "", source: str = "") -> list[NormalizedEngineeringValue]:
    """Extract only plausible engineering tokens; table/title-block noise is ignored where possible."""
    value = str(text or "").strip()
    if not value:
        return []
    patterns = [
        r"(?:ø|⌀|DN\s*)\s*\d+(?:[,.]\d+)?\s*(?:мм|mm)?",
        r"\b\d+(?:[,.]\d+)?\s*(?:л/с|м3/ч|м³/ч|м3/сут|м³/сут|кПа|МПа|бар|мм|м|%)\b",
        r"\bi\s*=\s*\d+(?:[,.]\d+)?",
    ]
    found: list[NormalizedEngineeringValue] = []
    seen: set[tuple[str, str]] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, value, flags=re.IGNORECASE):
            raw = match.group(0).strip()
            normalized = normalize_engineering_value(raw, parameter, source)
            key = (normalized.kind, normalized.raw.lower())
            if key not in seen:
                found.append(normalized)
                seen.add(key)
    if not found and re.fullmatch(r"\s*(?:\d+(?:[,.]\d+)?|да|нет|предусмотрен|не предусмотрен)\s*", value, re.IGNORECASE):
        found.append(normalize_engineering_value(value, parameter, source))
    return found
