from __future__ import annotations

import json

from app.reporting.result_store import build_question_mark_trace, save_result


def test_question_mark_trace_finds_parser_origin(tmp_path):
    root = tmp_path / "document"
    root.mkdir()
    (root / "parsed.json").write_text(json.dumps({"pages": [{"text": "ООО ? проект"}], "bbox": [1, 2, 3, 4]}, ensure_ascii=False), encoding="utf-8")

    trace = build_question_mark_trace(root, {"document_id": "test", "results": []})

    assert trace["parser"]["count"] == 1
    assert trace["first_detected_stage"] == "parser"


def test_question_mark_trace_does_not_count_its_own_diagnostic(tmp_path):
    root = tmp_path / "document"
    root.mkdir()

    trace = build_question_mark_trace(root, {"document_id": "test", "results": []})

    assert trace["final_result"]["count"] == 0
    assert trace["first_detected_stage"] is None


def test_save_result_uses_timestamped_filename_and_metadata(tmp_path):
    root = tmp_path / "document"
    root.mkdir()
    result = {"document_id": "test", "checked_at": "2026-09-07T13:09:17", "results": []}

    path = save_result(root, result)

    assert path.name == "result_20260907_130917.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["result_file"] == path.name
    assert saved["result_id"] == "result_20260907_130917"
    assert "question_mark_trace" in saved
