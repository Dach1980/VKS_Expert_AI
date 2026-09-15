"""Project Expert AI — Embedding Builder v3.

Строит embeddings и FAISS из document chunks.
Метаданные индекса содержат полную canonical identity нормативной версии.
"""

import json
import shutil

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
        self.document = self.storage.get_document(document_id)
        self.version = self.storage.get_version(document_id, version_id)
        self.version_metadata = self.storage.get_version_metadata(document_id, self.version["id"])

    def load_chunks(self):
        file = self.paths.chunks / "all_chunks.json"
        if not file.exists():
            raise FileNotFoundError(f"Chunks not found: {file}")
        with file.open("r", encoding="utf-8") as f:
            chunks = json.load(f)
        print("Chunks loaded:", len(chunks))
        return chunks

    def _normative_metadata(self):
        return {
            "document": {
                "id": self.document_id,
                "number": self.document.get("number"),
                "title": self.document.get("title"),
                "document_type": self.document.get("document_type"),
            },
            "version": {
                "id": self.version.get("id"),
                "edition": self.version_metadata.get("edition", {}),
            },
            "source": self.version_metadata.get("source", {}),
        }

    def build_embeddings(self, chunks):
        client = EmbeddingClient()
        vectors = []
        metadata = []
        normative = self._normative_metadata()

        for index, item in enumerate(chunks, start=1):
            text = item.get("embedding_text", "")
            if not text:
                content = item.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
            if not str(text).strip():
                continue

            vector = client.embed(str(text))
            vectors.append(vector)
            item_metadata = item.get("metadata", {})
            metadata.append({
                "chunk_id": item["chunk_id"],
                "type": item.get("type", "text"),
                "document": item.get("document", self.document_id),
                "document_id": item.get("document_id", self.document_id),
                "version": item.get("version", self.version.get("id")),
                "page": item.get("page", 0),
                "location": item.get("location", {}),
                "content": item.get("content", {}),
                "metadata": item_metadata,
                "normative": normative,
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

        # FAISS on Windows may fail when its native writer receives a path
        # containing Cyrillic characters. Document IDs and version IDs are
        # allowed to contain Cyrillic, so write the FAISS file through an
        # ASCII-only temporary path and then move it using Python.
        temp_index_file = self.storage.project_root / ".faiss_index_tmp"
        temp_index_file.unlink(missing_ok=True)
        try:
            faiss.write_index(index, str(temp_index_file))
            shutil.move(str(temp_index_file), str(index_file))
        finally:
            temp_index_file.unlink(missing_ok=True)

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
