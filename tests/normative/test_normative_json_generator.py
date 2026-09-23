import json

from app.knowledge.normative.generator import NormativeJSONGenerator
from app.knowledge.storage import KnowledgeStorage
from app.knowledge.registry_manager import DocumentRegistry


def test_generator_builds_valid_normative_json_2_0(tmp_path):
    knowledge = tmp_path / "knowledge"
    registry_path = knowledge / "registry" / "documents.json"
    parsed_path = knowledge / "parsed" / "SP_30_test.json"
    structured_path = knowledge / "structured" / "SP_30_test.json"
    pdf_path = knowledge / "regulations" / "SP_30" / "SP_30_test.pdf"

    registry_path.parent.mkdir(parents=True)
    parsed_path.parent.mkdir(parents=True)
    pdf_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "SP_30",
                        "number": "СП 30.13330.2020",
                        "title": "Внутренний водопровод и канализация зданий",
                        "document_type": "СП",
                        "versions": [
                            {
                                "id": "SP_30_test",
                                "status": "uploaded",
                                "source": {
                                    "file": "knowledge/regulations/SP_30/SP_30_test.pdf",
                                    "original_filename": "СП_30.13330.2020.pdf",
                                    "pages": 1,
                                },
                                "parsed_file": "knowledge/parsed/SP_30_test.json",
                                "structured_file": "knowledge/structured/SP_30_test.json",
                                "edition": {
                                    "date": "2020-06-01"
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    parsed_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "document": {
                    "number": "СП 30.13330.2020",
                    "title": "Внутренний водопровод и канализация зданий",
                    "pages": 1,
                },
                "pages": [
                    {
                        "page": 1,
                        "geometry": {"width": 1000, "height": 1400},
                        "blocks": [
                            {"bbox": [10, 10, 500, 40], "text": "1 Область применения"},
                            {"bbox": [10, 50, 900, 100], "text": "1.1 Настоящий свод правил должен применяться при проектировании зданий."},
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    storage = KnowledgeStorage(project_root=tmp_path)
    document, result = NormativeJSONGenerator("SP_30", "SP_30_test", storage).generate()

    assert result.valid is True
    assert document["schema_version"] == "2.0"
    assert document["structure"]["sections"][0]["clauses"][0]["number"] == "1.1"
    assert document["requirements"][0]["clause_id"] == "1.1"
    assert document["requirements"][0]["type"] == "mandatory"
    assert structured_path.exists()
