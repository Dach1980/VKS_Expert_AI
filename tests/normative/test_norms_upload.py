from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.api import norms


class _FakeRegistry:
    def __init__(self):
        self.document = None

    def get_document(self, document_id):
        return self.document

    def register_version(self, **kwargs):
        if self.document is None:
            self.document = {
                "id": kwargs["document_id"],
                "number": kwargs["number"],
                "title": kwargs["title"],
                "versions": [],
            }
        version = {
            "id": kwargs["version_id"],
            "status": "uploaded",
            "current_selected_by_user": False,
            "edition": {},
            "source": {"file": kwargs["file_path"]},
            "parsed_file": kwargs["parsed_file"],
            "structured_file": kwargs["structured_file"],
            "index": {},
        }
        self.document["versions"].append(version)

    def save(self):
        pass


class _FakeStorage:
    def __init__(self):
        self.registry = _FakeRegistry()
        self.saved = None

    def save_uploaded_pdf(self, document_id, upload_file, version_id):
        self.saved = (document_id, version_id, upload_file.filename)
        document = self.registry.get_document(document_id)
        version = next(v for v in document["versions"] if v["id"] == version_id)
        version["edition"] = {
            "date": "2025-03-01",
            "amendment": {
                "number": "5",
                "effective_from": "2025-03-01",
            },
        }
        version["source"]["original_filename"] = upload_file.filename
        return Path("test-upload.pdf")

    @staticmethod
    def _pdf_pages(path):
        return 1


def test_upload_norm_does_not_depend_on_removed_filename_classifier(monkeypatch):
    storage = _FakeStorage()
    monkeypatch.setattr(norms, "KnowledgeStorage", lambda: storage)
    monkeypatch.setattr(norms, "_find_duplicate_version", lambda storage, upload_hash: None)
    monkeypatch.setattr(norms, "_sha256_uploaded", lambda upload_file: "test-sha256")

    upload = UploadFile(
        filename="СП 30.13330.2020 Изм.5 01.03.2025.pdf",
        file=BytesIO(b"%PDF-test"),
    )

    result = norms.upload_norm(upload)

    assert result.success is True
    assert result.number == "СП 30.13330.2020"
    assert result.filename == "СП 30.13330.2020 Изм.5 01.03.2025.pdf"

    version = storage.registry.document["versions"][0]
    assert version["edition"]["date"] == "2025-03-01"
    assert version["edition"]["amendment"]["number"] == "5"
    assert version["edition"]["amendment"]["effective_from"] == "2025-03-01"
    assert version["source"]["original_filename"] == result.filename
    assert version["source"]["sha256"] == "test-sha256"
