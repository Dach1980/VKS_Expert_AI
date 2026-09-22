"""Diagnostic for the audit retrieval -> normative requirement selection chain.

Diagnostic-only script. It reproduces the real baseline candidate and prints:
1. retrieve_audit_context() output;
2. select_normative_requirements() output;
3. the exact production _multi_context() filtering result.

No production code is modified.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.checking.resilient import _indexed_norms, _multi_context
from app.knowledge.storage import KnowledgeStorage
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_requirement import select_normative_requirements
from app.skills.registry import route_candidate
from app.rag.normative_router import filter_retrievers


CANDIDATE = {
    "parameter": "диаметр выпуска",
    "title": "Диаметры",
    "description": "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
    "source_context": "Вводная часть раздела ВК о системе водоотведения.",
    "evidence_text": (
        "Бытовые стоки от приборов в санузлах и КУИ, от трапов технических и "
        "душевых помещений, а также от опорожнения сетей водоснабжения и отопления "
        "в количестве 3,58 л/с, 4,34 м³/ч, 8,48 м³/сут отводятся системой внутренней "
        "самотечной бытовой канализации по пяти выпускам Ø110мм в внутриплощадочную "
        "сеть бытовой канализации Ø160 мм."
    ),
    "project_value": "Ø110мм",
}


def dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def print_result(i: int, result: dict) -> None:
    print(f"\nRESULT #{i}")
    print(f"  page: {result.get('page')}")
    print(f"  score: {result.get('score')}")
    print(f"  source: {result.get('source')}")
    print(f"  type: {result.get('type')}")
    print(f"  chunk_id: {result.get('chunk_id')}")
    print(f"  norm_number: {result.get('norm_number')}")
    print(f"  version: {result.get('version')}")
    print(f"  metadata: {result.get('metadata')}")
    print("  content:")
    print(str(result.get("content", ""))[:1800])


def main() -> None:
    print("=== Requirement selection diagnostic ===")
    print(f"Repository root: {ROOT}")

    skill_id = "vk_wastewater"
    route = route_candidate(CANDIDATE, skill_id)
    print("\nROUTE:")
    dump(route)

    storage = KnowledgeStorage()
    norms = _indexed_norms(storage)
    print(f"\n_indexed_norms(): {len(norms)}")
    for document, version, _ in norms:
        print(
            f"  - {document.get('number')} ({document.get('id')})"
            f" -> {version.get('id')}"
        )

    scoped = filter_retrievers(norms, route)
    print(f"filter_retrievers(): {len(scoped)}")
    for document, version, _ in scoped:
        print(f"  - {document.get('number')} -> {version.get('id')}")

    print("\nSTEP 1: retrieve_audit_context()")
    results = retrieve_audit_context(
        norms,
        CANDIDATE,
        top_k=6,
        skill_id=skill_id,
    )
    print(f"RETRIEVED CONTEXT COUNT: {len(results)}")
    for i, result in enumerate(results, 1):
        print_result(i, result)

    print("\nSTEP 2: select_normative_requirements()")
    selected = select_normative_requirements(
        results,
        str(CANDIDATE.get("parameter") or ""),
        limit=4,
    )
    print(f"SELECTED REQUIREMENTS COUNT: {len(selected)}")
    for i, item in enumerate(selected, 1):
        print(f"\nREQUIREMENT #{i}")
        print(f"  norm: {item.get('norm')}")
        print(f"  version: {item.get('version')}")
        print(f"  clause: {item.get('clause')!r}")
        print(f"  requirement_relevance: {item.get('requirement_relevance')}")
        print(f"  has_concrete_clause: {item.get('has_concrete_clause')}")
        print(f"  has_numeric_rule: {item.get('has_numeric_rule')}")
        print(f"  operator: {item.get('operator')!r}")
        print(f"  normative_value: {item.get('normative_value')}")
        print(f"  normative_unit: {item.get('normative_unit')!r}")
        print(f"  page: {item.get('page')}")
        print(f"  metadata_text: {item.get('metadata_text')!r}")
        print("  requirement text:")
        print(str(item.get("requirement") or "")[:1800])

    print("\nSTEP 3: exact production _multi_context() filter")
    norm_text, production_requirements = _multi_context(results, CANDIDATE)
    print(f"PRODUCTION REQUIREMENTS COUNT: {len(production_requirements)}")
    for i, item in enumerate(production_requirements, 1):
        print(
            f"  #{i}: norm={item.get('norm')!r}, "
            f"clause={item.get('clause')!r}, "
            f"requirement_nonempty={bool(str(item.get('requirement') or '').strip())}"
        )

    print("\nPRODUCTION NORM TEXT:")
    print(norm_text[:8000] if norm_text else "<EMPTY>")

    print("\nFINAL DIAGNOSTIC:")
    if not results:
        print("FAILURE_STAGE=retrieve_audit_context")
    elif not selected:
        print("FAILURE_STAGE=select_normative_requirements")
    elif not production_requirements:
        print("FAILURE_STAGE=_multi_context_production_filter")
    else:
        print("FAILURE_STAGE=after_requirement_selection")
        print("Requirement selection and production _multi_context() filter both returned data.")

if __name__ == "__main__":
    main()
