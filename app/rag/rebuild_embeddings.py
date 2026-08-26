"""
VKS Expert AI
Rebuild Embeddings v1

Purpose:
Rebuild FAISS vector index using LM Studio embeddings.

Pipeline:

Chunks JSON
    |
    v
LM Studio Embedding API
    |
    v
Vectors
    |
    v
FAISS Index
    |
    v
Metadata
"""


from pathlib import Path
import json
import numpy as np
import faiss
from tqdm import tqdm


from app.rag.embedding_client import EmbeddingClient



DOCUMENT = "SP_30.13330"


BASE_DIR = Path("knowledge/index") / DOCUMENT


CHUNKS_FILE = (
    BASE_DIR
    / "document_chunks"
    / "all_chunks.json"
)


OUTPUT_DIR = (
    BASE_DIR
    / "embeddings"
)


INDEX_FILE = (
    OUTPUT_DIR
    / "index.faiss"
)


VECTORS_FILE = (
    OUTPUT_DIR
    / "vectors.npy"
)


METADATA_FILE = (
    OUTPUT_DIR
    / "metadata.json"
)



def load_chunks():

    print("Loading chunks...")

    with open(
        CHUNKS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    print(
        f"Chunks loaded: {len(data)}"
    )

    return data



def build_embeddings(chunks):

    print(
        "Loading embedding client..."
    )

    client = EmbeddingClient()


    vectors = []
    metadata = []


    print(
        "Generating embeddings..."
    )

    for index, item in enumerate(tqdm(chunks)):

        text = item.get(
            "embedding_text",
            ""
        )

        if not text:

            content = item.get(
                "content",
                {}
            )

            text = content.get(
                "text",
                ""
            )


        print()
        print("CHUNK:", index)
        print("TEXT LENGTH:", len(text))


        if not text.strip():
            print("EMPTY TEXT")
            continue


        vector = client.embed(
            text
        )


        print(
            "VECTOR TYPE:",
            type(vector)
        )


        try:
            print(
                "VECTOR LENGTH:",
                len(vector)
            )

            print(
                "VECTOR SAMPLE:",
                vector[:5]
            )

        except Exception as e:

            print(
                "VECTOR ERROR:",
                e
            )


        vectors.append(
            vector
        )


        metadata.append(
            {
                "chunk_id": item.get(
                    "chunk_id"
                ),

                "document": item.get(
                    "document",
                    DOCUMENT
                ),

                "type": item.get(
                    "type",
                    "text"
                ),

                "page": item.get(
                    "page",
                    None
                ),

                "text": text,

                "embedding_text": item.get(
                    "embedding_text",
                    ""
                )
            }
        )

    print()
    print("==============================")
    print("TOTAL VECTORS:", len(vectors))
    print("==============================")


    if len(vectors) == 0:
        raise RuntimeError(
            "Embedding list is empty"
        )

    vectors = np.array(
        vectors,
        dtype="float32"
    )


    return vectors, metadata



def build_faiss(
    vectors
):

    print(
        "Building FAISS index..."
    )


    dimension = vectors.shape[1]


    index = faiss.IndexFlatIP(
        dimension
    )


    # normalize for cosine similarity

    faiss.normalize_L2(
        vectors
    )


    index.add(
        vectors
    )


    print(
        f"Vectors added: {index.ntotal}"
    )


    return index



def save_all(
    index,
    vectors,
    metadata
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    print(
        "Saving FAISS index..."
    )


    faiss.write_index(
        index,
        str(INDEX_FILE)
    )


    print(
        "Saving vectors..."
    )


    np.save(
        VECTORS_FILE,
        vectors
    )


    print(
        "Saving metadata..."
    )


    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2
        )


    print()
    print(
        "Saved:"
    )

    print(
        INDEX_FILE
    )

    print(
        VECTORS_FILE
    )

    print(
        METADATA_FILE
    )



def main():

    print("=" * 70)
    print(
        "VKS Expert AI"
    )
    print(
        "Rebuild Embeddings v1"
    )
    print("=" * 70)


    chunks = load_chunks()


    vectors, metadata = (
        build_embeddings(
            chunks
        )
    )


    index = build_faiss(
        vectors
    )


    save_all(
        index,
        vectors,
        metadata
    )


    print()
    print(
        "Embedding rebuild complete"
    )



if __name__ == "__main__":

    main()
