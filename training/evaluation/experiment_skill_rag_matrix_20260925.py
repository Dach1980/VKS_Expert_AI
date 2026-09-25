"""Run a real Visual -> Skill -> RAG -> Requirement audit matrix.

Unlike the earlier saved-report replay, this experiment starts from the source PDF
and uses the production visual prompt, strict candidate validation, Skill filtering,
bbox evidence gate, indexed normative retrieval and normative requirement
selection. It deliberately stops before Qwen compliance classification.

The experiment is diagnostic only: it does not write the production first-pass
report/checkpoint and does not modify production behavior.

Required local state:
- source PDF for document 53c22e43fcc843ef81f950516e81e68d;
- current KnowledgeStorage registry and indexed normative versions;
- LM Studio running with an available vision-capable chat model.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.checking.first_pass import _json_array, _strict_candidates, _vision_request
from app.checking.page_pipeline import PageEvidence, normalize_bbox, render_pdf_pages
from app.checking.resilient import (
    CHECK_DPI,
    _bbox_has_real_evidence,
    _indexed_norms,
    _filter_skill_candidates,
    _multi_context,
)
from app.knowledge.storage import KnowledgeStorage
from app.llm.lmstudio_client import LMStudioClient
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_router import filter_retrievers, route_candidate
from app.skills.registry import get_skill

DOCUMENT_ID = "53c22e43fcc843ef81f950516e81e68d"
SKILL_ID = "vk_wastewater"
SOURCE_PDF = (
    Path("knowledge")
    / "project_documents"
    / DOCUMENT_ID
    / "source.pdf"
)
OUTPUT_PATH = Path("data") / "skill_rag_matrix_20260925_result.json"

def _load_existing_rendered_pages(render_dir: Path) -> list[PageEvidence]:
    """Reuse first-pass page images when the original PDF is intentionally untracked."""
    images = sorted(render_dir.glob("page_*.png"))
    if not images:
        return []
    try:
        from PIL import Image
    except ImportError:
        return []
    pages: list[PageEvidence] = []
    for index, image_path in enumerate(images, start=1):
        with Image.open(image_path) as image:
            width, height = image.size
        pages.append(PageEvidence(index, str(image_path), width, height))
    return pages


def _build_matrix(skill: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(check["id"]): {
            "check_id": str(check["id"]),
            "name": str(check["name"]),
            "raw_visual_candidates": 0,
            "strict_candidates": 0,
            "skill_candidates": 0,
            "bbox_valid": 0,
            "bbox_rejected": 0,
            "rag_calls": 0,
            "rag_hits": 0,
            "route_passes": 0,
            "requirements": 0,
            "candidate_results": [],
            "drop_reasons": [],
        }
        for check in skill["checks"]
    }


def _status(item: dict[str, object]) -> str:
    skill_candidates = int(item["skill_candidates"])
    if skill_candidates == 0:
        return "NO_CANDIDATE"
    if int(item["bbox_valid"]) == 0:
        return "NO_VALID_BBOX"
    if int(item.get("route_passes", 0)) == 0:
        return "ROUTE_FAIL"
    if int(item["rag_hits"]) == 0:
        return "RAG_NO_HIT"
    if int(item["requirements"]) == 0:
        return "NO_REQUIREMENT"
    return "PASS"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Limit the diagnostic run to the first N PDF pages; 0 means all pages.",
    )
    args = parser.parse_args()

    skill = get_skill(SKILL_ID)
    storage = KnowledgeStorage()
    indexed_norms = _indexed_norms(storage)
    if not indexed_norms:
        raise SystemExit("No indexed normative documents are available")

    render_dir = Path("data") / "skill_rag_matrix_pages"
    if SOURCE_PDF.exists():
        pages = render_pdf_pages(SOURCE_PDF, render_dir, dpi=CHECK_DPI)
        source_mode = "source_pdf"
    else:
        existing_dir = SOURCE_PDF.parent / "checking" / "first_pass"
        pages = _load_existing_rendered_pages(existing_dir)
        source_mode = "existing_first_pass_render"
    pages_available = len(pages)
    if not pages:
        raise SystemExit(
            "Source PDF not found and no existing first-pass page images were found. "
            f"Expected PDF: {SOURCE_PDF}; expected rendered pages: "
            f"{SOURCE_PDF.parent / 'checking' / 'first_pass' / 'page_*.png'}"
        )    if args.max_pages > 0:
        pages = pages[:args.max_pages]
    if not pages:
        raise SystemExit("No PDF pages available for the experiment")

    matrix = _build_matrix(skill)
    vision_model = LMStudioClient(model=None)

    raw_visual_candidates = 0
    strict_candidates = 0
    skill_candidates = 0
    bbox_valid = 0
    bbox_rejected = 0
    rag_calls = 0
    rag_hits = 0
    requirements_seen = 0

    print(
        json.dumps(
            {
                "experiment": "skill_rag_matrix",
                "stage": "start",
                "document_id": DOCUMENT_ID,
                "skill_id": SKILL_ID,
                "pages": len(pages),
                "indexed_norms": [
                    {"number": d.get("number"), "version": v.get("id")}
                    for d, v, _ in indexed_norms
                ],
                "decision_stage": "not_run",
                "source_mode": source_mode,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    for page_index, page in enumerate(pages, start=1):
        print(f"[SKILL-RAG] page {page_index}/{len(pages)}")

        prompt = __import__(
            "app.checking.vk_audit",
            fromlist=["build_vk_audit_prompt"],
        ).build_vk_audit_prompt(page.page, SKILL_ID)

        raw = _json_array(
            _vision_request(
                vision_model,
                prompt,
                Path(page.image_path),
                1400,
            )
        )
        raw_visual_candidates += len(raw)
        for candidate in raw:
            check_id = str(candidate.get("check_id") or "")
            if check_id in matrix:
                matrix[check_id]["raw_visual_candidates"] += 1

        strict = _strict_candidates(raw)
        strict_candidates += len(strict)
        for candidate in strict:
            check_id = str(candidate.get("check_id") or "")
            if check_id in matrix:
                matrix[check_id]["strict_candidates"] += 1

        filtered = _filter_skill_candidates(strict, skill, page.page)
        skill_candidates += len(filtered)

        for candidate in filtered:
            check_id = str(candidate.get("check_id") or "")
            item = matrix.get(check_id)
            if item is None:
                continue
            item["skill_candidates"] += 1

            bbox = normalize_bbox(
                candidate.get("bbox"),
                page.width,
                page.height,
            )
            if not bbox or not _bbox_has_real_evidence(
                Path(page.image_path),
                bbox,
            ):
                bbox_rejected += 1
                item["bbox_rejected"] += 1
                item["drop_reasons"].append(
                    {"page": page.page, "reason": "bbox_geometry_or_empty_evidence"}
                )
                continue

            bbox_valid += 1
            item["bbox_valid"] += 1

            route = route_candidate(candidate, SKILL_ID)
            scoped = filter_retrievers(indexed_norms, route)
            if route.get("scope") and scoped:
                item["route_passes"] += 1
            retrieved = retrieve_audit_context(
                indexed_norms,
                candidate,
                top_k=6,
                skill_id=SKILL_ID,
            )
            rag_calls += 1
            item["rag_calls"] += 1
            if retrieved:
                rag_hits += 1
                item["rag_hits"] += 1

            _, requirements = _multi_context(retrieved, candidate)
            requirements_seen += len(requirements)
            item["requirements"] += len(requirements)

            item["candidate_results"].append(
                {
                    "page": page.page,
                    "title": candidate.get("title"),
                    "parameter": candidate.get("parameter"),
                    "project_value": candidate.get("project_value"),
                    "evidence_text": candidate.get("evidence_text"),
                    "route": route,
                    "scoped_retrievers": [
                        {
                            "number": d.get("number"),
                            "version": v.get("id"),
                        }
                        for d, v, _ in scoped
                    ],
                    "retrieved_count": len(retrieved),
                    "requirements": [
                        {
                            "norm": req.get("norm"),
                            "version": req.get("version"),
                            "page": req.get("page"),
                            "clause": req.get("clause"),
                            "requirement": req.get("requirement"),
                        }
                        for req in requirements
                    ],
                }
            )

    for item in matrix.values():
        item["status"] = _status(item)

    counts = Counter(str(item["status"]) for item in matrix.values())
    result = {
        "experiment": "skill_rag_matrix",
        "date": "2026-09-25",
        "document_id": DOCUMENT_ID,
        "skill_id": SKILL_ID,
        "pages_checked": len(pages),
        "pages_available": pages_available,
        "source_mode": source_mode,
        "indexed_norms": [
            {"number": d.get("number"), "version": v.get("id")}
            for d, v, _ in indexed_norms
        ],
        "pipeline": [
            "Vision",
            "strict_candidate_validation",
            "Skill_filter",
            "bbox_evidence_gate",
            "routing",
            "scoped_RAG",
            "normative_requirement_selection",
        ],
        "decision_stage": "not_run",
        "aggregate": {
            "raw_visual_candidates": raw_visual_candidates,
            "strict_candidates": strict_candidates,
            "skill_candidates": skill_candidates,
            "bbox_valid": bbox_valid,
            "bbox_rejected": bbox_rejected,
            "rag_calls": rag_calls,
            "rag_hits": rag_hits,
            "requirements": requirements_seen,
        },
        "status_counts": dict(counts),
        "matrix": list(matrix.values()),
        "note": (
            "This is a real source-PDF diagnostic. It does not replay saved "
            "findings, call Qwen compliance classification, write the production "
            "first-pass report, or classify violation/compliant/unchecked."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
