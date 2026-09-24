from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]

REGULATIONS = ROOT / "knowledge" / "regulations"
STRUCTURED = ROOT / "knowledge" / "structured"
VECTORDB = ROOT / "data" / "vectordb"

DOCS = [
    "СП_30.13330.2020",
    "СП_31.13330.2021",
    "СП_32.13330.2018",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_load(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def find_structured(doc_number: str):
    candidates = sorted(STRUCTURED.glob(f"{doc_number}*.json"))
    return candidates


def inspect_version(version_dir: Path):
    emb = version_dir / "embeddings"
    return {
        "version_id": version_dir.name,
        "path": str(version_dir.relative_to(ROOT)),
        "index_faiss": (emb / "index.faiss").exists(),
        "metadata_json": (emb / "metadata.json").exists(),
        "index_size": (
            (emb / "index.faiss").stat().st_size
            if (emb / "index.faiss").exists()
            else None
        ),
        "metadata_size": (
            (emb / "metadata.json").stat().st_size
            if (emb / "metadata.json").exists()
            else None
        ),
        "document_chunks": (version_dir / "document_chunks").exists(),
        "pages": (version_dir / "pages").exists(),
        "enriched": (version_dir / "enriched").exists(),
    }


result = {
    "root": str(ROOT),
    "documents": [],
}

for doc in DOCS:
    print("\n" + "=" * 100)
    print(doc)
    print("=" * 100)

    pdf_root = REGULATIONS / doc
    vector_root = VECTORDB / doc

    pdfs = sorted(pdf_root.glob("*.pdf")) if pdf_root.exists() else []
    structured = find_structured(doc)
    versions = (
        sorted([p for p in vector_root.iterdir() if p.is_dir()])
        if vector_root.exists()
        else []
    )

    print("\nPDF:")
    for p in pdfs:
        print(f"  {p.relative_to(ROOT)}")
        print(f"    sha256={sha256(p)}")

    print("\nSTRUCTURED:")
    for p in structured:
        data = json_load(p)
        print(f"  {p.relative_to(ROOT)}")

        if isinstance(data, dict):
            print(f"    keys={list(data.keys())[:15]}")

            for key in (
                "id",
                "document_id",
                "document_number",
                "version_id",
                "source",
                "edition",
                "normative",
            ):
                if key in data:
                    value = data[key]
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)[:500]
                    print(f"    {key}={value}")

    print("\nVECTOR VERSIONS:")
    for v in versions:
        info = inspect_version(v)

        print(f"\n  VERSION: {info['version_id']}")
        print(f"    path={info['path']}")
        print(f"    index.faiss={info['index_faiss']} ({info['index_size']} bytes)")
        print(f"    metadata.json={info['metadata_json']} ({info['metadata_size']} bytes)")
        print(f"    document_chunks={info['document_chunks']}")
        print(f"    pages={info['pages']}")
        print(f"    enriched={info['enriched']}")

        metadata = v / "embeddings" / "metadata.json"

        if metadata.exists():
            data = json_load(metadata)

            if isinstance(data, dict):
                print(f"    metadata.keys={list(data.keys())[:20]}")

                for key in (
                    "document_id",
                    "version_id",
                    "document_number",
                    "normative",
                    "source",
                    "edition",
                ):
                    if key in data:
                        value = data[key]
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False)[:1000]
                        print(f"    metadata.{key}={value}")

    result["documents"].append({
        "document": doc,
        "pdf": [str(p.relative_to(ROOT)) for p in pdfs],
        "structured": [str(p.relative_to(ROOT)) for p in structured],
        "versions": [inspect_version(v) for v in versions],
    })


out = ROOT / "training" / "evaluation" / "normative_mapping_20260917.json"
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 100)
print(f"RESULT JSON: {out}")
print("=" * 100)
