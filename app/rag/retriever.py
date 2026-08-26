"""
VKS Expert AI

Retriever v1.7

Hybrid RAG Retriever

Pipeline:

Query
 |
Embedding
 |
FAISS search
 |
Candidate reranking
 |
Hybrid score
 |
Results


Ranking:

FAISS similarity       65%
Keyword matching       20%
Formula boost          10%
Section boost           5%

"""


from pathlib import Path
import json
import numpy as np
import faiss


from app.rag.embedding_client import EmbeddingClient



# ============================================================
# CONFIG
# ============================================================


DOCUMENT = "SP_30.13330"


BASE_DIR = (
    Path("knowledge/index")
    /
    DOCUMENT
)


INDEX_FILE = (
    BASE_DIR
    /
    "embeddings"
    /
    "index.faiss"
)


VECTORS_FILE = (
    BASE_DIR
    /
    "embeddings"
    /
    "vectors.npy"
)


METADATA_FILE = (
    BASE_DIR
    /
    "embeddings"
    /
    "metadata.json"
)



TOP_K_FAISS = 50

TOP_K_RESULT = 10



# ============================================================
# QUERY BOOST
# ============================================================


KEYWORDS = [

    "максимальный расчетный расход",

    "расчетный расход воды",

    "расчетном участке сети",

    "следует определять по формуле",

    "определять по формуле",

    "формуле"

]



SECTION_HINTS = [

    "5.3",

    "определение расчетных расходов воды",

    "максимальный расчетный расход воды"

]



# ============================================================
# RETRIEVER
# ============================================================


class HybridRetriever:


    def __init__(self):

        print(
            "Loading FAISS index..."
        )


        self.index = faiss.read_index(
            str(INDEX_FILE)
        )


        print(
            "Using index:"
        )

        print(
            INDEX_FILE
        )


        print(
            "Vectors loaded:",
            self.index.ntotal
        )



        print(
            "Loading metadata..."
        )


        with open(
            METADATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            self.metadata = json.load(f)



        print(
            "Records loaded:",
            len(self.metadata)
        )



        print(
            "Initializing embedding client..."
        )


        self.client = EmbeddingClient()



        print(
            "Retriever ready"
        )



    # --------------------------------------------------------


    def normalize(
        self,
        value
    ):


        if value < 0:

            return 0


        if value > 1:

            return 1


        return value



    # --------------------------------------------------------


    def keyword_score(
        self,
        query,
        item
    ):


        text = (

            item.get(
                "embedding_text",
                ""
            )
            +
            " "
            +
            json.dumps(
                item.get(
                    "content",
                    {}
                ),
                ensure_ascii=False
            )

        ).lower()



        score = 0



        for word in KEYWORDS:

            if word.lower() in query.lower():

                if word.lower() in text:

                    score += 0.05



        return self.normalize(
            score
        )



    # --------------------------------------------------------


    def formula_boost(
        self,
        item
    ):


        if item.get(
            "type"
        ) == "formula":

            return 1.0


        return 0



    # --------------------------------------------------------


    def section_boost(
        self,
        item
    ):


        text = (

            item.get(
                "embedding_text",
                ""
            )
            +
            json.dumps(
                item.get(
                    "content",
                    {}
                ),
                ensure_ascii=False
            )

        ).lower()



        score = 0



        for hint in SECTION_HINTS:


            if hint.lower() in text:

                score += 0.3



        return self.normalize(
            score
        )



    # --------------------------------------------------------


    def hybrid_score(
        self,
        query,
        faiss_score,
        item
    ):


        score = (

            faiss_score * 0.65

            +

            self.keyword_score(
                query,
                item
            )
            *
            0.20


            +

            self.formula_boost(
                item
            )
            *
            0.10


            +

            self.section_boost(
                item
            )
            *
            0.05

        )


        return score



    # --------------------------------------------------------


    def search(
        self,
        query
    ):


        print()
        print(
            "SEARCH QUERY:"
        )

        print(query)



        vector = self.client.embed(
            query
        )


        vector = np.array(
            [
                vector
            ],
            dtype="float32"
        )



        faiss.normalize_L2(
            vector
        )



        scores, ids = self.index.search(

            vector,

            TOP_K_FAISS

        )



        candidates = []



        for score, idx in zip(
            scores[0],
            ids[0]
        ):


            if idx < 0:

                continue



            item = self.metadata[idx]



            final = self.hybrid_score(

                query,

                float(score),

                item

            )



            candidates.append(

                {

                    "final_score":
                        final,


                    "faiss_score":
                        float(score),


                    "index":
                        int(idx),


                    **item

                }

            )



        candidates.sort(

            key=lambda x:
                x["final_score"],

            reverse=True

        )



        return candidates[
            :TOP_K_RESULT
        ]



# ============================================================
# TEST
# ============================================================


def main():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Retriever v1.7"
    )

    print("=" * 70)



    retriever = HybridRetriever()



    query = """

Как определяется максимальный
расчетный расход воды
на расчетном участке сети?

"""



    results = retriever.search(
        query
    )



    print()

    print(
        "HYBRID RESULTS"
    )

    print("=" * 70)



    for i, item in enumerate(
        results,
        start=1
    ):


        print()

        print(
            f"RESULT #{i}"
        )

        print(
            "-" * 70
        )


        print(
            "Final:",
            round(
                item["final_score"],
                5
            )
        )


        print(
            "FAISS:",
            round(
                item["faiss_score"],
                5
            )
        )


        print(
            "Index:",
            item["index"]
        )


        print(
            "Page:",
            item["page"]
        )


        print(
            "Type:",
            item["type"]
        )


        print(
            "Chunk:",
            item["chunk_id"]
        )


        print()

        content = item.get(
            "content",
            {}
        )


        if isinstance(
            content,
            dict
        ):


            print(
                content.get(
                    "text",
                    ""
                )
            )

        else:

            print(
                content
            )



if __name__ == "__main__":

    main()
    