"""Persistent result artifacts and provenance diagnostics for completed checks."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

_RESULT_RE = re.compile(r"^result_(\d{8}_\d{6})(?:_\d+)?\.json$")


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


def _scan_question_marks(value: Any, path: str = "$", samples: list[dict[str, str]] | None = None) -> tuple[int, list[dict[str, str]]]:
    """Count literal '?' and keep a small, path-aware sample for provenance."""
    samples = samples if samples is not None else []
    count = 0
    if isinstance(value, str):
        count = value.count("?")
        if count and len(samples) < 12:
            samples.append({"path": path, "text": value[:500]})
        return count, samples
    if isinstance(value, dict):
        for key, item in value.items():
            child_count, _ = _scan_question_marks(item, f"{path}.{key}", samples)
            count += child_count
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            child_count, _ = _scan_question_marks(item, f"{path}[{index}]", samples)
            count += child_count
    return count, samples


def build_question_mark_trace(document_root: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Build a stage-oriented '?' trace without changing the checking decision."""
    stages: dict[str, dict[str, Any]] = {}

    parsed_path = document_root / "parsed.json"
    if parsed_path.exists():
        try:
            parsed = json.loads(parsed_path.read_text(encoding="utf-8-sig"))
            count, samples = _scan_question_marks(parsed)
            stages["parser"] = {"count": count, "source": str(parsed_path), "samples": samples}
        except (OSError, json.JSONDecodeError) as error:
            stages["parser"] = {"count": None, "error": str(error)}
    else:
        stages["parser"] = {"count": None, "source": str(parsed_path), "missing": True}

    trace_log = ((result.get("audit_trace") or {}).get("diagnostics_log") or [])
    vision_values: list[Any] = []
    for event in trace_log:
        if not isinstance(event, dict):
            continue
        if str(event.get("kind") or "").startswith("vision"):
            vision_values.append(event)
    count, samples = _scan_question_marks(vision_values)
    stages["vision"] = {"count": count, "events": len(vision_values), "samples": samples}

    findings: list[Any] = []
    for key in ("results", "compliant_results", "review_results", "checks"):
        value = result.get(key)
        if isinstance(value, list):
            findings.extend(value)
    count, samples = _scan_question_marks(findings)
    stages["candidate_and_decision"] = {"count": count, "samples": samples}

    requirements: list[Any] = []
    rag_sources: list[Any] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        requirements.extend(finding.get("normative_requirements") or [])
        rag_sources.extend(finding.get("normative_sources") or [])
    count_req, samples_req = _scan_question_marks(requirements)
    count_rag, samples_rag = _scan_question_marks(rag_sources)
    stages["rag"] = {"count": count_rag, "samples": samples_rag}
    stages["requirements"] = {"count": count_req, "samples": samples_req}

    final_payload = dict(result)
    final_payload.pop("question_mark_trace", None)
    count, samples = _scan_question_marks(final_payload)
    stages["final_result"] = {"count": count, "samples": samples}

    first_stage = None
    for name in ("parser", "vision", "candidate_and_decision", "rag", "requirements", "final_result"):
        value = stages[name].get("count")
        if isinstance(value, int) and value > 0:
            first_stage = name
            break
    stages["first_detected_stage"] = first_stage
    stages["interpretation"] = (
        "Знак '?' обнаружен уже на стадии parser/vision/candidate/RAG/requirements; проверяйте samples и path."
        if first_stage
        else "В сохранённых стадиях literal '?' не найден; если он виден в браузере, проверять UI/шрифт/декодирование ответа API."
    )
    return stages


