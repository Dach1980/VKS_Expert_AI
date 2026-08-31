"""VKS Expert AI — SP Index Builder v2."""

import json
from datetime import datetime
from pathlib import Path

from app.knowledge.storage import KnowledgeStorage
from app.knowledge.pdf_page_processor import PDFPageProcessor
from app.knowledge.page_enricher import PageEnricher
from app.knowledge.structure_parser import save_structure, build_structure
from app.knowledge.document_chunk_builder import DocumentChunkBuilder
from app.knowledge.embedding_builder import EmbeddingBuilder


class SPIndexBuilder:
    def __init__(self, document_id="SP_30.13330", version_id=None, storage=None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()
        self.paths = self.storage.paths(document_id, version_id)
        self.version = self.storage.get_version(document_id, version_id)

    def check_pdf(self):
        if not self.paths.pdf.exists():
            raise FileNotFoundError(f"PDF not found: {self.paths.pdf}")
        print("PDF:", self.paths.pdf)

    def run_page_processor(self):
        PDFPageProcessor(self.document_id, self.version["id"], self.storage).run()

    def run_page_enrichment(self):
        """Create enriched pages before chunking and embedding."""
        print("Starting page enrichment...")
        enricher = PageEnricher(
            pages_dir=self.paths.pages,
            formulas_dir=self.storage.knowledge_root / "work" / "formulas",
            output_dir=self.paths.enriched,
        )
        pages = sorted(self.paths.pages.glob("page_*.json"))
        print("Pages found for enrichment:", len(pages))
        for page_file in pages:
            enricher.enrich_page(page_file)
        print("Page enrichment completed:", len(pages))

    def run_structure_parser(self):
        if not self.paths.parsed.exists():
            raise FileNotFoundError(f"Parsed JSON not found: {self.paths.parsed}")
        with self.paths.parsed.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        sections = build_structure(data)
        result, output = save_structure(data, sections, self.storage, self.document_id, self.version["id"])
        print("Structured:", output)
        return result

    def run_chunk_builder(self):
        builder = DocumentChunkBuilder(self.document_id, self.version["id"], self.storage)
        chunks = builder.process_all_pages()
        return chunks, builder.save(chunks)

    def run_embedding_builder(self):
        # Ensure the selected version's complete output tree immediately before
        # embedding. This is intentionally repeated here because indexing is
        # executed as a background task and must not depend on a directory that
        # may have been removed by a previous/parallel processing attempt.
        self.storage.ensure_version_dirs(self.document_id, self.version["id"])
        self.paths.embeddings.mkdir(parents=True, exist_ok=True)
        print("Embedding directory:", self.paths.embeddings)
        builder = EmbeddingBuilder(self.document_id, self.version["id"], self.storage)
        builder.run()

    def build_summary(self):
        paths = self.paths
        page_count = len(list(paths.pages.glob("page_*.json"))) if paths.pages.exists() else 0
        enriched_count = len(list(paths.enriched.glob("page_*_enriched.json"))) if paths.enriched.exists() else 0
        chunks_file = paths.chunks / "all_chunks.json"
        embedding_index = paths.embeddings / "index.faiss"
        return {
            "document": self.storage.get_document(self.document_id)["number"],
            "document_id": self.document_id,
            "version": self.version["id"],
            "source": {"pdf": str(paths.pdf)},
            "statistics": {
                "pages": page_count,
                "enriched_pages": enriched_count,
                "chunks": self._count_chunks(chunks_file),
                "vector_index": embedding_index.exists(),
            },
            "created": datetime.now().isoformat(),
        }

    @staticmethod
    def _count_chunks(file):
        if not file.exists():
            return 0
        with file.open("r", encoding="utf-8") as f:
            return len(json.load(f))

    def save_summary(self, summary):
        output = self.paths.chunks
        output.mkdir(parents=True, exist_ok=True)
        file = output / "index_summary.json"
        with file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print("Saved summary:", file)

    def run(self, build_pages=True, build_structure_stage=True, build_enrichment=True, build_chunks=True, build_embeddings=True):
        self.check_pdf()
        self.storage.ensure_version_dirs(self.document_id, self.version["id"])
        if build_pages:
            self.run_page_processor()
        if build_structure_stage:
            self.run_structure_parser()
        if build_enrichment:
            self.run_page_enrichment()
        if build_chunks:
            self.run_chunk_builder()
        if build_embeddings:
            self.run_embedding_builder()
        summary = self.build_summary()
        self.save_summary(summary)
        return summary


def main():
    print("=" * 70)
    print("VKS Expert AI — SP Index Builder v2")
    print("=" * 70)
    summary = SPIndexBuilder().run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("DONE")


if __name__ == "__main__":
    main()
