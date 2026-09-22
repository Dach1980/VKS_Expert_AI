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

## Архитектурное ограничение

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

Проверены:

- `app/knowledge/structure_parser.py`
- `app/knowledge/build_sp_index.py`
- `app/knowledge/pdf_page_processor.py`

### PDFPageProcessor

Формирует parsed JSON schema 1.0.

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

Страница содержит:

- document metadata;
- `page`;
- `geometry.width/height`;
- `source.pdf`;
- `source.pipeline = ["PyMuPDF", "PDFPageProcessor"]`;
- `created`;
- `blocks[]`;
- `formulas[]`.

Block содержит:

- `index`;
- `bbox = [x0,y0,x1,y1]`;
- `text`.

На текущем этапе `formulas[]` всегда создаётся пустым.

### StructureParser

`StructureParser.build_structure()` использует:

- `document`;
- `pages[].page`;
- `pages[].blocks[].text`;
- `pages[].blocks[].bbox`.

Формирует:

- sections: `type, number, title, page_start, page_end, clauses`;
- clauses: `type, number, level, text, page_start, page_end, source.file, source.blocks[].page, source.blocks[].bbox`;
- appendices: `type, number, title, page_start, page_end, blocks`.

### Граница

`PDFPageProcessor` отвечает за PDF → parsed representation → provenance.

`StructureParser` отвечает за parsed representation → структурные разделы/пункты/приложения.

Normative JSON Generator должен стоять после StructureParser и использовать уже существующие текст, номер пункта, страницы, bbox, source provenance, document_id/version. Он не должен повторно извлекать PDF-текст, страницы или bbox.

## PageEnricher / DocumentChunkBuilder

Проверены:

- `app/knowledge/page_enricher.py`
- `app/knowledge/document_chunk_builder.py`

### PageEnricher

Работает поверх page JSON, уже созданного PDFPageProcessor.

Повторно использует:

- page;
- blocks[].text;
- blocks[].bbox;
- document;
- version;
- geometry.

Нормализует blocks в `text_blocks[]`, умеет подключать формулы из `knowledge/work/formulas/page_NNN/page_NNN_formulas.json` и формирует `embedding_text`.

Это индексное enrichment, а не основная normative provenance.

### DocumentChunkBuilder

Создаёт retrieval chunks, а не нормативную структуру.

Формирует:

- `chunk_id`;
- `document`;
- `document_id`;
- `version`;
- `page`;
- `location.page`;
- `location.bbox`;
- `location.pdf`;
- `content.text`;
- `metadata.normative`.

Не знает нормативной семантики requirement/subject/attribute/operator/value/unit/condition/applicability/exception/table/reference.

Текущий builder получает страницы из `paths.enriched`, поэтому появление Generator само по себе не делает его источником RAG. Интеграцию с индексированием решать только после валидации первого Normative JSON 2.0.

# Normative JSON 2.0 — проектный контракт

## Цель

Normative JSON 2.0 — отдельная семантическая модель нормативного документа между StructureParser и indexing.

Целевой поток:

```
PDF
  ↓
PDFPageProcessor
  ↓
parsed JSON 1.0
  ↓
StructureParser
  ↓
Normative JSON Generator
  ↓
Normative JSON 2.0
  ↓
Validator
  ↓
Indexing
  ├─ PageEnricher
  ├─ DocumentChunkBuilder
  └─ EmbeddingBuilder
```

Контракт верхнего уровня:

```
NormativeDocument
├── schema_version
├── document
│   ├── document_id
│   ├── number
│   ├── title
│   ├── document_type
│   ├── edition
│   │   ├── id
│   │   ├── label
│   │   ├── base_year
│   │   └── amendments[]
│   └── source
│       ├── file
│       ├── original_filename
│       ├── sha256
│       └── pages
├── structure
│   ├── sections[]
│   │   └── clauses[]
│   └── appendices[]
├── requirements[]
├── tables[]
├── references[]
└── provenance
```

## Полный контракт полей

