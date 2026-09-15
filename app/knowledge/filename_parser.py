"""Universal parser for normative-document filenames.

Canonical human-readable form::

    СП_30.13330.2020 Изм.5 01.03.2025.pdf

The amendment marker is optional. The date is an independent attribute and
may be the only version marker for laws, government resolutions, etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class FilenameParseError(ValueError):
    """Имя нормативного файла не соответствует принятой модели."""


@dataclass(frozen=True)
class ParsedFilename:
    document_number: str
    amendment_number: str | None
    effective_date: str | None
    original_filename: str

    @property
    def version_id(self) -> str:
        """Стабильный технический ID версии, производный от имени версии."""
        number = re.sub(r"[^A-Za-z0-9А-Яа-я]+", "_", self.document_number).strip("_")
        date_part = self.effective_date.replace("-", "") if self.effective_date else "undated"
        amendment_part = f"_amendment_{self.amendment_number}" if self.amendment_number else ""
        return f"{number}_{date_part}{amendment_part}"


_DATE_RE = re.compile(r"(?<!\d)(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})(?!\d)")
_AMENDMENT_RE = re.compile(
    r"(?i)(?:^|\s)(?:изм(?:енение|енения)?|изменени[ея]|amendment)\.?\s*№?\s*(\d+)(?=\s|$)"
)


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("–", "-").strip())


def _parse_date(value: str) -> str:
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        day, month, year = value.split(".")
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError as exc:
            raise FilenameParseError(f"Некорректная дата в имени файла: {value}") from exc
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise FilenameParseError(f"Некорректная дата в имени файла: {value}") from exc


def parse_normative_filename(filename: str | Path) -> ParsedFilename:
    """Разбирает универсальное имя нормативного PDF."""
    original = Path(filename).name
    if Path(original).suffix.lower() != ".pdf":
        raise FilenameParseError(f"Ожидался PDF-файл: {original}")

    normalized = _normalize_spaces(Path(original).stem)
    date_match = _DATE_RE.search(normalized)
    effective_date = _parse_date(date_match.group(1)) if date_match else None
    without_date = normalized[: date_match.start()].rstrip() if date_match else normalized

    amendment_match = _AMENDMENT_RE.search(without_date)
    amendment_number = amendment_match.group(1) if amendment_match else None
    document_part = without_date[: amendment_match.start()].rstrip() if amendment_match else without_date

    if not document_part:
        raise FilenameParseError(f"Не удалось определить номер документа: {original}")

    return ParsedFilename(
        document_number=_normalize_spaces(document_part),
        amendment_number=amendment_number,
        effective_date=effective_date,
        original_filename=original,
    )
