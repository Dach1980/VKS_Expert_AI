"""Real production-chain gate for the saved sewer_diameter candidate.

This experiment imports the production routing/retrieval/requirement-selection
functions without changing their implementation. It does not call Qwen. Instead,
it replaces the LM client only at the final decision boundary with a capture-only
client, so the exact prompt that production would send to Qwen is saved.

Required local state:
- the repository at the patched commit;
- the saved project document 53c22e43fcc843ef81f950516e81e68d;
- the currently indexed normative documents used by KnowledgeStorage.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.checking.audit_decision import decide_audit
from app.checking.resilient import _indexed_norms, _multi_context
from app.knowledge.storage import KnowledgeStorage
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_router import filter_retrievers, route_candidate

DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
REPORT_PATH = Path("knowledge") / "project_documents" / DOCUMENT_ID / "checking" / "first_pass" / "report.json"
OUTPUT_PATH = Path("training") / "evaluation" / "experiment_sewer_diameter_real_chain_20260915_result.json"

FORBIDDEN_NORM = "СП 32.13330.2018"
FORBIDDEN_CLAUSE = "6.3.5"
EXPECTED_NORM = "СП 30.13330.2020"


class CaptureOnlyClient:
    """Capture the exact production prompt without contacting LM Studio/Qwen."""

    def __init__(self) -> None:
        self.prompt: str | None = None

    def chat(self, prompt: str, **_: object) -> str:
        self.prompt = prompt
        return "{}"


def _load_saved_candidate() -> dict[str, object]:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    findings = report.get("results") or []
    finding = next(
        item for item in findings
        if item.get("id") == 5 and item.get("check_id") == "sewer_diameter"
    )
    table_check = finding.get("table_check") or {}
    evidence_text = str(table_check.get("evidence_text") or finding.get("evidence_text") or "").strip()
    return {
        "parameter": finding.get("parameter") or "диаметр выпуска",
        "title": finding.get("check_name") or "Диаметры",
        "description": finding.get("description") or "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
        "source_context": finding.get("source_context") or "Вводная часть раздела ВК о системе водоотведения.",
        "evidence_text": evidence_text,
        "project_value": finding.get("project_value_raw") or finding.get("project_value") or "Ø110мм",
    }


def main() -> None:
    candidate = _load_saved_candidate()
    storage = KnowledgeStorage()
    retrievers = _indexed_norms(storage)

    route = route_candidate(candidate, "vk_wastewater")
    scoped_retrievers = filter_retrievers(retrievers, route)
    retrieved = retrieve_audit_context(retrievers, candidate, top_k=6, skill_id="vk_wastewater")
    norm_text, requirements = _multi_context(retrieved, candidate)

    capture = CaptureOnlyClient()
    decide_audit(capture, candidate, norm_text)
    qwen_input = capture.prompt or ""

    selected_sources = [
        {
            "norm": item.get("norm"),
            "version": item.get("version"),
            "clause": item.get("clause"),
            "page": item.get("page"),
            "requirement": item.get("requirement"),
        }
        for item in requirements
    ]
    retrieved_sources = [
        {
            "norm": item.get("norm_number"),
            "version": item.get("version"),
            "page": item.get("page"),
            "clause": (item.get("metadata") or {}).get("clause"),
            "score": item.get("score"),
            "route_scope": item.get("route_scope"),
            "route_reason": item.get("route_reason"),
            "chunk_id": item.get("chunk_id"),
            "text": ((item.get("content") or {}).get("text") if isinstance(item.get("content"), dict) else ""),
        }
        for item in retrieved
    ]

    result = {
        "experiment": "sewer_diameter_real_chain",
        "date": "2026-09-15",
        "production_patch_scope": "app/rag/normative_requirement.py::_clause and requirement segment extraction",
        "document_id": DOCUMENT_ID,
        "candidate": candidate,
        "route": route,
        "scoped_retrievers": [
            {"number": d.get("number"), "version": v.get("id")}
            for d, v, _ in scoped_retrievers
        ],
        "retrieved_count": len(retrieved),
        "retrieved_sources": retrieved_sources,
        "selected_requirements": selected_sources,
        "qwen_input": qwen_input,
        "qwen_input_gate": {
            "forbidden_norm_present": FORBIDDEN_NORM in qwen_input,
            "forbidden_clause_present": FORBIDDEN_CLAUSE in qwen_input,
            "forbidden_requirement_present": any(
                item.get("norm") == FORBIDDEN_NORM and item.get("clause") == FORBIDDEN_CLAUSE
                for item in selected_sources
            ),
            "forbidden_norm_excluded": FORBIDDEN_NORM not in qwen_input,
            "forbidden_clause_excluded": FORBIDDEN_CLAUSE not in qwen_input,
            "expected_internal_norm_selected": any(
                item.get("norm") == EXPECTED_NORM for item in selected_sources
            ),
            "expected_clause_selected": any(
                item.get("norm") == EXPECTED_NORM
                and item.get("clause") == "18.34"
                and str(item.get("requirement") or "").startswith("18.34 ")
                for item in selected_sources
            ),
        },
    }
    gate = result["qwen_input_gate"]
    result["status"] = (
        "PASS"
        if route.get("scope") == "internal_wastewater"
        and gate["forbidden_norm_excluded"]
        and gate["forbidden_clause_excluded"]
        and gate["expected_internal_norm_selected"]
        and gate["expected_clause_selected"]
        else "FAIL"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
