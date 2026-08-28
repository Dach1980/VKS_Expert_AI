"""VKS Expert AI — KnowledgeStorage v1."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.registry_manager import DocumentRegistry, RegistryError


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StorageError(Exception):
    """Ошибка работы с KnowledgeStorage."""


@dataclass(frozen=True)
class DocumentPaths:
    pdf: Path
    parsed: Path
    structured: Path
    index_root: Path
    pages: Path
    enriched: Path
    chunks: Path
    embeddings: Path


class KnowledgeStorage:
    """Единая точка доступа к путям нормативных документов."""

    def __init__(
        self,
        project_root: Path | str = PROJECT_ROOT,
        registry: DocumentRegistry | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.knowledge_root = self.project_root / "knowledge"
        self.registry = registry or DocumentRegistry(
            self.knowledge_root / "registry" / "documents.json"
        )

    def get_document(self, document_id: str) -> dict[str, Any]:
        document = self.registry.get_document(document_id)
        if document is None:
            raise StorageError(f"Документ не найден: {document_id}")
        return document

    def get_current_version(self, document_id: str) -> dict[str, Any]:
        try:
            return self.registry.get_current_version(document_id)
        except RegistryError as error:
            raise StorageError(str(error)) from error

    def resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        return path if path.is_absolute() else self.project_root / path

    def _get_version(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        document = self.get_document(document_id)
        if version_id is None:
            return self.get_current_version(document_id)

        for version in document.get("versions", []):
            if version.get("id") == version_id:
                return version

        raise StorageError(
            f"Версия {version_id!r} не найдена для {document_id}"
        )

    def paths(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> DocumentPaths:
        version = self._get_version(document_id, version_id)
        index_root = self.knowledge_root / "index" / document_id

        return DocumentPaths(
            pdf=self.resolve(version.get("file", "")),
            parsed=self.resolve(version.get("parsed_file", "")),
            structured=self.resolve(version.get("structured_file", "")),
            index_root=index_root,
            pages=index_root / "pages",
            enriched=index_root / "enriched",
            chunks=index_root / "document_chunks",
            embeddings=index_root / "embeddings",
        )

    def pdf_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).pdf

    def parsed_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).parsed

    def structured_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).structured

    def pages_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).pages

    def enriched_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).enriched

    def chunks_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).chunks

    def embeddings_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).embeddings

    def ensure_version_dirs(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> DocumentPaths:
        paths = self.paths(document_id, version_id)
        for directory in (
            paths.pages,
            paths.enriched,
            paths.chunks,
            paths.embeddings,
            paths.parsed.parent,
            paths.structured.parent,
            paths.pdf.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return paths

    def save_pdf(
        self,
        document_id: str,
        source: Path | str,
        version_id: str | None = None,
    ) -> Path:
        source_path = Path(source)
        if not source_path.exists():
            raise StorageError(f"Исходный PDF не найден: {source_path}")
        if source_path.suffix.lower() != ".pdf":
            raise StorageError("KnowledgeStorage принимает только PDF")

        paths = self.ensure_version_dirs(document_id, version_id)
        shutil.copy2(source_path, paths.pdf)
        return paths.pdf

    def get_status(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        document = self.get_document(document_id)
        version = self._get_version(document_id, version_id)
        paths = self.paths(document_id, version.get("id"))

        page_files = list(paths.pages.glob("page_*.json")) if paths.pages.exists() else []
        enriched_files = (
            list(paths.enriched.glob("page_*_enriched.json"))
            if paths.enriched.exists()
            else []
        )

        chunks_file = paths.chunks / "all_chunks.json"
        embeddings_file = paths.embeddings / "index.faiss"
        metadata_file = paths.embeddings / "metadata.json"

        return {
            "document_id": document_id,
            "number": document.get("number"),
            "title": document.get("title"),
            "version_id": version.get("id"),
            "version_type": version.get("type"),
            "status": version.get("status"),
            "effective_from": version.get("effective_from"),
            "paths": {
                "pdf": str(paths.pdf),
                "parsed": str(paths.parsed),
                "structured": str(paths.structured),
                "pages": str(paths.pages),
                "enriched": str(paths.enriched),
                "chunks": str(paths.chunks),
                "embeddings": str(paths.embeddings),
            },
            "processing": {
                "uploaded": paths.pdf.exists(),
                "parsed": paths.parsed.exists(),
                "structured": paths.structured.exists(),
                "pages_indexed": bool(page_files),
                "pages_count": len(page_files),
                "enriched": bool(enriched_files),
                "enriched_pages_count": len(enriched_files),
                "chunks": chunks_file.exists(),
                "vector_index": embeddings_file.exists(),
                "vector_metadata": metadata_file.exists(),
            },
            "checked_at": datetime.now().isoformat(),
        }

    def list_statuses(self) -> list[dict[str, Any]]:
        return [
            self.get_status(document["id"])
            for document in self.registry.get_all_documents()
        ]
