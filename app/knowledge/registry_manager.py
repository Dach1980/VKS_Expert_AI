import json
import re
from pathlib import Path
from datetime import date


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FILE = PROJECT_ROOT / "knowledge" / "registry" / "documents.json"


class RegistryError(Exception):
    """Ошибка работы с реестром нормативных документов."""
    pass


class DocumentRegistry:
    def __init__(self, registry_file: Path = REGISTRY_FILE):
        self.registry_file = registry_file
        self.data = self._load()

    def _load(self):
        if not self.registry_file.exists():
            raise RegistryError(f"Файл реестра не найден:\n{self.registry_file}")
        try:
            with open(self.registry_file, "r", encoding="utf-8-sig") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise RegistryError(f"Ошибка JSON в файле реестра:\n{error}") from error

    def save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)

    def get_all_documents(self):
        return self.data.get("documents", [])

    def get_document(self, document_id):
        for document in self.get_all_documents():
            if document["id"] == document_id:
                return document
        return None

    @staticmethod
    def _number_group(value):
        normalized = re.sub(r"\s+", " ", str(value or "")).strip().lower()
        match = re.search(r"(?:сп|гост\s*р?|снип|тр|фз)\s*[0-9]+\.[0-9]+", normalized, re.IGNORECASE)
        return re.sub(r"\s+", " ", match.group(0)).strip() if match else normalized

    def get_current_version(self, document_id):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        current_versions = [version for version in document.get("versions", []) if version.get("status") == "current"]
        if not current_versions:
            raise RegistryError(f"Для документа {document_id} не найдена действующая версия.")
        if len(current_versions) > 1:
            raise RegistryError(f"Для документа {document_id} найдено несколько действующих версий.")
        return current_versions[0]

    def register_version(self, document_id, number, title, document_type="СП", version_id=None,
                         version_type="edition", effective_from=None, file_path=None,
                         parsed_file=None, structured_file=None, make_current=True):
        """Создать документ/версию в Registry.

        Старые записи вроде «СП 30.13330» допускают каноническое уточнение
        до «СП 30.13330.2020», если это тот же логический документ.
        """
        if not document_id or not number or not title:
            raise RegistryError("document_id, number и title обязательны")

        document = self.get_document(document_id)
        if document is None:
            document = {"id": document_id, "number": number, "title": title,
                        "document_type": document_type, "versions": []}
            self.data.setdefault("documents", []).append(document)
        else:
            existing_number = document.get("number") or ""
            if existing_number != number:
                if self._number_group(existing_number) == self._number_group(number):
                    # Full number is authoritative when it contains the year/version.
                    if len(str(number)) >= len(str(existing_number)):
                        document["number"] = number
                    else:
                        number = existing_number
                else:
                    raise RegistryError(f"Номер документа {document_id} не совпадает с существующим Registry")
            existing_title = document.get("title") or ""
            if existing_title != title:
                # Prefer the more descriptive title discovered from the normative PDF.
                if len(str(title)) >= len(str(existing_title)):
                    document["title"] = title
                else:
                    title = existing_title

        versions = document.setdefault("versions", [])
        if version_id is None:
            version_id = f"{document_id}_{date.today().isoformat().replace('-', '')}"
        if any(version.get("id") == version_id for version in versions):
            raise RegistryError(f"Версия уже существует: {document_id}/{version_id}")

        version = {
            "id": version_id,
            "type": version_type,
            "status": "current" if make_current else "uploaded",
            "effective_from": effective_from,
            "file": file_path,
            "parsed_file": parsed_file,
            "structured_file": structured_file,
        }
        versions.append(version)
        if make_current:
            for other in versions:
                if other is not version and other.get("status") == "current":
                    other["status"] = "superseded"
        self.save()
        return document, version

    def activate_version(self, document_id, version_id):
        """Сделать существующую версию единственной действующей версией."""
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        target = next((version for version in document.get("versions", []) if version.get("id") == version_id), None)
        if target is None:
            raise RegistryError(f"Версия не найдена: {document_id}/{version_id}")
        for version in document.get("versions", []):
            version["status"] = "current" if version is target else "superseded"
        self.save()
        return target

    def delete_version(self, document_id, version_id):
        """Удалить версию; при необходимости назначить самой новой оставшуюся."""
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        versions = document.get("versions", [])
        target = next((v for v in versions if v.get("id") == version_id), None)
        if target is None:
            raise RegistryError(f"Версия не найдена: {document_id}/{version_id}")
        was_current = target.get("status") == "current"
        versions.remove(target)
        document_removed = False
        if not versions:
            self.data["documents"] = [item for item in self.get_all_documents() if item.get("id") != document_id]
            document_removed = True
        elif was_current:
            fallback = max(versions, key=lambda version: version.get("effective_from") or "")
            for version in versions:
                version["status"] = "current" if version is fallback else "superseded"
        self.save()
        return target, document_removed

    def list_current_documents(self):
        result = []
        for document in self.get_all_documents():
            try:
                current = self.get_current_version(document["id"])
                result.append({"id": document["id"], "number": document["number"], "title": document["title"],
                               "document_type": document["document_type"], "version": current})
            except RegistryError:
                continue
        return result

    def validate(self):
        errors = []
        documents = self.get_all_documents()
        if not isinstance(documents, list):
            return ["Поле 'documents' должно быть списком."]
        document_ids = set()
        for document in documents:
            document_id = document.get("id")
            if not document_id:
                errors.append("Обнаружен документ без id.")
                continue
            if document_id in document_ids:
                errors.append(f"Дублирующийся id документа: {document_id}")
            document_ids.add(document_id)
            if not document.get("number"):
                errors.append(f"{document_id}: отсутствует number.")
            if not document.get("title"):
                errors.append(f"{document_id}: отсутствует title.")
            versions = document.get("versions", [])
            if not isinstance(versions, list):
                errors.append(f"{document_id}: versions должен быть списком.")
                continue
            current_count = sum(1 for version in versions if version.get("status") == "current")
            for version in versions:
                file_path = version.get("file")
                if file_path and not (PROJECT_ROOT / file_path).exists():
                    errors.append(f"{document_id}: файл не найден:\n  {file_path}")
                effective_from = version.get("effective_from")
                if effective_from:
                    try:
                        date.fromisoformat(effective_from)
                    except ValueError:
                        errors.append(f"{document_id}: некорректная дата effective_from: {effective_from}")
            if current_count == 0:
                errors.append(f"{document_id}: нет действующей версии.")
            elif current_count > 1:
                errors.append(f"{document_id}: несколько действующих версий.")
        return errors


def print_registry(registry):
    print("=" * 60)
    print("VKS Expert AI — Regulatory Registry")
    print("=" * 60)
    print(f"\nФайл реестра:\n{registry.registry_file}\n")
    documents = registry.get_all_documents()
    if not documents:
        print("Реестр пуст.")
        return
    for document in documents:
        print(f"{document['number']} — {document['title']}")
        print(f"  ID: {document['id']}")
        for version in document.get("versions", []):
            print(f"  └─ {version['id']} [{version.get('status')}]\n     файл: {version.get('file')}\n     действует с: {version.get('effective_from')}")


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
