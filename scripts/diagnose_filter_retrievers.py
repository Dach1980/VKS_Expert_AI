"""Diagnostic pass for normative retriever routing/filtering.

This script does not modify production code. It reproduces the transition:

    route_candidate() -> _indexed_norms() -> filter_retrievers()

and prints the exact values used by filter_retrievers(), including each
matching condition.

Run from the repository root:

    python scripts/diagnose_filter_retrievers.py
"""

from __future__ import annotations

import json

from app.checking.resilient import _indexed_norms
from app.knowledge.storage import KnowledgeStorage
from app.rag.normative_router import filter_retrievers, route_candidate


CANDIDATE = {
    "parameter": "диаметр выпуска",
    "title": "Диаметры",
    "description": "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
    "source_context": "Вводная часть раздела ВК о системе водоотведения.",
    "evidence_text": (
        "Бытовые стоки от приборов в санузлах и КУИ, от трапов технических и "
        "душевых помещений, а также от опорожнения сетей водоснабжения и "
        "отопления в количестве 3,58 л/с, 4,34 м³/ч, 8,48 м³/сут отводятся "
        "системой внутренней самотечной бытовой канализации по пяти выпускам "
        "Ø110мм в внутриплощадочную сеть бытовой канализации Ø160 мм."
    ),
    "project_value": "Ø110мм",
}


def main() -> int:
    storage = KnowledgeStorage()

    route = route_candidate(CANDIDATE)
    retrievers = _indexed_norms(storage)
    selected = filter_retrievers(retrievers, route)

    allowed = {
        str(value).strip().lower()
        for value in route.get("normative_documents", [])
    }

    print("=== filter_retrievers() diagnostic ===")
    print()
    print("PROJECT CANDIDATE:")
    print(json.dumps(CANDIDATE, ensure_ascii=False, indent=2))
    print()
    print("ROUTE:")
    print(json.dumps(route, ensure_ascii=False, indent=2))
    print()
    print("ALLOWED NORMALIZED DOCUMENT NUMBERS:")
    for value in sorted(allowed):
        print(f"  - {value}")
    print()
    print(f"_indexed_norms() returned: {len(retrievers)} retrievers")
    print()

    print("RETRIEVERS AND EXACT FILTER CONDITIONS:")
    for index, item in enumerate(retrievers, start=1):
        document, version, _retriever = item
        number = str(
            document.get("number")
            or document.get("id")
            or ""
        ).strip().lower()
        title = str(document.get("title") or "").strip().lower()

        condition_1 = number in allowed
        condition_2_matches = [
            value for value in allowed if number and number in value
        ]
        condition_3_matches = [
            value for value in allowed if value and value in title
        ]

        print(f"[{index}]")
        print(f"  document.id:       {document.get('id')}")
        print(f"  document.number:   {document.get('number')!r}")
        print(f"  normalized number: {number!r}")
        print(f"  document.title:    {document.get('title')!r}")
        print(f"  normalized title:  {title!r}")
        print(f"  condition #1 number in allowed: {condition_1}")
        print(f"  condition #2 number-in-value matches: {condition_2_matches}")
        print(f"  condition #3 value-in-title matches: {condition_3_matches}")
        print(
            "  FINAL FILTER MATCH: "
            f"{condition_1 or bool(condition_2_matches) or bool(condition_3_matches)}"
        )
        print(
            f"  version.id:        {version.get('id')}"
        )
        print()

    print("FILTER RESULT:")
    print(f"  selected retrievers: {len(selected)}")
    for index, (document, version, _retriever) in enumerate(selected, start=1):
        print(
            f"  [{index}] {document.get('number')} "
            f"({document.get('id')}) -> version {version.get('id')}"
        )

    print()
    print("EXPECTED BASELINE:")
    print("  СП 30.13330.2020 must be selected for this candidate.")
    print(
        "  If selected retrievers = 0, the failure is in routing/filtering "
        "before retriever.search()."
    )
    print(
        "  If selected retrievers = 1 and it is СП 30.13330.2020, "
        "routing/filtering is working and the next diagnostic target is "
        "retriever.search()."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
