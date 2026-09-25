"""Convert retrieved SP text into explicit, auditable requirements."""
from __future__ import annotations

import re
from typing import Any

_CLAUSE_PATTERNS = (
    re.compile(r"(?:пункт|п\.|параграф|раздел)\s*([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
    # A Russian normative clause such as 18.34 has one or more dot-separated
    # components after the first number. The previous {2,} required at least
    # three components and therefore missed ordinary clauses like 18.34.
    re.compile(r"(?:^|\s)([0-9]+(?:\.[0-9]+)+)(?:\s|$|[,:;])"),
)

_NUMBER_PATTERNS = (
    re.compile(
        r"(?:не\s+менее|не\s+меньше|не\s+ниже|не\s+более|не\s+выше|равен|равна|равно|>=|<=)\s*"
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
    normative_json = metadata.get("normative_json")
    if isinstance(normative_json, dict):
        for key in ("clause_ids", "requirement_ids", "reference_ids"):
            values = normative_json.get(key)
            if isinstance(values, list):
                parts.extend(str(value) for value in values if value not in (None, ""))
    return " ".join(parts)


def _clause_candidates(text: str) -> list[tuple[str, str]]:
    """Return clause headings together with the text belonging to each clause.

    Page-level Normative JSON metadata may contain several clauses because one
    PDF page can span multiple structural clauses. It is therefore a page
    scope, not the exact clause of an individual text chunk.
    """
    matches = list(
        re.finditer(
            r"(?<![A-Za-zА-Яа-яЁё0-9№])(\d+(?:\.\d+)+)(?=\s+)",
            str(text or ""),
        )
    )
    candidates: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[start:end].strip()
        if segment:
            candidates.append((match.group(1), segment))
    return candidates


def _clause(text: str, result: dict[str, Any] | None = None, parameter: str = "") -> str:
    candidates = _clause_candidates(text)
    if candidates:
        parameter_words = {
            word.lower()
            for word in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", parameter)
        }
        if parameter_words:
            scored = []
            for clause, segment in candidates:
                lower = segment.lower()
                overlap = sum(word in lower for word in parameter_words)
                scored.append((overlap, clause))
            best_overlap = max(score for score, _ in scored)
            if best_overlap > 0:
                return next(clause for score, clause in scored if score == best_overlap)
        return candidates[0][0]

    if result:
        metadata = result.get("metadata")
        if isinstance(metadata, dict):
            for key in ("clause", "paragraph", "point", "section"):
                value = str(metadata.get(key) or "").strip()
                match = re.search(r"\d+(?:\.\d+)+", value)
                if match:
                    return match.group(0)

            normative_json = metadata.get("normative_json")
            if isinstance(normative_json, dict):
                clause_ids = normative_json.get("clause_ids")
                if isinstance(clause_ids, list):
                    for value in clause_ids:
                        match = re.search(r"\d+(?:\.\d+)+", str(value or ""))
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
    if any(x in lower for x in ("не менее", "не меньше", "не ниже", ">=")):
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
    clause = _clause(text, result, parameter)
    requirement_text = text
    candidates = _clause_candidates(text)
    if candidates and clause:
        for candidate_clause, segment in candidates:
            if candidate_clause == clause:
                requirement_text = segment
                break

    requirement = {
        "norm": str(result.get("norm_number") or ""),
        "version": str(result.get("version") or ""),
        "clause": clause,
        "requirement": requirement_text,
        "parameter": parameter,
        "operator": _operator(requirement_text),
        "normative_value": _number(requirement_text),
        "normative_unit": "",
        "page": result.get("page"),
        "source": result,
        "metadata": result.get("metadata") if isinstance(result.get("metadata"), dict) else {},
    }
    for pattern, unit in _UNIT_PATTERNS:
        if re.search(pattern, requirement_text, re.IGNORECASE):
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
