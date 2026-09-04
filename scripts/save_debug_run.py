"""Save a completed checking report as a versioned debug experiment artifact."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def compact_metrics(report: dict) -> dict:
    summary = report.get("summary") or {}
    scope = report.get("check_scope") or {}
    diagnostics = report.get("diagnostics") or {}
    trace = report.get("trace") or report.get("audit_trace") or {}
    matrix = diagnostics.get("matrix") or []

    return {
        "pages_checked": scope.get("pages_checked", summary.get("pages", 0)),
        "pages_available": scope.get("pages_available", summary.get("pages_available", 0)),
        "limited": bool(scope.get("limited", False)),
        "remarks": summary.get("violations", len(report.get("remarks") or [])),
        "compliant": summary.get("compliant", len(report.get("compliant_results") or [])),
        "unchecked": summary.get("unchecked", len(report.get("review_results") or [])),
        "trace": {
            "raw_visual_candidates": trace.get("raw_visual_candidates", 0),
            "strict_candidates": trace.get("strict_candidates", 0),
            "skill_candidates": trace.get("skill_candidates", 0),
            "bbox_valid": trace.get("bbox_valid", 0),
            "rag_calls": trace.get("rag_calls", 0),
            "rag_hits": trace.get("rag_hits", 0),
            "requirements_seen": trace.get("requirements_seen", 0),
            "requirements_with_clause": trace.get("requirements_with_clause", 0),
            "decisions": trace.get("decisions", 0),
            "violations": trace.get("violations", 0),
            "compliant": trace.get("compliant", 0),
            "unchecked": trace.get("unchecked", 0),
            "visual_recovery_pages": trace.get("visual_recovery_pages", 0),
            "visual_recovery_candidates": trace.get("visual_recovery_candidates", 0),
        },
        "check_matrix": matrix,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--quantization", default="unknown")
    parser.add_argument("--label", default="run")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    report_path = ROOT / "knowledge" / "project_documents" / args.document_id / "checking" / "first_pass" / "report.json"
    if not report_path.exists():
        raise SystemExit(f"report.json not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ROOT / "debug" / "runs" / f"{timestamp}_{args.label}_{args.document_id}"
    run_dir.mkdir(parents=True, exist_ok=False)

    copy2(report_path, run_dir / "report.json")
    meta = {
        "run_id": run_dir.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "label": args.label,
        "document_id": args.document_id,
        "document_name": report.get("document_name", ""),
        "skill_id": report.get("skill_id", ""),
        "skill_name": report.get("skill_name", ""),
        "model": args.model,
        "quantization": args.quantization,
        "notes": args.notes,
        "metrics": compact_metrics(report),
    }
    (run_dir / "run_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved debug run: {run_dir.relative_to(ROOT)}")
    print(f"Git commit: {meta['git_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
