"""Read-only access to uploaded normative PDFs for the local UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.knowledge.storage import KnowledgeStorage, StorageError

router = APIRouter(prefix="/api/norms", tags=["norms"])


@router.get("/{document_id}/{version_id}/pdf")
def open_norm_pdf(document_id: str, version_id: str):
    storage = KnowledgeStorage()
    try:
        version = storage.get_version(document_id, version_id)
        path = storage.resolve(version.get("file", ""))
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if not path.exists() or not path.is_file() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF версии не найден")

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=Path(path).name,
        content_disposition_type="inline",
    )
