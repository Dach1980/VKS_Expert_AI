"""
VKS Expert AI

Retriever v1.3

Semantic retrieval layer.

Architecture:

Question
    |
    v
EmbeddingClient
    |
    v
LM Studio Embeddings
    |
    v
FAISS similarity search
    |
    v
Metadata filtering
    |
    v
Retrieved chunks
"""


from pathlib import Path
from typing import List, Dict


import json
import numpy as np
import faiss


from app.rag.embedding_client import EmbeddingClient



class Retriever:
    """
    FAISS based semantic retriever.
    """


    def __init__(
        self,
        index_root: str = "knowledge/index/SP_30.13330/embeddings",
    ):


        print(
            "Loading FAISS index..."
        )


        self.index_root = Path(index_root)


        self.index_path = (
            self.index_root /
            "index.faiss"
        )


        self.metadata_path = (
            self.index_root /
            "metadata.json"
        )



        self._check_files()



        print(
            "Using index:"
        )


        print(
            self.index_path.resolve()
        )



        self.index = faiss.read_index(

            str(self.index_path)

        )



        print(
            "Vectors loaded:",
            self.index.ntotal
        )



        print(
            "Loading metadata..."
        )


        with open(
            self.metadata_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.metadata = json.load(f)



        print(
            "Records loaded:",
            len(self.metadata)
        )



        print(
            "Loading embedding client..."
        )


        self.embedding_client = EmbeddingClient()



        print(
            "Retriever ready"
        )



    # ==================================================
    # CHECK FILES
    # ==================================================


    def _check_files(self):


        if not self.index_path.exists():

            raise FileNotFoundError(

                f"""
FAISS index not found:

{self.index_path}

"""

            )


        if not self.metadata_path.exists():

            raise FileNotFoundError(

                f"""
Metadata not found:

{self.metadata_path}

"""

            )



    # ==================================================
    # SEARCH
    # ==================================================


    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Semantic search.

        Args:
            query:
                User query

            top_k:
                Number of results

        Returns:
            Retrieved records
        """



        print()

        print(
            "SEARCH QUERY:"
        )

        print(
            query
        )



        # ----------------------------------------------
        # Create embedding
        # ----------------------------------------------


        vector = self.embedding_client.embed(

            query

        )



        query_vector = np.array(

            [vector],

            dtype="float32"

        )



        # ----------------------------------------------
        # Validate dimension
        # ----------------------------------------------


        if query_vector.shape[1] != self.index.d:

            raise ValueError(

                f"""
Embedding dimension mismatch.

FAISS index:
{self.index.d}

Query vector:
{query_vector.shape[1]}

"""

            )



        # ----------------------------------------------
        # Normalize
        # ----------------------------------------------


        faiss.normalize_L2(

            query_vector

        )



        # ----------------------------------------------
        # Search
        # ----------------------------------------------


        scores, ids = self.index.search(

            query_vector,

            top_k

        )



        results = []



        for score, idx in zip(
            scores[0],
            ids[0]
        ):


            if idx < 0:

                continue



            item = self.metadata[idx].copy()



            item["score"] = float(score)



            results.append(

                item

            )



        return results



    # ==================================================
    # DEBUG
    # ==================================================


    def print_results(
        self,
        results: List[Dict]
    ):


        print()

        print("=" * 70)

        print(
            "RETRIEVAL RESULTS"
        )

        print("=" * 70)



        for item in results:


            print()

            print(
                item.get(
                    "document",
                    "?"
                )
            )


            print(
                "page=",
                item.get(
                    "page",
                    "?"
                )
            )


            print(
                "score=",
                item.get(
                    "score",
                    0
                )
            )



# ======================================================
# DEMO
# ======================================================


def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Retriever v1.3"
    )

    print("=" * 70)



    retriever = Retriever()



    query = """

Как определяется максимальный
расчетный расход воды
на расчетном участке сети?

"""



    results = retriever.search(

        query,

        top_k=5

    )



    retriever.print_results(

        results

    )



if __name__ == "__main__":

    demo()
    