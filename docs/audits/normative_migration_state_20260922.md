# Состояние миграции нормативной базы — 2026-09-22

## Зафиксированное решение

Проект не возвращается к legacy-модели СП30 и не коммитит ранее созданные timestamp-версии JSON/индексов.

Нормативный production-контур должен строиться заново:

PDF нормативной редакции → модуль «Нормы» → новый расширенный JSON → validation → indexing → vector DB.

## Результат зачистки legacy

Удалены локально и подготовлены к удалению из Git:

- `knowledge/parsed/SP_30.13330.2020.json`
- `knowledge/structured/SP_30.13330.2020.json`
- `knowledge/regulations/SP_30.13330/СП_30.13330_базовая_версия.pdf`

Старый локальный `knowledge/index/SP_30.13330.2020.json` также удалён.

Не использовать legacy-контур `knowledge/parsed`, `knowledge/structured` и старую папку `knowledge/index` как источник нормативных данных.

## Промежуточные SP30 vector DB

Удалены локально:

- `СП_30.13330.2020_20260901_131113_910004`
- `СП_30.13330.2020_20260901_131113_939105`
- `СП_30.13330.2020_20260901_131114_011355`

Локально остаётся:

- `СП_30.13330.2020_20260901_131114_071565`

Но эта версия **не считается новым production-источником и не должна коммититься**. Она является остатком старого процесса индексации и будет заменена после повторной обработки PDF модулем «Нормы».

## Текущая локальная структура vector DB

Подтверждено 2026-09-22:

```
data/vectordb/
├── СП_30.13330.2020/
│   └── СП_30.13330.2020_20260901_131114_071565
├── СП_31.13330.2021/
│   └── СП_31.13330.2021_20260902_084832_463150
└── СП_32.13330.2018/
    └── СП_32.13330.2018_20260902_103742_199423
```

Эти существующие индексы относятся к старому JSON-процессу и **не являются основанием для production commit**.

## Исходные PDF для нового процесса

В локальном `knowledge/regulations/` находятся PDF различных редакций СП, включая имена вида:

```
СП_30.13330.2020 Изм.5 01.03.2025.pdf
```

Именно PDF редакций являются исходным материалом для нового модуля «Нормы».

Текущие PDF не следует автоматически превращать в production-индекс. Сначала необходимо провести аудит входных файлов и существующего кода модуля «Нормы».

## Git-правило

Не использовать `git add .` для фиксации этого состояния.

До завершения нового нормативного pipeline не коммитить:

- старые parsed JSON;
- старые structured JSON;
- старые timestamp JSON;
- старые vector indexes;
- экспериментальные файлы и результаты.

## Следующий этап

1. Аудит состава входных PDF в `knowledge/regulations/`.
2. Проверка текущего кода модуля «Нормы».
3. Проверка parser имени файла и формирования version metadata.
4. Проверка фактической схемы нового расширенного JSON.
5. Выбор одной тестовой редакции СП.
6. Генерация нового JSON через модуль «Нормы».
7. Валидация JSON.
8. Только после успешной проверки — индексация.
9. Затем повторить для всех нужных СП.
10. После этого сформировать чистый production commit.

## Важное архитектурное ограничение

Не восстанавливать нормативную применимость через бесконечные `if/elif/else`. Источником нормативного контекста должна стать структурированная нормативная база, а выбор требований должен опираться на metadata, структуру документа, редакцию и RAG.

## История диагностического аудита

Ранее отдельно доказано:

- Qwen корректно определяет неприменимость нескольких текстово похожих требований для кандидата «диаметр выпуска»;
- downstream `deterministic_numeric_comparison()` игнорировал эту применимость;
- `_finalise_decision()` мог терять provenance и подставлять первый requirement;
- parser единиц мог сопоставлять `0.5 МПа` с последующим `мм`;
- table-dependent requirement 18.36 ошибочно превращался в обычное числовое ограничение;
- generic word overlap по слову «диаметр» был слишком широким.

Эти проблемы **не исправляются сейчас**. Сначала завершается миграция нормативной базы и новый pipeline «Нормы».


## Граница StructureParser → SPIndexBuilder и формат PDFPageProcessor — 2026-09-22

Проверены в `main`:
- `app/knowledge/structure_parser.py`
- `app/knowledge/build_sp_index.py`
- `app/knowledge/pdf_page_processor.py`

### Что выдаёт PDFPageProcessor

`PDFPageProcessor` формирует parsed JSON schema `1.0`.

На уровне документа:
- `schema_version`
- `document.number`
- `document.title`
- `document.source_file`
- `document.pages`
- `document_id`
- `version`
- `pages[]`
- `created`

Каждая страница содержит:
- `document.number`
- `document.title`
- `document.source_file`
- `document.pages`
- `document_id`
- `version`
- `page`
- `geometry.width`
- `geometry.height`
- `source.pdf`
- `source.pipeline = ["PyMuPDF", "PDFPageProcessor"]`
- `created`
- `blocks[]`
- `formulas[]`

Каждый block содержит:
- `index`
- `bbox = [x0, y0, x1, y1]`
- `text`

На текущем этапе `formulas[]` всегда создаётся пустым.

### Что использует StructureParser

`StructureParser.build_structure()` получает parsed JSON и использует:
- `document`
- `pages[].page`
- `pages[].blocks[].text`
- `pages[].blocks[].bbox`

Он дополнительно формирует:
- sections: `type, number, title, page_start, page_end, clauses`
- clauses: `type, number, level, text, page_start, page_end, source.file, source.blocks[].page, source.blocks[].bbox`
- appendices: `type, number, title, page_start, page_end, blocks`

### Архитектурная граница

`PDFPageProcessor` отвечает за PDF → parsed representation → provenance.

`StructureParser` отвечает за parsed representation → структурные разделы/пункты/приложения.

Новый Normative JSON Generator должен стоять после `StructureParser` и использовать уже существующие:
- текст;
- номер пункта;
- страницы;
- bbox;
- исходный PDF/source provenance;
- document_id/version.

Он не должен повторно извлекать PDF-текст, страницы или bbox.

При этом Generator должен добавлять новую нормативную семантику:
- requirements;
- subject/attribute;
- operator/value/unit;
- condition/scope/exceptions;
- tables;
- references;
- edition/change metadata;
- связи с provenance.

### SPIndexBuilder

Текущий `SPIndexBuilder.run()` сам запускает:
`PDFPageProcessor → StructureParser → PageEnricher → DocumentChunkBuilder → EmbeddingBuilder`.

Результат `StructureParser` сохраняется как `structured JSON schema 1.0`, но последующие chunk/embedding стадии работают через page/enriched-page pipeline, а не как прямой consumer этого structured JSON.

Следовательно, новый Generator не следует встраивать внутрь `StructureParser` и не следует делать `SPIndexBuilder` владельцем нормативной семантики. Между структурным JSON и индексированием нужен отдельный слой:

`StructureParser → Normative JSON Generator → Validator → Indexing`.

