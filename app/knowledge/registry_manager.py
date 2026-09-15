import json
import re
from datetime import date
from pathlib import Path

from app.knowledge.filename_parser import FilenameParseError, parse_normative_filename

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FILE = PROJECT_ROOT / "knowledge" / "registry" / "documents.json"


class RegistryError(Exception):
    """Ошибка работы с реестром нормативных документов."""


class DocumentRegistry:
    """Registry with one canonical version model for all normative documents."""

    def __init__(self, registry_file: Path = REGISTRY_FILE):
        self.registry_file = registry_file
        self.data = self._load()

    def _load(self):
        if not self.registry_file.exists():
            raise RegistryError(f"Файл реестра не найден:\n{self.registry_file}")
        try:
            with open(self.registry_file, "r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise RegistryError(f"Ошибка JSON в файле реестра:\n{error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("documents", []), list):
            raise RegistryError("Некорректная структура Registry: documents должен быть списком")
        return data

    def save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.registry_file.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)
        temp.replace(self.registry_file)

    def get_all_documents(self):
        return self.data.get("documents", [])

    def get_document(self, document_id):
        return next((d for d in self.get_all_documents() if d.get("id") == document_id), None)

    @staticmethod
    def canonical_number(value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def _number_group(value):
        return DocumentRegistry.canonical_number(value).lower()

    @staticmethod
    def _edition_from_filename(file_path):
        try:
            parsed = parse_normative_filename(Path(file_path).name)
        except FilenameParseError:
            return {}
        edition = {}
        if parsed.effective_date:
            edition["date"] = parsed.effective_date
        if parsed.amendment_number:
            edition["amendment"] = {
                "number": parsed.amendment_number,
                "effective_from": parsed.effective_date,
            }
        return edition

    def get_current_version(self, document_id):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        current_versions = [
            version for version in document.get("versions", [])
            if version.get("status") == "current" and version.get("current_selected_by_user") is True
        ]
        if not current_versions:
            raise RegistryError(f"Для документа {document_id} не найдена действующая версия.")
        if len(current_versions) > 1:
            raise RegistryError(f"Для документа {document_id} найдено несколько действующих версий.")
        return current_versions[0]

    def register_version(
        self,
        document_id,
        number,
        title,
        document_type="СП",
        version_id=None,
        version_type="edition",
        file_path=None,
        parsed_file=None,
        structured_file=None,
        make_current=False,
        edition_date=None,
        amendment_number=None,
        amendment_effective_from=None,
        pages_count=None,
        sha256=None,
        index=None,
    ):
        if not document_id or not number or not title:
            raise RegistryError("document_id, number и title обязательны")

        number = self.canonical_number(number)
        document = self.get_document(document_id)
        if document is None:
            document = {
                "id": document_id,
                "number": number,
                "title": title,
                "document_type": document_type,
                "versions": [],
            }
            self.data.setdefault("documents", []).append(document)
        else:
            existing_number = self.canonical_number(document.get("number"))
            if existing_number and existing_number != number and self._number_group(existing_number) != self._number_group(number):
                raise RegistryError(f"Номер документа {document_id} не совпадает с существующим Registry")
            document["number"] = number
            document["title"] = title
            if document_type:
                document["document_type"] = document_type

        parsed_filename = None
        if file_path:
            try:
                parsed_filename = parse_normative_filename(Path(file_path).name)
            except FilenameParseError:
                parsed_filename = None

        if parsed_filename:
            if not version_id:
                version_id = parsed_filename.version_id
            if edition_date is None:
                edition_date = parsed_filename.effective_date
            if amendment_number is None:
                amendment_number = parsed_filename.amendment_number
            if amendment_effective_from is None and amendment_number is not None:
                amendment_effective_from = parsed_filename.effective_date

        if version_id is None:
            version_id = f"{document_id}_{date.today().isoformat().replace('-', '')}"

        versions = document.setdefault("versions", [])
        if any(version.get("id") == version_id for version in versions):
            raise RegistryError(f"Версия уже существует: {document_id}/{version_id}")

        edition = {}
        if edition_date:
            edition["date"] = str(edition_date)
        if amendment_number is not None:
            amendment = {"number": str(amendment_number)}
            if amendment_effective_from:
                amendment["effective_from"] = str(amendment_effective_from)
            edition["amendment"] = amendment

        version = {
            "id": version_id,
            "status": "uploaded",
            "current_selected_by_user": False,
            "edition": edition,
            "source": {"file": file_path},
            "parsed_file": parsed_file,
            "structured_file": structured_file,
            "index": index or {},
        }
        if pages_count is not None:
            version["index"]["pages_count"] = int(pages_count)
        if sha256:
            version["source"]["sha256"] = str(sha256)
        if parsed_filename:
            version["source"]["original_filename"] = parsed_filename.original_filename

        versions.append(version)
        if make_current:
            self._activate_in_document(document, version)
        self.save()
        return document, version

    def set_document_metadata(self, document_id, number=None, title=None):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        if number:
            number = self.canonical_number(number)
            if self._number_group(document.get("number")) != self._number_group(number):
                raise RegistryError("Канонический номер относится к другому нормативному документу")
            document["number"] = number
        if title:
            document["title"] = title
        self.save()
        return document

    @staticmethod
    def _activate_in_document(document, target):
        for version in document.get("versions", []):
            version["status"] = "current" if version is target else "superseded"
            version["current_selected_by_user"] = version is target

    def activate_version(self, document_id, version_id):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        target = next((v for v in document.get("versions", []) if v.get("id") == version_id), None)
        if target is None:
            raise RegistryError(f"Версия не найдена: {document_id}/{version_id}")
        self._activate_in_document(document, target)
        self.save()
        return target

    def delete_version(self, document_id, version_id):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        versions = document.get("versions", [])
        target = next((v for v in versions if v.get("id") == version_id), None)
        if target is None:
            raise RegistryError(f"Версия не найдена: {document_id}/{version_id}")
        was_current = target.get("status") == "current" and target.get("current_selected_by_user") is True
        versions.remove(target)
        document_removed = False
        if not versions:
            self.data["documents"] = [item for item in self.get_all_documents() if item.get("id") != document_id]
            document_removed = True
        elif was_current:
            for version in versions:
                version["status"] = "superseded"
                version["current_selected_by_user"] = False
        self.save()
        return target, document_removed

    def list_current_documents(self):
        result = []
        for document in self.get_all_documents():
            try:
                current = self.get_current_version(document["id"])
                result.append({
                    "id": document["id"],
                    "number": document["number"],
                    "title": document["title"],
                    "document_type": document["document_type"],
                    "version": current,
                })
            except RegistryError:
                continue
        return result

    def validate(self):
        errors = []
        documents = self.get_all_documents()
        document_ids = set()
        for document in documents:
            document_id = document.get("id")
            if not document_id:
                errors.append("Обнаружен документ без id.")
                continue
            if document_id in document_ids:
                errors.append(f"Дублирующийся id документа: {document_id}")
            document_ids.add(document_id)
            for key in ("number", "title", "document_type"):
                if not document.get(key):
                    errors.append(f"{document_id}: отсутствует {key}.")
            versions = document.get("versions", [])
            if not isinstance(versions, list):
                errors.append(f"{document_id}: versions должен быть списком.")
                continue
            current_count = sum(
                1 for version in versions
                if version.get("status") == "current" and version.get("current_selected_by_user") is True
            )
            if current_count > 1:
                errors.append(f"{document_id}: несколько действующих версий.")
            for version in versions:
                if not version.get("id"):
                    errors.append(f"{document_id}: версия без id.")
                edition = version.get("edition")
                if not isinstance(edition, dict):
                    errors.append(f"{document_id}/{version.get('id')}: edition должен быть объектом.")
                elif edition.get("date"):
                    try:
                        date.fromisoformat(str(edition["date"]))
                    except ValueError:
                        errors.append(f"{document_id}: некорректная edition.date: {edition['date']}")
                source = version.get("source")
                if not isinstance(source, dict) or not source.get("file"):
                    errors.append(f"{document_id}/{version.get('id')}: отсутствует source.file.")
                elif not (PROJECT_ROOT / source["file"]).exists():
                    errors.append(f"{document_id}: файл не найден:\n  {source['file']}")
        return errors


def print_registry(registry):
    print("=" * 60)
    print("Project Expert AI — Regulatory Registry")
    print("=" * 60)
    print(f"\nФайл реестра:\n{registry.registry_file}\n")
    for document in registry.get_all_documents():
        print(f"{document['number']} — {document['title']}")
        print(f"  ID: {document['id']}")
        for version in document.get("versions", []):
            edition = version.get("edition") or {}
            amendment = edition.get("amendment") or {}
            print(
                f"  └─ {version['id']} [{version.get('status')}]\n"
                f"     файл: {(version.get('source') or {}).get('file')}\n"
                f"     редакция: {edition.get('date') or '—'}\n"
                f"     изменение: {amendment.get('number') or '—'}\n"
                f"     действует с: {amendment.get('effective_from') or edition.get('date') or '—'}"
            )


def main():
    try:
        registry = DocumentRegistry()
        errors = registry.validate()
        print_registry(registry)
        print("\nПРОВЕРКА РЕЕСТРА\n" + "-" * 60)
        if errors:
            print("НАЙДЕНЫ ОШИБКИ:")
            for error in errors:
                print(f"  ✗ {error}")
            raise SystemExit(1)
        print("✓ Реестр корректен.")
    except RegistryError as error:
        print(f"ОШИБКА: {error}")
        raise SystemExit(1)
