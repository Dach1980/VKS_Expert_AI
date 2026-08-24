"""
Source document loading helpers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(
    source_path: Path,
) -> Dict[str, Any]:
    with source_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_pages(
    source: Dict[str, Any],
) -> List[Dict[str, Any]]:
    pages = source.get("pages")

    if isinstance(pages, list):
        return pages

    data = source.get("data")

    if isinstance(data, dict):
        pages = data.get("pages")

        if isinstance(pages, list):
            return pages

    return []


def save_json(
    data: Dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        