### document

```
document.document_id
document.number
document.title
document.document_type
document.edition
document.source
```

### edition

```
edition.id
edition.label
edition.base_year
edition.amendments[]
edition.amendments[].number
edition.amendments[].effective_from
```

### source

```
source.file
source.original_filename
source.sha256
source.pages
```

### structure / section

```
structure.sections[]
section.number
section.title
section.page_start
section.page_end
section.source
section.clauses[]
```

### clause

```
clause.number
clause.level
clause.text
clause.page_start
clause.page_end
clause.source
clause.requirements[]
clause.table_refs[]
clause.references[]
```

### appendix

```
appendix.number
appendix.title
appendix.page_start
appendix.page_end
appendix.source
appendix.requirements[]
appendix.tables[]
appendix.references[]
```

### requirement

```
requirement.requirement_id
requirement.clause_id
requirement.text
requirement.type
requirement.subject
requirement.relation
requirement.values[]
requirement.condition
requirement.scope
requirement.applicability
requirement.exceptions[]
requirement.table_refs[]
requirement.references[]
requirement.source
```

### subject

```
subject.object
subject.attribute
```

### normative value

```
values[].value
values[].unit
values[].condition
```

### condition

```
condition.text
condition.facts[]
condition.facts[].subject
condition.facts[].attribute
condition.facts[].relation
condition.facts[].value
condition.facts[].unit
```

### scope

```
scope.discipline
scope.system
scope.segment
```

### applicability

```
applicability.systems[]
applicability.segments[]
applicability.objects[]
applicability.contexts[]
applicability.exclusions[]
```

Важно: `applicable: true/false` сюда не переносится. Это результат сопоставления нормативного условия с проектом и относится к evaluation.

### exception

```
exception.text
exception.conditions[]
exception.requirement_refs[]
```

### table

```
table.table_id
table.number
table.title
table.columns[]
table.columns[].id
table.columns[].name
table.rows[]
table.rows[].id
table.rows[].cells[]
table.rows[].cells[].column
table.rows[].cells[].text
table.rows[].cells[].value
table.rows[].cells[].unit
table.source
```

### reference

```
reference.reference_id
reference.type
reference.target
reference.target.document_id
reference.target.clause
reference.target.table_id
reference.target.appendix
reference.target.document_number
reference.source
```

Типы:

- `clause_reference`
- `table_reference`
- `appendix_reference`
- `document_reference`
- `standard_reference`

### provenance

```
provenance.generator
provenance.generator.name
provenance.generator.version
provenance.source_format
provenance.extraction
provenance.extraction.pipeline[]
```

Entity-level source:

```
source.file
source.blocks[]
source.blocks[].page
source.blocks[].bbox
```

## Карта происхождения полей

### KEEP — существующая модель без концептуального изменения

- `document.document_id` — canonical Registry, `registry_manager.py`.
- `document.number` — `filename_parser.py`, canonical Registry.
- `document.title` — `norm_metadata.py`, Registry и исходный PDF/parsed representation.
- `document.document_type` — Registry.
- `edition.id` — canonical `version_id`, формируемый filename parser.
- `edition.amendments[].number` — `ParsedFilename.amendment_number`.
- `edition.amendments[].effective_from` — `ParsedFilename.effective_date`.
- `source.file` — Registry / normative metadata / PDF pipeline.
- `source.original_filename` — filename parser.
- `source.sha256` — canonical Registry.
- `section.title` — StructureParser.
- `section.page_start`, `section.page_end` — StructureParser.
- `clause.number` — StructureParser.
- `clause.level` — StructureParser.
- `clause.text` — StructureParser.
- `clause.page_start`, `clause.page_end` — StructureParser.
- `clause.source` — StructureParser.
- `requirement_id` — `training/schemas/normative_requirement.schema.json` и experiment dataset.

### EXTEND

