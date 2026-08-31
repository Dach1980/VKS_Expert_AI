"""Project Expert AI — Project Documentation API v1.

Upload and process project PDFs using the existing PDFPageProcessor.
The module deliberately does not create a second PDF parsing pipeline.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.knowledge.pdf_page_processor import PDFPageProcessor


router = APIRouter(prefix="/api/documents", tags=["documents"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_ROOT = PROJECT_ROOT / "knowledge" / "project_documents"
REGISTRY_FILE = DOCUMENTS_ROOT / "documents.json"
REGISTRY_LOCK = Lock()


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", value).strip("._-")
    return value or "document"


def _read_registry() -> list[dict]:
    DOCUMENTS_ROOT.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        return []
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _write_registry(items: list[dict]) -> None:
    DOCUMENTS_ROOT.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _status(item: dict) -> dict:
    root = Path(item["root"])
    pages = root / "pages"
    parsed = root / "parsed.json"
    return {
        **item,
        "processing": {
            "uploaded": (root / "source.pdf").exists(),
            "parsed": parsed.exists(),
            "pages_indexed": pages.exists() and any(pages.glob("page_*.json")),
            "pages_count": len(list(pages.glob("page_*.json"))) if pages.exists() else 0,
            "error": item.get("error"),
        },
    }


def _process_document(document_id: str) -> None:
    with REGISTRY_LOCK:
        items = _read_registry()
        item = next((x for x in items if x["id"] == document_id), None)
    if item is None:
        return

    root = Path(item["root"])
    try:
        pages = root / "pages"
        parsed = root / "parsed.json"
        processor = PDFPageProcessor(
            document_id=document_id,
            pdf_path=root / "source.pdf",
            output_dir=pages,
            parsed_path=parsed,
            document_meta={
                "number": item["name"],
                "title": item["name"],
                "version_id": item["id"],
            },
        )
        result = processor.run()
        with REGISTRY_LOCK:
            items = _read_registry()
            current = next((x for x in items if x["id"] == document_id), None)
            if current:
                current["status"] = "processed"
                current["pages"] = len(result)
                current["error"] = None
                current["processed_at"] = datetime.now().isoformat()
                _write_registry(items)
    except Exception as error:
        with REGISTRY_LOCK:
            items = _read_registry()
            current = next((x for x in items if x["id"] == document_id), None)
            if current:
                current["status"] = "error"
                current["error"] = str(error)
                current["processed_at"] = datetime.now().isoformat()
                _write_registry(items)
        print(f"[Project Expert AI][Documents] Processing error: {document_id}: {error}")


@router.get("")
def list_documents():
    with REGISTRY_LOCK:
        return {"documents": [_status(x) for x in _read_registry()]}


@router.post("/upload")
def upload_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Для проектной документации поддерживается только PDF")

    document_id = uuid.uuid4().hex
    name = Path(filename).stem
    root = DOCUMENTS_ROOT / document_id
    root.mkdir(parents=True, exist_ok=True)
    source = root / "source.pdf"

    try:
        file.file.seek(0)
        with source.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)
    except OSError as error:
        shutil.rmtree(root, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить PDF: {error}") from error

    item = {
        "id": document_id,
        "name": name,
        "filename": filename,
        "root": str(root),
        "status": "processing",
        "pages": 0,
        "created_at": datetime.now().isoformat(),
        "processed_at": None,
        "error": None,
    }
    with REGISTRY_LOCK:
        items = _read_registry()
        items.append(item)
        _write_registry(items)

    (background_tasks or BackgroundTasks()).add_task(_process_document, document_id)
    return {"success": True, **_status(item)}


@router.get("/{document_id}")
def get_document(document_id: str):
    with REGISTRY_LOCK:
        item = next((x for x in _read_registry() if x["id"] == document_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _status(item)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    with REGISTRY_LOCK:
        items = _read_registry()
        item = next((x for x in items if x["id"] == document_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="Документ не найден")
        items = [x for x in items if x["id"] != document_id]
        _write_registry(items)
    shutil.rmtree(Path(item["root"]), ignore_errors=True)
    return {"success": True, "document_id": document_id}
