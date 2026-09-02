"""Convert retrieved SP text into explicit, auditable requirements."""
from __future__ import annotations

import re
from typing import Any

_CLAUSE_PATTERNS = (
    re.compile(r"(?:пункт|п\.)\s*([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)([0-9]+(?:\.[0-9]+){2,})(?:\s|$)"),
)

_NUMBER_PATTERNS = (
    # A number is normative only when tied to an explicit requirement operator.
    re.compile(
        r"(?:не\s+менее|не\s+ниже|не\s+более|не\s+выше|равен|равна|равно|>=|<=)\s*"
        r"([0-9]+(?:[.,][0-9]+)?)",
        re.IGNORECASE,
    ),
    # Or when immediately followed by a recognized engineering unit.
    re.compile(
        r"([0-9]+(?:[.,][0-9]+)?)\s*(мм|м\b|л\s*/\s*с|м\s*[³3]\s*/\s*(?:ч|сут)|кпа\b|м/с)",
        re.IGNORECASE,
    ),
)

_UNIT_PATTERNS = (
    (r"л\s*/\s*с", "л/с"),
    (r"м\s*[³3]\s*/\s*ч", "м³/ч"),
    (r"м\s*[³3]\s*/\s*сут", "м³/сут"),
    (r"мм", "мм"),
    (r"м\b", "м"),
    (r"кпа\b", "кПа"),
    (r"м/с", "м/с"),
)


def _clause(text: str) -> str:
    for pattern in _CLAUSE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ""


def _number(text: str) -> float | None:
    """Extract only an engineering value, never a bare clause number."""
    for pattern in _NUMBER_PATTERNS:
        match = pattern.search(text.lower())
        if not match:
            continue
        # The unit pattern has the number in group 1; operator pattern also does.
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            continue
    return None


def _operator(text: str) -> str:
    lower = text.lower()
    if any(x in lower for x in ("не менее", "не ниже", ">=")):
        return ">="
    if any(x in lower for x in ("не более", "не выше", "<=")):
        return "<="
    # '=' is accepted only as a standalone mathematical equality; a clause such
    # as 8.3.2 must never become a normative equality.
    if "равен" in lower or "равна" in lower or "равно" in lower or re.search(r"(?<![0-9])=(?!=)", lower):
        return "="
    return ""


def extract_requirement(result: dict[str, Any], parameter: str = "") -> dict[str, Any]:
    content = result.get("content", {})
    text = str(content.get("text", "") if isinstance(content, dict) else content).strip()
    requirement = {
        "norm": str(result.get("norm_number") or ""),
        "version": str(result.get("version") or ""),
        "clause": _clause(text),
        "requirement": text,
        "parameter": parameter,
        "operator": _operator(text),
        "normative_value": _number(text),
        "normative_unit": "",
        "page": result.get("page"),
        "source": result,
    }
    for pattern, unit in _UNIT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            requirement["normative_unit"] = unit
            break
    return requirement


def select_normative_requirements(
    results: list[dict[str, Any]], parameter: str = "", limit: int = 4
) -> list[dict[str, Any]]:
    selected = []
    parameter_words = {
        x.lower() for x in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", parameter)
    }
    for result in results:
        item = extract_requirement(result, parameter)
        text = item["requirement"].lower()
        overlap = sum(word in text for word in parameter_words)
        explicit = bool(
            item["clause"]
            or item["operator"]
            or item["normative_value"] is not None
        )
        item["requirement_relevance"] = overlap * 0.1 + (0.25 if explicit else 0.0)
        selected.append(item)
    selected.sort(key=lambda x: x["requirement_relevance"], reverse=True)
    return selected[:limit]