- `edition.amendments` — существующее представление изменения расширяется до массива.
- `source.pages` — нормализует существующий page count.
- `section.number` — существующий numeric number нормализуется как string.
- `requirement.type` — основан на существующем `requirement_type`, при этом `table` заменяется семантически на `table_dependent`.
- `condition` — старый текст сохраняется, добавляются структурированные facts.
- `exceptions` — старый exception расширяется условиями и ссылками.
- `values[]` — расширяет `normative_value + normative_unit` до нескольких структурированных значений.
- `reference.type` — существующий `reference` type получает полноценную структуру target/source.

### MOVE / RENAME

- `requirement.clause` → `requirement.clause_id`.
- `requirement.requirement` → `requirement.text`.
- `object` → `subject.object`.
- `parameter` → `subject.attribute`.
- runtime `operator` из `app/rag/normative_requirement.py` → normative `relation`.
- `normative_value` + `normative_unit` → `values[]`.

Дублирование document/version/section metadata внутри каждой requirement не сохраняется: контекст наследуется от root/clause.

### NEW

- `schema_version = 2.0`.
- `edition.label`.
- `edition.base_year`.
- `clause.table_refs`.
- `clause.references`.
- `scope`.
- `applicability` как описание условий применимости, без runtime result.
- `table_refs` на requirement.
- `references` на requirement.
- полноценные `tables[]`, columns, rows, cells.
- полноценные `references[]` и target.
- requirement/table/reference-level semantic provenance.
- document-level `provenance.generator`.
- `provenance.source_format`.
- `provenance.extraction`.

## Источники существующих моделей

### Requirement schema

`training/schemas/normative_requirement.schema.json` уже содержит:

```
requirement_id
document
version
clause
section
requirement
requirement_type
system
segment
object
parameter
condition
exception
normative_value
normative_unit
source_page
```

Это основа requirement части, но не готовый JSON 2.0.

### Runtime requirement extraction

`app/rag/normative_requirement.py` уже содержит executable representation:

```
norm
version
clause
requirement
parameter
operator
normative_value
normative_unit
page
source
metadata
metadata_text
```

Особенно важно, что существующий `operator` является источником концепции для нового `relation`.

### Dataset

`training/datasets/experiment_001/requirements.jsonl` подтверждает реальные структуры требований, включая conditional requirements и несколько нормативных значений.

### Evidence trace

`training/schemas/evidence_trace.schema.json` содержит:

```
fact_id
requirement_id
relation
applicability
missing_condition
```

и состояния:

```
applicable
not_applicable
not_proven
```

Это модель evidence/evaluation, а не нормативного документа. Эти result states в Normative JSON 2.0 не переносятся.

### Audit case

`training/schemas/audit_case.schema.json` содержит нормативное evidence и applicability concepts:

```
system
segment
object
parameter
reason
applicable
```

Из него переиспользуются semantic concepts `system/segment/object/parameter`, но `applicable: boolean` в normative JSON не переносится.

### Canonical metadata

Источники:

- `app/knowledge/filename_parser.py`
- `app/knowledge/norm_metadata.py`
- `app/knowledge/registry_manager.py`

Они являются источником истины для:

```
document_id
number
title
document_type
version_id
edition
source.file
source.sha256
source.original_filename
amendment number
effective date
```

Generator не должен создавать вторую metadata/Registry модель.

### Tables

Полноценной модели таблиц в текущем репозитории не найдено. `requirement_type = table` — недостаточная модель.

Поэтому `tables[]`, columns, rows, cells и table links создаются впервые.

### References

Полноценной модели ссылок также не найдено. `requirement_type = reference` — только классификация требования.

Поэтому `references[]`, target и typed links создаются впервые.

## Что НЕ входит в Normative JSON 2.0

Не переносить:

- retrieval scores;
- RAG ranking;
- `best_score`;
- `query_hits`;
- `route_reason`;
- `has_numeric_rule`;
- `applicable: true/false`;
- `violation`;
- `compliance`;
- `supports_violation`;
- `supports_compliance`.

Это runtime/evaluation layer.

## Ключевой принцип Generator

