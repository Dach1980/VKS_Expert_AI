"""
VKS Expert AI

Retriever v1.14

Normative Formula Intent Retrieval

Features:

- FAISS semantic retrieval
- Formula context retrieval
- Normative intent detection
- Formula priority ranking
- Formula rendering
- Unified result output


Pipeline:

Query
 |
 v
Intent Detection
 |
 +----------------+
 |                |
 v                v
FAISS        Formula Search
 |
 +----------------+
 |
 v
Ranking
 |
 v
Context Expansion
 |
 v
Results


"""


from pathlib import Path
import json
import re

import faiss
import numpy as np


from app.rag.embedding_client import EmbeddingClient



# ============================================================
# CONFIG
# ============================================================


DOCUMENT = "SP_30.13330"


BASE_DIR = (
    Path("knowledge/index")
    / DOCUMENT
)


EMBEDDINGS_DIR = (
    BASE_DIR
    / "embeddings"
)


INDEX_FILE = (
    EMBEDDINGS_DIR
    / "index.faiss"
)


VECTORS_FILE = (
    EMBEDDINGS_DIR
    / "vectors.npy"
)


METADATA_FILE = (
    EMBEDDINGS_DIR
    / "metadata.json"
)



TOP_K = 10



# ============================================================
# LOAD
# ============================================================


def load_index():

    print("Loading FAISS index...")

    index = faiss.read_index(
        str(INDEX_FILE)
    )


    print(
        "Vectors loaded:",
        index.ntotal
    )


    return index



def load_metadata():

    print(
        "Loading metadata..."
    )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    print(
        "Records loaded:",
        len(data)
    )


    return data



# ============================================================
# QUERY INTENT
# ============================================================


FORMULA_KEYWORDS = [

    "формул",
    "определяется",
    "определить",
    "следует определять",
    "расчет",
    "расчетный",
    "значение",
    "коэффициент",
    "принимается",
    "вычисляется"

]



def is_formula_query(query):

    text = (
        query
        .lower()
    )


    score = 0


    for word in FORMULA_KEYWORDS:

        if word in text:

            score += 1


    return score >= 2



# ============================================================
# FORMULA HELPERS
# ============================================================


def normalize_formula(formula):

    if not formula:

        return ""


    formula = (
        formula
        .replace("\\,", " ")
        .replace("\\;", " ")
        .replace("\\cdot", "*")
        .replace("\\alpha", "α")
    )


    formula = re.sub(
        r"\s+",
        " ",
        formula
    )


    return formula.strip()



def render_formula(item):

    if (
        item.get("type")
        !=
        "formula_context"
    ):

        return ""


    content = item.get(
        "content",
        {}
    )


    formula = content.get(
        "formula",
        ""
    )


    if not formula:

        return ""


    return (

        "\n\n"
        "FORMULA:\n"
        +
        normalize_formula(formula)

    )



# ============================================================
# FORMULA SCORE
# ============================================================


def formula_score(
    query,
    item
):


    if item.get("type") != "formula_context":

        return 0


    score = 0


    text = (

        item
        .get("content", {})
        .get("text", "")

    ).lower()



    query_words = (

        query
        .lower()
        .split()

    )


    for word in query_words:

        if len(word) > 3:

            if word in text:

                score += 0.05



    if (
        "максимальный"
        in query.lower()
        and
        "максимальный"
        in text
    ):

        score += 0.25



    if (
        "расчетный"
        in query.lower()
        and
        "расчетный"
        in text
    ):

        score += 0.25



    if "формула" in query.lower():

        score += 0.2



    return min(
        score,
        0.5
    )



# ============================================================
# EMBEDDING SEARCH
# ============================================================


def search_faiss(
    query,
    index,
    metadata,
    client
):


    vector = client.embed(
        query
    )


    vector = np.array(
        [vector],
        dtype="float32"
    )


    faiss.normalize_L2(
        vector
    )


    scores, ids = index.search(
        vector,
        TOP_K
    )


    results = []


    for score, idx in zip(
        scores[0],
        ids[0]
    ):


        item = metadata[idx]


        results.append({

            "item": item,

            "score":
                float(score),

            "source":
                "faiss"

        })


    return results



# ============================================================
# FORMULA SEARCH
# ============================================================


def search_formula(
    query,
    metadata
):


    results = []


    for item in metadata:


        if (
            item.get("type")
            ==
            "formula_context"
        ):


            score = formula_score(
                query,
                item
            )


            if score > 0:

                results.append({

                    "item": item,

                    "score":
                        score,

                    "source":
                        "formula"

                })


    return results



# ============================================================
# MERGE
# ============================================================


def merge_results(
    faiss_results,
    formula_results,
    formula_mode
):


    merged = []


    for r in faiss_results:


        item = r["item"]


        bonus = 0


        if formula_mode:

            if item.get("type") == "formula_context":

                bonus = 0.30


        merged.append({

            "item":
                item,

            "source":
                r["source"],

            "score":
                r["score"]
                +
                bonus

        })



    for r in formula_results:


        merged.append({

            "item":
                r["item"],

            "source":
                "formula",

            "score":
                r["score"]
                +
                0.35

        })



    merged.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    return merged[:TOP_K]



# ============================================================
# DISPLAY
# ============================================================


def print_results(results):


    print()
    print(
        "=" * 70
    )

    print(
        "NORMATIVE FORMULA INTENT RESULTS"
    )

    print(
        "=" * 70
    )



    for i, r in enumerate(
        results,
        1
    ):

        item = r["item"]


        content = item.get(
            "content",
            {}
        )


        text = content.get(
            "text",
            ""
        )


        print()
        print(
            f"RESULT #{i}"
        )

        print(
            "-" * 70
        )


        print(
            "FINAL:",
            round(
                r["score"],
                5
            )
        )


        print(
            "SOURCE:",
            r["source"]
        )


        print(
            "PAGE:",
            item.get(
                "page"
            )
        )


        print(
            "TYPE:",
            item.get(
                "type"
            )
        )


        print()


        print(
            text
        )


        formula = render_formula(
            item
        )


        if formula:

            print(
                formula
            )



# ============================================================
# MAIN
# ============================================================


def main():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Retriever v1.14"
    )

    print("=" * 70)



    query = input(
        "\nSEARCH QUERY:\n\n"
    )



    index = load_index()


    metadata = load_metadata()



    print(
        "Initializing embedding client..."
    )


    client = EmbeddingClient()



    print(
        "Formula contexts:",
        len(
            [
                x for x in metadata
                if x.get("type")
                ==
                "formula_context"
            ]
        )
    )


    print(
        "Retriever ready"
    )



    formula_mode = is_formula_query(
        query
    )



    faiss_results = search_faiss(
        query,
        index,
        metadata,
        client
    )


    formula_results = search_formula(
        query,
        metadata
    )



    results = merge_results(
        faiss_results,
        formula_results,
        formula_mode
    )


    print_results(
        results
    )



if __name__ == "__main__":

    main()
    