"""Metadata extraction for normative PDF versions.

Canonical version metadata is derived from the universal filename parser.
PDF/parsed JSON may enrich document number/title, but cannot override the
explicit amendment/date encoded in the filename.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.knowledge.filename_parser import FilenameParseError, parse_normative_filename


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _extract_from_json(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    result: dict[str, str] = {}
    number_keys = {"document_number", "norm_number", "normative_number", "standard_number", "number", "code"}
    title_keys = {"document_title", "norm_title", "title", "name", "document_name"}
    for key, value in _walk_strings(data):
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        normalized_key = key.lower().strip()
        if normalized_key in number_keys:
            result.setdefault("number", text)
        elif normalized_key in title_keys and len(text) > 8 and not text.lower().endswith((".pdf", ".json")):
            result.setdefault("title", text)
    return result


def _discover_sibling_json(parsed_path: Path | None) -> list[Path]:
    if not parsed_path or not parsed_path.parent.exists():
        return []
    return sorted(parsed_path.parent.glob("*.json"))


def extract_version_metadata(
    pdf_path: Path | str,
    parsed_path: Path | str | None = None,
) -> dict[str, Any]:
    """Extract canonical document/version metadata.

    The filename is authoritative for edition date and amendment number.
    Parsed JSON is used only for document number/title enrichment.
    """
    pdf_path = Path(pdf_path)
    parsed = Path(parsed_path) if parsed_path else None

    try:
        filename = parse_normative_filename(pdf_path.name)
    except FilenameParseError as error:
        raise ValueError(str(error)) from error

    parsed_meta = _extract_from_json(parsed)
    number = parsed_meta.get("number") or filename.document_number
    title = parsed_meta.get("title")

    edition: dict[str, Any] = {}
    if filename.effective_date:
        edition["date"] = filename.effective_date
    if filename.amendment_number is not None:
        edition["amendment"] = {"number": filename.amendment_number}
        if filename.effective_date:
            edition["amendment"]["effective_from"] = filename.effective_date

    page_count = 0
    if pdf_path.exists():
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as document:
                page_count = len(document)
        except Exception:
            try:
                from pypdf import PdfReader
                page_count = len(PdfReader(str(pdf_path)).pages)
            except Exception:
                pass

    source = {
        "file": str(pdf_path),
        "original_filename": filename.original_filename,
    }

    result: dict[str, Any] = {
        "number": number,
        "edition": edition,
        "source": source,
        "pages_count": page_count,
        "version_id": filename.version_id,
    }
    if title:
        result["title"] = title
    return result