Generator не должен угадывать нормативную семантику там, где исходный текст её не подтверждает.

Если для фрагмента нельзя достоверно установить:

- operator;
- value;
- unit;
- applicability;
- table relation;
- reference target;

исходный текст и provenance должны сохраняться, а semantic field должен оставаться неопределённым/отсутствующим согласно контракту.

Нельзя превращать неопределённость в ложное нормативное правило.

## Контрольный набор для первого fixture

Перед реализацией полноценного Generator контракт должен быть проверен на:

- 11.5 — условие / зазор / единицы;
- 18.18 — обычное текстовое требование;
- 18.31 — защита от ложного числового вывода;
- 18.36 — table-dependent requirement;
- 21.18 — числовая/условная структура.

Цель fixture — доказать, что схема способна выразить реальные нормативные конструкции, а не только простые числовые правила.

## Следующий этап

1. Создать `normative_document.schema.json` в выделенном каталоге схем.
2. Создать минимальный fixture Normative JSON 2.0 на одном контрольном фрагменте.
3. Провалидировать сам schema и fixture.
4. Только после PASS перейти к реализации Validator.
5. Затем реализовать Generator поверх существующих outputs PDFPageProcessor/StructureParser.
6. После первого валидного JSON отдельно решить интеграцию Normative JSON с indexing/RAG.
7. Не менять сейчас downstream applicability/numeric comparison и не восстанавливать routing через `if/elif/else`.

# Validation Normative JSON 2.0 — 2026-09-22

## Fixture

Создан минимальный контрольный fixture:

- training/fixtures/normative_document_2_0_minimal.json
- commit: 7df6114b62d215c12561c210525328bd0fdc2e9f

Fixture содержит минимальный полный документ, одну секцию, один пункт и одно обязательное числовое требование с subject, relation, values[], condition, scope, applicability и provenance.
Fixture намеренно не использует runtime-поле applicable.

## Проверка schema

Проверена JSON-структура самой schema:

- schema корректно разбирается как JSON;
- $schema = JSON Schema Draft 2020-12;
- найдено 33 внутренних $ref;
- неразрешённых ссылок на $defs не обнаружено.

Во время negative validation обнаружен реальный дефект первого варианта schema: prefixItems + items:false без ограничения длины не запрещал bbox из трёх координат. Исправление внесено: source_block.bbox.minItems = 4 и maxItems = 4.

Commit исправления schema: ecdac402e2e3fcbddb7ed3edffdaa1f44171cb35.

После исправления проверка повторена.

## Validation results

Проверка выполнена непосредственно относительно текущего содержимого training/schemas/normative_document.schema.json; negative cases получены мутацией одного и того же положительного fixture.

| Case | Ожидание | Результат |
|---|---|---|
| Положительный fixture | PASS | **PASS** |
| Отсутствует requirement_id | FAIL | **FAIL / корректно отклонён** |
| bbox содержит 3 координаты | FAIL | **FAIL / корректно отклонён** |
| Неизвестный requirement.type | FAIL | **FAIL / корректно отклонён** |
| applicable: true в requirement | FAIL | **FAIL / корректно отклонён** |
| values: [100] вместо массива объектов | FAIL | **FAIL / корректно отклонён** |

Точные диагностические причины:

- $.requirements[0].requirement_id: required
- $.requirements[0].source.blocks[0].bbox: minItems
- $.requirements[0].type: enum
- $.requirements[0].applicable: additionalProperties
- $.requirements[0].values[0]: type

Таким образом, после исправления bbox все запланированные positive/negative проверки проходят по ожидаемому поведению.

## Что доказала проверка

1. Базовый Normative JSON 2.0 может быть выражен текущим контрактом.
2. Обязательный requirement_id действительно enforced schema.
3. bbox теперь строго требует четыре координаты.
4. requirement.type ограничен закрытым enum.
5. Runtime/evaluation-поле applicable не может незаметно попасть в normative JSON.
6. values[] действительно является массивом структурированных объектов, а не массивом сырых чисел.
7. additionalProperties: false работает как защита от возврата к legacy/runtime полям.

