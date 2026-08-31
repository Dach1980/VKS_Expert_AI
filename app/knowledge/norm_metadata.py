"""Metadata extraction for normative PDF versions."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _extract_from_text(text: str) -> dict[str, str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    result: dict[str, str] = {}

    number = re.search(
        r"\b((?:СП|ГОСТ\s*Р?|СНиП|ТР|ФЗ)\s*\d+(?:\.\d+)+)\b",
        text,
        re.IGNORECASE,
    )
    if number:
        result["number"] = re.sub(r"\s+", " ", number.group(1)).strip()

    title = re.search(
        r"(ВНУТРЕННИЙ\s+ВОДОПРОВОД\s+И\s+КАНАЛИЗАЦИЯ\s+ЗДАНИЙ)",
        text,
        re.IGNORECASE,
    )
    if title:
        result["title"] = title.group(1).title()

    change = re.search(
        r"Изменени(?:е|я)\s*(?:№|N|No\.?)?\s*(\d+)",
        text,
        re.IGNORECASE,
    )
    if change:
        result["change_number"] = change.group(1)

    change_date = re.search(
        r"(?:Изменени(?:е|я)|введено|действует).*?"
        r"(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )
    if change_date:
        result["change_date"] = change_date.group(1)

    return result


def _extract_from_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    result: dict[str, str] = {}
    strings: list[str] = []
    preferred = {
        "document_number": "number",
        "norm_number": "number",
        "normative_number": "number",
        "standard_number": "number",
        "document_title": "title",
        "norm_title": "title",
        "change_number": "change_number",
        "amendment_number": "change_number",
        "revision_number": "change_number",
        "change_date": "change_date",
        "amendment_date": "change_date",
        "revision_date": "change_date",
    }
    for key, value in _walk_strings(data):
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        strings.append(value)
        target = preferred.get(key.lower().strip())
        if target == "number" and re.search(r"(?:СП|ГОСТ|СНиП|ТР|ФЗ)\s*\d+(?:\.\d+)+", value, re.IGNORECASE):
            result.setdefault("number", re.sub(r"\s+", " ", value))
        elif target == "title" and len(value) > 8:
            result.setdefault("title", value)
        elif target == "change_number":
            match = re.search(r"\d+", value)
            if match:
                result.setdefault("change_number", match.group(0))
        elif target == "change_date":
            match = re.search(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}", value)
            if match:
                result.setdefault("change_date", match.group(0))

    text_result = _extract_from_text(" ".join(strings))
    for key, value in text_result.items():
        result.setdefault(key, value)
    return result


def extract_version_metadata(pdf_path: Path | str, parsed_path: Path | str | None = None) -> dict[str, Any]:
    """Read metadata from parsed JSON and, importantly, from the PDF itself."""
    pdf_path = Path(pdf_path)
    parsed_path = Path(parsed_path) if parsed_path else None
    result = _extract_from_json(parsed_path) if parsed_path else {}
    page_count = 0

    if pdf_path.exists():
        try:
            import pymupdf

            with pymupdf.open(pdf_path) as document:
                page_count = len(document)
                sample_text = "\n".join(
                    document[index].get_text("text")
                    for index in range(min(len(document), 5))
                )
            pdf_result = _extract_from_text(sample_text)
            for key, value in pdf_result.items():
                # PDF is the fallback when parsed JSON is absent, and fixes
                # incomplete legacy Registry metadata.
                result.setdefault(key, value)
        except Exception:
            pass

    result["pages_count"] = page_count
    return result
