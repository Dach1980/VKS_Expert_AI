"""Diagnostic for the production normative retriever.search() stage.

Reproduces the baseline wastewater candidate and traces:
candidate -> route -> indexed norms -> filter_retrievers -> build_audit_queries
-> Retriever.search(), including both the primary and conditional fallback query.

This script is diagnostic-only and does not modify production code or indexes.
"""
from __future__ import annotations

import json
import traceback

from app.checking.resilient import _indexed_norms
from app.knowledge.storage import KnowledgeStorage
from app.rag.audit_retrieval import build_audit_queries
from app.rag.normative_router import filter_retrievers, route_candidate


CANDIDATE = {
    "parameter": "диаметр выпуска",
    "title": "Диаметры",
    "description": "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
    "source_context": "Вводная часть раздела ВК о системе водоотведения.",
    "evidence_text": (
        "Бытовые стоки от приборов в санузлах и КУИ, от трапов технических и "
        "душевых помещений, а также от опорожнения сетей водоснабжения и отопления "
        "в количестве 3,58 л/с, 4,34 м³/ч, 8,48 м³/сут отводятся системой "
        "внутренней самотечной бытовой канализации по пяти выпускам Ø110мм "
        "в внутриплощадочную сеть бытовой канализации Ø160 мм."
    ),
    "project_value": "Ø110мм",
}


def print_result(index: int, result: dict) -> None:
    content = result.get("content", {})
    text = content.get("text", "") if isinstance(content, dict) else str(content)
    print(
        f"\nRESULT #{index}"
        f"\n  page:       {result.get('page')}"
        f"\n  score:      {float(result.get('score', 0) or 0):.6f}"
        f"\n  source:     {result.get('source')}"
        f"\n  type:       {result.get('type')}"
        f"\n  chunk_id:   {result.get('chunk_id')}"
    )
    print(f"  content:    {str(text)[:1200].replace(chr(10), ' ')}")
    if isinstance(content, dict):
        formula = content.get("formula")
        if formula:
            print(f"  formula:    {formula}")
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        print(
            "  metadata:   "
            + json.dumps(metadata, ensure_ascii=False, separators=(", ", ": "))
        )


def main() -> None:
    print("=== Retriever.search() diagnostic ===")
    print("\nPROJECT CANDIDATE:")
    print(json.dumps(CANDIDATE, ensure_ascii=False, indent=2))

    route = route_candidate(CANDIDATE, "vk_wastewater")
    print("\nROUTE:")
    print(json.dumps(route, ensure_ascii=False, indent=2))

    storage = KnowledgeStorage()
    retrievers = _indexed_norms(storage)
    print(f"\n_indexed_norms() returned: {len(retrievers)} retrievers")

    scoped = filter_retrievers(retrievers, route)
    print(f"filter_retrievers() selected: {len(scoped)} retrievers")
    for document, version, _retriever in scoped:
        print(
            f"  - {document.get('number')} "
            f"({document.get('id')}) -> version {version.get('id')}"
        )

    if not scoped:
        print("\nDIAGNOSTIC CONCLUSION: FAIL before retriever.search().")
        print("No scoped retriever was selected.")
        return

    queries = build_audit_queries(CANDIDATE)
    print(f"\nBUILT AUDIT QUERIES: {len(queries)}")
    for i, query in enumerate(queries, 1):
        print(f"\nQUERY #{i} ({len(query)} chars):")
        print(query)

    total_results = 0
    successful_queries = 0

    for query_index, query in enumerate(queries, 1):
        print(f"\n=== SEARCH QUERY #{query_index} ===")
        for document, version, retriever in scoped:
            print(
                f"DOCUMENT: {document.get('number')} ({document.get('id')})"
                f"\nVERSION:  {version.get('id')}"
            )
            try:
                results = retriever.search(query, top_k=6)
                successful_queries += 1
                total_results += len(results)
                print(f"SEARCH RESULT COUNT: {len(results)}")
                for result_index, result in enumerate(results, 1):
                    print_result(result_index, result)
            except Exception as error:
                print(f"SEARCH ERROR: {type(error).__name__}: {error}")
                traceback.print_exc()

    print("\n=== DIAGNOSTIC CONCLUSION ===")
    print(f"Queries built:             {len(queries)}")
    print(f"Successful search calls:   {successful_queries}")
    print(f"Total returned results:    {total_results}")
    if total_results == 0:
        print("Retriever.search() returned ZERO results for all diagnostic queries.")
        print("Next target: embedding/search/index behavior inside Retriever.search().")
    else:
        print("Retriever.search() returned results.")
        print("Next target: downstream audit retrieval / requirement selection.")
    

if __name__ == "__main__":
    main()