## Gate

**VALIDATION GATE: PASS.**

До этого PASS реализация Validator не начиналась.

Следующий этап — проектирование отдельного Normative JSON Validator, не смешивая его с Generator, StructureParser или RAG.

## Проект Validator

Validator должен иметь две независимые группы проверок.

### 1. Schema validation

Отвечает только за соответствие JSON Schema 2.0: required fields, types, enum, array/object structure, bbox shape, additional properties и базовые constraints.

Schema validation не должна исправлять входной JSON.

### 2. Semantic/integrity validation

После schema PASS Validator должен проверять связи и внутреннюю согласованность документа:

- requirement.clause_id существует среди clauses;
- table_refs указывают на существующие tables;
- references[] и typed links не ссылаются на несуществующие внутренние targets;
- requirement_id, table_id и reference_id уникальны;
- страницы provenance находятся в диапазоне document.source.pages;
- bbox имеет четыре координаты и, при доступной geometry страницы, не выходит за её границы;
- page_start <= page_end;
- section/clause provenance согласуется с указанными страницами;
- значения/условия не должны автоматически преобразовываться в другие нормативные значения.

Validator должен возвращать ошибки, а не молча исправлять JSON.

### Не входит в Validator

Validator не должен выбирать применимость требования к проекту, выставлять applicable true/false, сравнивать проектные значения с нормативными, рассчитывать violation/compliance, ранжировать RAG hits, выбирать лучший нормативный документ, заменять Generator или исправлять смысловые ошибки Qwen.

## Следующий практический шаг

После PASS проектировать реализацию Validator как отдельного слоя:

Normative JSON 2.0 → Schema validation → Semantic integrity validation → PASS/FAIL → Indexing

Только после этого переходить к Generator.
# Normative JSON Validator contract — 2026-09-23

Зафиксирован первый контракт Validator и базовый набор тестов.

Структура:

- app/knowledge/normative/validator.py — публичный API и orchestration;
- app/knowledge/normative/schema_validator.py — JSON Schema validation;
- app/knowledge/normative/integrity_validator.py — semantic/integrity checks;
- app/knowledge/normative/validation_result.py — ValidationResult, ValidationError, ValidationWarning;
- app/knowledge/normative/validation_codes.py — стабильные machine-readable коды ошибок;
- app/knowledge/normative/__init__.py — публичные exports;
- tests/normative/test_normative_validator.py — первый regression-набор.

Публичный API:

    NormativeJSONValidator(schema_path).validate(document) -> ValidationResult

Порядок выполнения зафиксирован: SchemaValidator запускается первым; IntegrityValidator запускается только после schema PASS. При schema FAIL integrity-проверки не выполняются.

Первый regression-набор содержит 10 случаев:

1. valid minimal fixture -> PASS;
2. missing requirement_id -> schema ERROR;
3. invalid bbox -> schema ERROR;
4. unknown requirement.type -> schema ERROR;
5. applicable -> schema ERROR через additionalProperties;
6. invalid values[] -> schema ERROR;
7. nonexistent clause_id -> integrity ERROR;
8. duplicate requirement_id -> integrity ERROR;
9. nonexistent table_ref -> integrity ERROR;
10. out-of-range provenance page -> integrity ERROR.

На этом этапе тесты зафиксированы в репозитории, но отдельный execution среды CI/pytest ещё не выполнялся через GitHub API. Поэтому данный шаг является фиксацией контракта и regression suite, а не утверждением о выполнении тестов.

Validator не определяет applicability к проекту, не сравнивает проектные и нормативные значения, не рассчитывает violation/compliance, не ранжирует RAG и не выбирает нормативный документ.

Следующий шаг: выполнить pytest в рабочем окружении проекта; при PASS — уточнить и реализовать semantic integrity checks, не расширяя Validator в сторону Generator/RAG/runtime applicability.