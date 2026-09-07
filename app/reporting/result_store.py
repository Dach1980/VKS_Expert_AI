"""Persistent result artifacts for completed Project Expert AI checks."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_RESULT_RE = re.compile(r"^result_(\d{8}_\d{6})\.json$")


def results_dir(document_root: Path) -> Path:
    path = document_root / "checking" / "first_pass"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp(value: str | None = None) -> str:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_result(document_root: Path, result: dict[str, Any]) -> Path:
    """Write an immutable timestamped result artifact and return its path."""
    directory = results_dir(document_root)
    stamp = _timestamp(str(result.get("checked_at") or ""))
    path = directory / f"result_{stamp}.json"
    # A second run in the same second must never overwrite the first result.
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = directory / f"result_{stamp}.json"
    payload = dict(result)
    payload["result_file"] = path.name
    payload["result_id"] = path.stem
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def load_results(document_root: Path) -> list[dict[str, Any]]:
    directory = document_root / "checking" / "first_pass"
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in directory.glob("result_*.json"):
        if not _RESULT_RE.match(path.name) and not re.match(r"^result_\d{8}_\d{6}_\d+\.json$", path.name):
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            value.setdefault("result_file", path.name)
            value.setdefault("result_id", path.stem)
            items.append(value)
    items.sort(key=lambda x: str(x.get("checked_at") or x.get("result_file") or ""), reverse=True)
    return items
