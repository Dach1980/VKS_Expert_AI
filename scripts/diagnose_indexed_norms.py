"""Diagnostic pass for the indexed normative documents used by _indexed_norms().

This script intentionally does not modify production code and does not swallow
exceptions from Retriever(). It reports the exact point at which a normative
document fails to become an indexed Retriever.

Run from the repository root:
    python scripts/diagnose_indexed_norms.py

Optional:
    python scripts/diagnose_indexed_norms.py --json
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

from app.knowledge.storage import KnowledgeStorage
from app.rag.retriever import Retriever


def diagnose_document(storage: KnowledgeStorage, document: dict) -> dict:
    result = {
        "document_id": document.get("id"),
        "document_number": document.get("number"),
        "current_version": None,
        "paths_embeddings": None,
        "index_faiss_exists": False,
        "metadata_json_exists": False,
        "retriever_created": False,
        "retriever_error": None,
        "retriever_error_type": None,
    }

    try:
        version = storage.get_current_version(document["id"])
        result["current_version"] = version.get("id") if version else None

        if not version or not version.get("id"):
            raise RuntimeError("Current version is missing or has no id")

        paths = storage.paths(document["id"], version["id"])
        result["paths_embeddings"] = str(paths.embeddings)
        index_file = paths.embeddings / "index.faiss"
        metadata_file = paths.embeddings / "metadata.json"
        result["index_faiss_exists"] = index_file.exists()
        result["metadata_json_exists"] = metadata_file.exists()

        # Match _indexed_norms() exactly: Retriever is only attempted when
        # both index files are present.
        if result["index_faiss_exists"] and result["metadata_json_exists"]:
            Retriever(document["id"], version["id"], storage)
            result["retriever_created"] = True
        else:
            missing = []
            if not result["index_faiss_exists"]:
                missing.append(str(index_file))
            if not result["metadata_json_exists"]:
                missing.append(str(metadata_file))
            result["retriever_error"] = (
                "Retriever() not attempted because required file(s) are missing: "
                + "; ".join(missing)
            )
            result["retriever_error_type"] = "MissingIndexedFiles"

    except Exception as error:
        result["retriever_error_type"] = type(error).__name__
        result["retriever_error"] = str(error)
        result["traceback"] = traceback.format_exc()

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose _indexed_norms() without swallowing exceptions."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the human-readable report.",
    )
    args = parser.parse_args()

    storage = KnowledgeStorage()
    documents = storage.registry.get_all_documents()
    results = [diagnose_document(storage, document) for document in documents]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("=== _indexed_norms() diagnostic ===")
    print(f"Repository root: {Path(__file__).resolve().parents[1]}")
    print(f"Registry documents: {len(documents)}")
    print()

    for index, item in enumerate(results, start=1):
        print(f"[{index}] {item['document_number']} ({item['document_id']})")
        print(f"  current_version:       {item['current_version']}")
        print(f"  paths.embeddings:      {item['paths_embeddings']}")
        print(f"  index.faiss exists:    {item['index_faiss_exists']}")
        print(f"  metadata.json exists:  {item['metadata_json_exists']}")
        print(f"  Retriever() created:   {item['retriever_created']}")
        if item["retriever_error"]:
            print(f"  Retriever() error:     {item['retriever_error_type']}: {item['retriever_error']}")
            if item.get("traceback"):
                print("  traceback:")
                print(item["traceback"].rstrip())
        print()

    indexed_count = sum(1 for item in results if item["retriever_created"])
    print(f"Indexed Retrievers created: {indexed_count}/{len(results)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
