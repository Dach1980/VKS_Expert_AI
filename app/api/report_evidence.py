"""Evidence image delivery for document check reports."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.documents import DOCUMENTS_ROOT

router = APIRouter(prefix="/api/reports/evidence", tags=["reports"])


@router.get("/{document_id}/{filename:path}")
def evidence_image(document_id: str, filename: str):
    root = (DOCUMENTS_ROOT / document_id / "checking" / "first_pass" / "annotated").resolve()
    requested = (root / filename).resolve()
    if root not in requested.parents or not requested.exists() or not requested.is_file() or requested.suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="Evidence image not found")
    return FileResponse(requested, media_type="image/png")
