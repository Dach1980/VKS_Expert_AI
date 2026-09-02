"""Convert retrieved SP text into explicit, auditable requirements."""
from __future__ import annotations

import re
from typing import Any


_CLAUSE_PATTERNS = (
    re.compile(r"(?:пункт|п\.)\s*([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)([0-9]+(?:\.[0-9]+){2,})(?:\s|$)"),
)


def _clause(text: str) -> str:
    for pattern in _CLAUSE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ""


def _number(text: str) -> float | None:
    match = re.search(r"(?<![A-Za-zА-Яа-я])(?:не менее|не более|равен|равна|=)?\s*([0-9]+(?:[.,][0-9]+)?)", text.lower())
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _operator(text: str) -> str:
    lower = text.lower()
    if "не менее" in lower or "не ниже" in lower or "не менее чем" in lower or ">=" in lower:
        return ">="
    if "не более" in lower or "не выше" in lower or "<=" in lower:
        return "<="
    if "равен" in lower or "равна" in lower or "=" in lower:
        return "="
    return ""


def extract_requirement(result: dict[str, Any], parameter: str = "") -> dict[str, Any]:
    """Extract only explicit requirement signals; never invent missing values."""
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
    unit_patterns = (
        (r"л\s*/\s*с", "л/с"), (r"м\s*[³3]\s*/\s*ч", "м³/ч"),
        (r"м\s*[³3]\s*/\s*сут", "м³/сут"), (r"мм", "мм"),
        (r"м\b", "м"), (r"кпа\b", "кПа"), (r"м/с", "м/с"),
    )
    for pattern, unit in unit_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            requirement["normative_unit"] = unit
            break
    return requirement


def select_normative_requirements(results: list[dict[str, Any]], parameter: str = "", limit: int = 4) -> list[dict[str, Any]]:
    """Keep explicit, parameter-relevant requirements ahead of generic chunks."""
    selected = []
    parameter_words = {x.lower() for x in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", parameter)}
    for result in results:
        item = extract_requirement(result, parameter)
        text = item["requirement"].lower()
        overlap = sum(word in text for word in parameter_words)
        explicit = bool(item["clause"] or item["operator"] or item["normative_value"] is not None)
        item["requirement_relevance"] = overlap * 0.1 + (0.25 if explicit else 0.0)
        selected.append(item)
    selected.sort(key=lambda x: x["requirement_relevance"], reverse=True)
    return selected[:limit]
