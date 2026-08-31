"""Metadata extraction for normative PDF versions."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any


def _normalize_number(value: str) -> str:
    value = str(value or '').replace('\u00a0', ' ')
    value = re.sub(r'(?i)\b(СП|ГОСТ\s*Р?|СНиП|ТР|ФЗ)\s*[-_ ]*', lambda m: re.sub(r'\s+', ' ', m.group(1)).strip() + ' ', value)
    value = re.sub(r'\s*([._])\s*', r'\1', value)
    return re.sub(r'\s+', ' ', value).strip()


def _extract_number(text: str) -> str | None:
    match = re.search(r'(?i)\b(СП|ГОСТ\s*Р?|СНиП|ТР|ФЗ)\s*[-_ ]*([0-9]{1,5}(?:\s*[._]\s*[0-9]{1,6}){1,5})', text or '')
    return _normalize_number(f'{match.group(1)} {match.group(2)}') if match else None


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _extract_from_text(text: str) -> dict[str, str]:
    text = re.sub(r'\s+', ' ', text or '').strip()
    result: dict[str, str] = {}
    number = _extract_number(text)
    if number:
        result['number'] = number
    title = re.search(r'(ВНУТРЕННИЙ\s+ВОДОПРОВОД\s+И\s+КАНАЛИЗАЦИЯ\s+ЗДАНИЙ)', text, re.IGNORECASE)
    if title:
        result['title'] = 'Внутренний водопровод и канализация зданий'
    change = re.search(r'Изменени(?:е|я)\s*(?:№|N|No\.?)?\s*(\d+)', text, re.IGNORECASE)
    if change:
        result['change_number'] = change.group(1)
    change_date = re.search(r'(?:Изменени(?:е|я)|введено|действует).*?(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if change_date:
        result['change_date'] = change_date.group(1)
    return result


def _extract_from_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8-sig') as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    result: dict[str, str] = {}
    strings: list[str] = []
    preferred = {
        'document_number': 'number', 'norm_number': 'number', 'normative_number': 'number',
        'standard_number': 'number', 'number': 'number', 'code': 'number',
        'document_title': 'title', 'norm_title': 'title', 'title': 'title', 'name': 'title',
        'change_number': 'change_number', 'amendment_number': 'change_number', 'revision_number': 'change_number',
        'change_date': 'change_date', 'amendment_date': 'change_date', 'revision_date': 'change_date'
    }
    for key, value in _walk_strings(data):
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        strings.append(value)
        target = preferred.get(key.lower().strip())
        if target == 'number':
            number = _extract_number(value)
            if number:
                result.setdefault('number', number)
        elif target == 'title' and len(value) > 8:
            result.setdefault('title', value)
        elif target == 'change_number':
            match = re.search(r'\d+', value)
            if match:
                result.setdefault('change_number', match.group(0))
        elif target == 'change_date':
            match = re.search(r'\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}', value)
            if match:
                result.setdefault('change_date', match.group(0))
    for key, value in _extract_from_text(' '.join(strings)).items():
        result.setdefault(key, value)
    return result


def _extract_from_filename(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    stem = path.stem.replace('_', ' ').replace('-', ' ')
    result: dict[str, str] = {}
    number = _extract_number(stem)
    if number:
        result['number'] = number
    # Filename is authoritative for explicitly named base/amendment files.
    base = re.search(r'(?i)\bбазов(?:ая|ая версия|ую)\b|\bбез\s+изменений\b', stem)
    if base:
        result['version_type'] = 'base'
        result['change_number'] = ''
    amendment = re.search(r'(?i)\b(?:изм(?:енение|енения)?|изменени[ея]|amendment)\s*№?\s*(\d+)\b', stem)
    if amendment:
        result['version_type'] = 'amendment'
        result['change_number'] = amendment.group(1)
    return result


def _discover_sibling_json(parsed_path: Path | None) -> list[Path]:
    if not parsed_path or not parsed_path.parent.exists():
        return []
    stem_text = parsed_path.stem.replace('_', ' ')
    m = re.search(r'(?:СП|ГОСТ|СНиП|ТР|ФЗ)\s*[0-9]+(?:[._][0-9]+)+', stem_text, re.I)
    if not m:
        return []
    compact = re.sub(r'[^0-9.]', '', m.group(0))
    return sorted(parsed_path.parent.glob(f'*{compact}*.json'))


def extract_version_metadata(pdf_path: Path | str, parsed_path: Path | str | None = None) -> dict[str, Any]:
    pdf_path = Path(pdf_path)
    parsed_path = Path(parsed_path) if parsed_path else None
    filename_meta = _extract_from_filename(pdf_path)
    result = _extract_from_json(parsed_path) if parsed_path else {}

    if not result.get('number'):
        for candidate in _discover_sibling_json(parsed_path):
            candidate_meta = _extract_from_json(candidate)
            if candidate_meta.get('number'):
                result.update(candidate_meta)
                break
            candidate_name_meta = _extract_from_filename(candidate)
            if candidate_name_meta.get('number'):
                result.setdefault('number', candidate_name_meta['number'])
                break

    if not result.get('number'):
        result.update({k: v for k, v in filename_meta.items() if k not in result})

    page_count = 0
    if pdf_path.exists():
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as document:
                page_count = len(document)
                sample_text = '\n'.join(document[index].get_text('text') for index in range(min(len(document), 8)))
            for key, value in _extract_from_text(sample_text).items():
                result.setdefault(key, value)
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                page_count = len(reader.pages)
                sample_text = '\n'.join((reader.pages[index].extract_text() or '') for index in range(min(len(reader.pages), 8)))
                for key, value in _extract_from_text(sample_text).items():
                    result.setdefault(key, value)
            except Exception:
                pass

    # Explicit filename semantics override text: a file named "базовая_версия"
    # is the base edition even if its source PDF contains references to later changes.
    if filename_meta.get('version_type'):
        result['version_type'] = filename_meta['version_type']
        result['change_number'] = filename_meta.get('change_number', '')
    result['pages_count'] = page_count
    return result