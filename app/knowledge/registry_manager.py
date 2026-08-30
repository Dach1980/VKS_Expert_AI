import json
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

    def get_current_version(self, document_id):
        document = self.get_document(document_id)
        if document is None:
            raise RegistryError(f"Документ не найден: {document_id}")
        current_versions = [
            version for version in document.get("versions", [])
            if version.get("status") == "current"
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
        effective_from=None,
        file_path=None,
        parsed_file=None,
        structured_file=None,
        make_current=True,
    ):
        """Создать документ/версию в Registry и при необходимости сделать её current."""
        if not document_id or not number or not title:
            raise RegistryError("document_id, number и title обязательны")

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
            if document.get("number") != number:
                raise RegistryError(f"Номер документа {document_id} не совпадает с существующим Registry")
            if document.get("title") != title:
                raise RegistryError(f"Название документа {document_id} не совпадает с существующим Registry")

        versions = document.setdefault("versions", [])
        if version_id is None:
            version_id = f"{document_id}_{date.today().isoformat().replace('-', '')}"
        if any(version.get("id") == version_id for version in versions):
            raise RegistryError(f"Версия уже существует: {document_id}/{version_id}")

        if make_current:
            for version in versions:
                if version.get("status") == "current":
                    version["status"] = "superseded"

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
        self.save()
        return document, version

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
            current_count = 0
            for version in versions:
                if version.get("status") == "current":
                    current_count += 1
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
            print(f"  └─ {version['id']} [{version.get('status')}]")
            print(f"     файл: {version.get('file')}")
            print(f"     действует с: {version.get('effective_from')}")


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


if __name__ == "__main__":
    main()
