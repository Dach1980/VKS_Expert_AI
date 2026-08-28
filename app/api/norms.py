"""VKS Expert AI — Norms API.

Provides the frontend with registered normative documents and their
processing status. File processing itself remains in the knowledge pipeline.
"""

from fastapi import APIRouter, HTTPException

from app.knowledge.storage import KnowledgeStorage, StorageError


router = APIRouter(prefix="/api/norms", tags=["norms"])


@router.get("")
def list_norms():
    """Список нормативных документов из RegistryManager + статус Storage."""
    storage = KnowledgeStorage()
    try:
        return {
            "documents": storage.list_statuses()
        }
    except StorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/{document_id}")
def get_norm(document_id: str):
    """Информация и статус конкретного нормативного документа."""
    storage = KnowledgeStorage()
    try:
        return storage.get_status(document_id)
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