def _page_number_from_image(value: Any) -> int | None:
    match = re.search(r"page_(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def _build_vision_diagnostics(result: dict[str, Any], requested_pages: list[int]) -> dict[str, Any]:
    """Aggregate existing Vision audit events into an explicit per-page lifecycle."""
    trace = result.get("audit_trace") or {}
    events = trace.get("diagnostics_log") if isinstance(trace, dict) else []
    pages: dict[int, dict[str, Any]] = {}

    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict) or not str(event.get("kind") or "").startswith("vision"):
            continue
        page = _page_number_from_image(event.get("page_image"))
        if page is None:
            continue
        item = pages.setdefault(page, {
            "page": page,
            "status": "running",
            "vision_calls": 0,
            "parsed_candidates": 0,
            "recovery_calls": 0,
            "recovery_candidates": 0,
            "errors": 0,
        })
        kind = str(event.get("kind") or "")
        if kind == "vision_transport":
            item["vision_calls"] += 1
            if event.get("response_length") is not None:
                item["status"] = "completed"
        elif kind == "vision_parsed":
            item["parsed_candidates"] += int(event.get("parsed_count", 0) or 0)
            item["status"] = "completed"
        elif kind == "vision_recovery":
            item["recovery_calls"] += 1
        elif kind == "vision_recovery_parsed":
            item["recovery_candidates"] += int(event.get("parsed_count", 0) or 0)
            item["status"] = "completed"
        elif kind == "vision_error":
            item["errors"] += 1
            if item["status"] != "completed":
                item["status"] = "failed"

    scope = result.get("check_scope") or {}
    processed = sorted({int(x) for x in (scope.get("pages_processed") or scope.get("checked_pages") or [])})
    failed = sorted({int(x) for x in (scope.get("pages_failed") or scope.get("failed_pages") or [])})
    for page in requested_pages:
        item = pages.setdefault(page, {
            "page": page,
            "status": "not_processed",
            "vision_calls": 0,
            "parsed_candidates": 0,
            "recovery_calls": 0,
            "recovery_candidates": 0,
            "errors": 0,
        })
        if page in failed:
            item["status"] = "failed"
        elif page in processed:
            item["status"] = "completed"

    ordered = [pages[p] for p in sorted(pages)]
    pages_with_candidates = sorted({
        int(item["page"])
        for item in ordered
        if int(item.get("parsed_candidates", 0) or 0) > 0
        or int(item.get("recovery_candidates", 0) or 0) > 0
    })
    successful = sorted(set(processed) - set(failed))

    return {
        "pages_requested": sorted({int(x) for x in requested_pages}),
        "pages_processed": successful,
        "pages_with_candidates": pages_with_candidates,
        "pages_failed": failed,
        "requested_count": len(requested_pages),
        "processed_count": len(successful),
        "successful": len(successful),
        "failed": len(failed),
        "total_seconds": None,
        "average_seconds": None,
        "timing_note": "В текущем audit_trace длительность отдельных Vision вызовов не сохранялась; null означает отсутствие измерения, а не нулевое время.",
        "pages": ordered,
    }


def _enrich_pipeline_telemetry(document_root: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Fix scope semantics and attach telemetry before the immutable result is written."""
    payload = deepcopy(result)
    scope = dict(payload.get("check_scope") or {})
    checkpoint_path = document_root / "checking" / "first_pass" / "checkpoint.json"
    checkpoint: dict[str, Any] = {}
    if checkpoint_path.exists():
        try:
            value = json.loads(checkpoint_path.read_text(encoding="utf-8-sig"))
            if isinstance(value, dict):
                checkpoint = value
        except (OSError, json.JSONDecodeError):
            pass

    requested = sorted({int(x) for x in (scope.get("requested_pages") or checkpoint.get("selected_pages") or [])})
    processed = sorted({int(x) for x in (checkpoint.get("completed_pages") or []) if int(x) in requested})
    failed = sorted({int(x) for x in (scope.get("failed_pages") or []) if int(x) in requested})
    if str(payload.get("status") or "") == "completed" and requested:
        processed = requested

    scope.update({
        "pages_requested": requested,
        "pages_processed": sorted(set(processed) - set(failed)),
        "pages_failed": failed,
        "pages_checked": len(sorted(set(processed) - set(failed))),
        "requested_pages": requested,
        "checked_pages": sorted(set(processed) - set(failed)),
        "failed_pages": failed,
    })
    payload["check_scope"] = scope
    vision_diagnostics = _build_vision_diagnostics(payload, requested)
    scope["pages_with_candidates"] = vision_diagnostics["pages_with_candidates"]
    payload["check_scope"] = scope
    payload["vision_diagnostics"] = vision_diagnostics

    # Rebuild the public contract once telemetry and audit_trace are complete.
    from app.reporting.report_contract import prepare_public_report
    payload = prepare_public_report(payload)
    payload.pop("_pipeline_findings", None)
    return payload


def save_result(document_root: Path, result: dict[str, Any]) -> Path:
    """Write an immutable timestamped result artifact with provenance diagnostics."""
    directory = results_dir(document_root)
    payload = _enrich_pipeline_telemetry(document_root, result)
    payload["question_mark_trace"] = build_question_mark_trace(document_root, payload)
    stamp = _timestamp(str(payload.get("checked_at") or ""))
    path = directory / f"result_{stamp}.json"
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = directory / f"result_{stamp}.json"
    payload["result_file"] = path.name
    payload["result_id"] = path.stem
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

    if isinstance(result, dict):
        result.clear()
        result.update(payload)
    return path


def load_results(document_root: Path) -> list[dict[str, Any]]:
    directory = document_root / "checking" / "first_pass"
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in directory.glob("result_*.json"):
        if not _RESULT_RE.match(path.name):
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
