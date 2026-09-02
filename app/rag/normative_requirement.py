"""Convert retrieved SP text into explicit, auditable requirements."""
from __future__ import annotations

import re
from typing import Any

_CLAUSE_PATTERNS = (
    re.compile(r"(?:пункт|п\.|параграф|раздел)\s*([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)([0-9]+(?:\.[0-9]+){2,})(?:\s|$)"),
)

_NUMBER_PATTERNS = (
    re.compile(
        r"(?:не\s+менее|не\s+ниже|не\s+более|не\s+выше|равен|равна|равно|>=|<=)\s*"
        r"([0-9]+(?:[.,][0-9]+)?)",
        re.IGNORECASE,
    ),
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


def _metadata_text(result: dict[str, Any]) -> str:
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    parts: list[str] = []
    for key in ("clause", "section", "paragraph", "point", "number", "heading", "title"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts)


def _clause(text: str, result: dict[str, Any] | None = None) -> str:
    if result:
        metadata = result.get("metadata")
        if isinstance(metadata, dict):
            for key in ("clause", "paragraph", "point", "section"):
                value = str(metadata.get(key) or "").strip()
                match = re.search(r"\d+(?:\.\d+)+", value)
                if match:
                    return match.group(0)
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
    if "равен" in lower or "равна" in lower or "равно" in lower or re.search(r"(?<![0-9])=(?!=)", lower):
        return "="
    return ""


def extract_requirement(result: dict[str, Any], parameter: str = "") -> dict[str, Any]:
    content = result.get("content", {})
    text = str(content.get("text", "") if isinstance(content, dict) else content).strip()
    metadata_text = _metadata_text(result)
    clause = _clause(text, result)
    requirement = {
        "norm": str(result.get("norm_number") or ""),
        "version": str(result.get("version") or ""),
        "clause": clause,
        "requirement": text,
        "parameter": parameter,
        "operator": _operator(text),
        "normative_value": _number(text),
        "normative_unit": "",
        "page": result.get("page"),
        "source": result,
        "metadata": result.get("metadata") if isinstance(result.get("metadata"), dict) else {},
    }
    for pattern, unit in _UNIT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            requirement["normative_unit"] = unit
            break
    if metadata_text:
        requirement["metadata_text"] = metadata_text
    return requirement


def select_normative_requirements(
    results: list[dict[str, Any]], parameter: str = "", limit: int = 4
) -> list[dict[str, Any]]:
    """Rank concrete, clause-bearing requirements ahead of generic chunks.

    The audit pipeline must not silently lose a visual candidate merely because
    the best semantic hit was a heading/table fragment without an explicit clause.
    Clause-bearing requirements therefore receive a strong priority, followed by
    parameter overlap and explicit numeric operators/values.
    """
    selected = []
    parameter_words = {
        x.lower() for x in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", parameter)
    }
    for result in results:
        item = extract_requirement(result, parameter)
        text = item["requirement"].lower()
        metadata_text = str(item.get("metadata_text") or "").lower()
        overlap = sum(word in f"{text} {metadata_text}" for word in parameter_words)
        has_clause = bool(item["clause"])
        has_requirement_text = bool(item["requirement"].strip())
        has_numeric_rule = item["operator"] in {">=", "<=", "="} or item["normative_value"] is not None
        explicit = has_clause or has_numeric_rule
        item["requirement_relevance"] = (
            (2.0 if has_clause else 0.0)
            + (0.5 if has_numeric_rule else 0.0)
            + (overlap * 0.1)
            + (0.1 if has_requirement_text else 0.0)
        )
        item["has_concrete_clause"] = has_clause
        item["has_numeric_rule"] = has_numeric_rule
        selected.append(item)
    selected.sort(key=lambda x: x["requirement_relevance"], reverse=True)
    return selected[:limit]
