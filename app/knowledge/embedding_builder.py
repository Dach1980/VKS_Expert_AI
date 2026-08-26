import json
import os
from pathlib import Path
from datetime import datetime

import numpy as np
import faiss

from sentence_transformers import SentenceTransformer


# ============================================================
# VKS Expert AI
# Embedding Builder v1
# ============================================================


BASE_DIR = Path(__file__).resolve().parents[2]


DOCUMENT = "SP_30.13330"


ENRICHED_DIR = (
    BASE_DIR
    / "knowledge"
    / "index"
    / DOCUMENT
    / "enriched"
)


OUTPUT_DIR = (
    BASE_DIR
    / "knowledge"
    / "index"
    / DOCUMENT
    / "embeddings"
)


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------


def ensure_dirs():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def load_pages():

    pages = []

    files = sorted(
        ENRICHED_DIR.glob(
            "page_*_enriched.json"
        )
    )

    print(
        f"Pages found: {len(files)}"
    )

    for file in files:

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        pages.append(data)

    return pages



def build_embedding_records(pages):

    records = []

    counter = 0


    for page in pages:


        page_number = page.get(
            "page",
            page.get(
                "page_number",
                0
            )
        )


        text_blocks = page.get(
            "text_blocks",
            []
        )


        formulas = page.get(
            "formulas",
            []
        )


        text_parts = []


        for block in text_blocks:

            if isinstance(block, dict):

                text = block.get(
                    "text",
                    ""
                )

            else:

                text = str(block)


            if text:

                text = str(text).strip()

                if text:

                    text_parts.append(
                        text
                    )


        for formula in formulas:

            if isinstance(formula, dict):

                latex = formula.get(
                    "latex"
                )

            else:

                latex = formula


            if latex:

                latex = str(latex).strip()


                if latex:

                    text_parts.append(
                        "Формула: "
                        + latex
                    )


        if not text_parts:

            continue


        content = "\n".join(
            text_parts
        )


        counter += 1


        records.append(
            {
                "id": counter,

                "document": DOCUMENT,

                "page": page_number,

                "text": content,

                "created": datetime.now().isoformat()
            }
        )


    return records



def save_json(
    filename,
    data
):

    path = OUTPUT_DIR / filename


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


    print(
        "Saved:",
        path
    )



# ------------------------------------------------------------
# main
# ------------------------------------------------------------


def main():

    print("=" * 70)
    print("VKS Expert AI")
    print("Embedding Builder v1")
    print("=" * 70)


    ensure_dirs()


    pages = load_pages()


    print(
        "Building records..."
    )


    records = build_embedding_records(
        pages
    )


    print(
        "Chunks:",
        len(records)
    )


    save_json(
        "metadata.json",
        records
    )


    print(
        "Loading embedding model..."
    )


    model = SentenceTransformer(
        MODEL_NAME
    )


    texts = [
        r["text"]
        for r in records
    ]


    print(
        "Creating embeddings..."
    )


    embeddings = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=True,
        normalize_embeddings=True
    )


    embeddings = np.array(
        embeddings,
        dtype="float32"
    )


    np.save(
        OUTPUT_DIR / "vectors.npy",
        embeddings
    )


    dimension = embeddings.shape[1]


    print(
        "Embedding dimension:",
        dimension
    )


    print(
        "Building FAISS index..."
    )


    index = faiss.IndexFlatIP(
        dimension
    )


    index.add(
        embeddings
    )


    faiss.write_index(
        index,
        str(
            OUTPUT_DIR
            / "index.faiss"
        )
    )


    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        "Documents:",
        DOCUMENT
    )

    print(
        "Pages:",
        len(pages)
    )

    print(
        "Vectors:",
        len(records)
    )

    print(
        "Index:",
        OUTPUT_DIR / "index.faiss"
    )

    print()
    print("DONE")



if __name__ == "__main__":

    main()
