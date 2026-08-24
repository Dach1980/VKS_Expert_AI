"""
VKS Expert AI — source document helpers.
"""

from __future__ import annotations

from typing import Any, Dict, List


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
