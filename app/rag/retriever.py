"""
VKS Expert AI
Retriever v1

Purpose:
Semantic search over FAISS knowledge index.

Pipeline:

Query
  ↓
Embedding model
  ↓
FAISS similarity search
  ↓
Metadata lookup
  ↓
Context blocks
"""


import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[2]


INDEX_DIR = (
    BASE_DIR
    / "knowledge"
    / "index"
    / "SP_30.13330"
    / "embeddings"
)


FAISS_INDEX = INDEX_DIR / "index.faiss"
METADATA_FILE = INDEX_DIR / "metadata.json"


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-mpnet-base-v2"
)


class Retriever:
    """
    FAISS based semantic retriever.
    """

    def __init__(
        self,
        index_path=FAISS_INDEX,
        metadata_path=METADATA_FILE,
        model_name=MODEL_NAME,
    ):

        print("Loading FAISS index...")

        self.index = faiss.read_index(
            str(index_path)
        )

        print(
            f"Vectors loaded: {self.index.ntotal}"
        )


        print("Loading metadata...")

        with open(
            metadata_path,
            "r",
            encoding="utf8"
        ) as f:
            self.metadata = json.load(f)


        print(
            f"Records loaded: {len(self.metadata)}"
        )


        print(
            "Loading embedding model..."
        )

        self.model = SentenceTransformer(
            model_name
        )


        print("Ready")


    def search(
        self,
        query: str,
        top_k: int = 5,
    ):
        """
        Semantic search.
        """

        vector = self.model.encode(
            [query],
            normalize_embeddings=True
        )


        scores, ids = self.index.search(
            vector,
            top_k
        )


        results = []


        for score, idx in zip(
            scores[0],
            ids[0]
        ):

            if idx < 0:
                continue


            item = self.metadata[idx]

            results.append(
                {
                    "score": float(score),
                    "page": item.get(
                        "page"
                    ),
                    "text": item.get(
                        "text"
                    ),
                    "document": item.get(
                        "document"
                    )
                }
            )


        return results



def main():

    print("=" * 70)
    print(
        "VKS Expert AI\nRetriever v1"
    )
    print("=" * 70)


    retriever = Retriever()


    query = input(
        "\nQuery: "
    )


    results = retriever.search(
        query,
        top_k=5
    )


    print("\n")
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)


    for r in results:

        print()
        print(
            f"PAGE: {r['page']}"
        )

        print(
            f"SCORE: {r['score']:.4f}"
        )

        print(
            r["text"][:1000]
        )



if __name__ == "__main__":
    main()
    