"""VKS Expert AI — Embedding Builder v2.

Строит embeddings и FAISS из document chunks.
Использует общий KnowledgeStorage и существующий EmbeddingClient.
"""

import json

import faiss
import numpy as np

from app.knowledge.storage import KnowledgeStorage
from app.rag.embedding_client import EmbeddingClient


class EmbeddingBuilder:
    def __init__(self, document_id="SP_30.13330", version_id=None, storage=None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.paths = self.storage.paths(document_id, version_id)

    def load_chunks(self):
        file = self.paths.chunks / "all_chunks.json"
        if not file.exists():
            raise FileNotFoundError(f"Chunks not found: {file}")
        with file.open("r", encoding="utf-8") as f:
            chunks = json.load(f)
        print("Chunks loaded:", len(chunks))
        return chunks

    def build_embeddings(self, chunks):
        client = EmbeddingClient()
        vectors = []
        metadata = []

        for index, item in enumerate(chunks, start=1):
            text = item.get("embedding_text", "")
            if not text:
                content = item.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
            if not str(text).strip():
                continue

            vector = client.embed(str(text))
            vectors.append(vector)
            metadata.append({
                "chunk_id": item["chunk_id"],
                "type": item.get("type", "text"),
                "document": item.get("document", self.document_id),
                "document_id": item.get("document_id", self.document_id),
                "version": item.get("version"),
                "page": item.get("page", 0),
                "location": item.get("location", {}),
                "content": item.get("content", {}),
                "metadata": item.get("metadata", {}),
                "embedding_text": text,
            })
            print(f"Embedded {index}/{len(chunks)}")

        if not vectors:
            raise RuntimeError("Embedding list is empty")

        return np.asarray(vectors, dtype="float32"), metadata

    def build_faiss(self, vectors):
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return index

    def save(self, index, vectors, metadata):
        output = self.paths.embeddings
        output.mkdir(parents=True, exist_ok=True)
        index_file = output / "index.faiss"
        vectors_file = output / "vectors.npy"
        metadata_file = output / "metadata.json"

        faiss.write_index(index, str(index_file))
        np.save(vectors_file, vectors)
        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print("Saved:", index_file)
        print("Saved:", vectors_file)
        print("Saved:", metadata_file)
        return index_file

    def run(self):
        chunks = self.load_chunks()
        vectors, metadata = self.build_embeddings(chunks)
        index = self.build_faiss(vectors)
        self.save(index, vectors, metadata)
        print("Vectors:", len(metadata))
        print("DONE")


def main():
    EmbeddingBuilder().run()


if __name__ == "__main__":
    main()
