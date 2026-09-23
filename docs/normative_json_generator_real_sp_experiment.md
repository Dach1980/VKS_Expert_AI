# Реальный прогон СП: Normative JSON 2.0 Generator

## Назначение

Этот документ фиксирует состояние реализации перехода нормативной базы на **Normative JSON 2.0** и служит контрольной точкой для первого прогона реального СП.

Цель: получить воспроизводимую цепочку

```
PDF → PDFPageProcessor → Normative JSON 2.0 → Validator PASS → Index
```

Искусственные тестовые fixtures не заменяют проверку на реальном нормативном PDF.

## Контрольный документ

Первым реальным документом для эксперимента используется:

- Номер: **СП 30.13330.2020**
- Файл: **СП_30.13330.2020 Изм.5 01.03.2025.pdf**
- Тип: изменение №5
- Дата: 01.03.2025
- В Registry текущая версия должна получить отдельный `version_id`.

## Что реализовано

### 1. Normative JSON Generator

Файл:

`app/knowledge/normative/generator.py`

Generator:

1. использует результат `PDFPageProcessor`;
2. не дублирует PDF-разбор;
3. строит структуру документа;
4. выделяет разделы, пункты и приложения;
5. формирует `requirements`;
6. сохраняет provenance/source information;
7. записывает канонический JSON в `paths.structured`;
8. запускает `NormativeJSONValidator`;
9. сохраняет состояние генерации в `normative_generation.json`.

Generator намеренно **консервативный**: если из текста нельзя надёжно установить числовое значение, единицу измерения, область применения или связь с таблицей, он не должен придумывать эти сведения.

### 2. Validator

Normative JSON 2.0 проверяется существующим Validator.

Проверяются, в частности:

- соответствие JSON Schema;
- уникальность ID;
- существование clause/reference/table, на которые есть ссылки;
- диапазоны страниц;
- корректность bbox;
- целостность связей.

Индексация разрешается только при:

```json
{
  "status": "validated",
  "valid": true
}
```

### 3. API

Добавлен endpoint:

```
POST /api/norms/{document_id}/{version_id}/generate
```

Генерация выполняется в background task.

Состояние:

```
knowledge/.../index/normative_generation.json
```

Основные состояния:

- `running`
- `validated`
- `failed`

Этапы:

- `starting`
- `loading`
- `structure`
- `validation`

### 4. UI

В разделе «Нормы» добавлена кнопка:

**Создать JSON 2.0**

UI показывает прогресс:

- подготовка;
- извлечение страниц;
- построение структуры;
- Validator;
- Validator PASS;
- Validator ERROR.

Кнопка индексации блокируется до Validator PASS.

### 5. Защита индексации

И API, и production index builder независимо проверяют:

1. PDF существует;
2. Normative JSON 2.0 существует;
3. `schema_version == "2.0"`;
4. присутствует `normative_generation.json`;
5. `status == "validated"`;
6. `valid == true`.

Таким образом, старый структурный JSON не должен использоваться как основание для нового production index.

### 6. JSON 2.0 реально используется при индексации

`app/knowledge/document_chunk_builder.py` получает связи из Normative JSON 2.0 и добавляет их в metadata chunks:

```json
{
  "normative_json": {
    "clause_ids": [],
    "requirement_ids": [],
    "reference_ids": []
  }
}
```

Следовательно, JSON 2.0 является не только gate перед индексацией, но и источником структурной нормативной метаинформации для индекса.

## Что НЕ является частью Generator

Generator не должен переносить в нормативный JSON:

- retrieval scores;
- ranking;
- `best_score`;
- `query_hits`;
- `route_reason`;
- `has_numeric_rule`;
- compliance/violation/support flags.

Это признаки работы retrieval/checking, а не свойства нормативного документа.

## Почему Generator сделан универсальным

Старый `StructureParser` содержит логику, специфичную для СП 30 и `EXPECTED_SECTIONS`.

Новый Generator не должен зависеть от структуры одного конкретного СП.

Это важно для дальнейшей миграции:

```
СП 30 → СП 31 → СП 32 → остальные СП
```

без создания отдельного набора hardcoded правил для каждого документа.

## Regression

Созданы/используются:

- `tests/normative/test_normative_json_generator.py`
- `tests/normative/test_normative_validator.py`
- `.github/workflows/normative-regression.yml`

Последний зафиксированный CI прогон проверяет:

- Python syntax;
- frontend syntax;
- Validator regression;
- Generator regression.

Validator regression: **10 tests PASS**.

Generator regression проверяет, что:

- JSON 2.0 создаётся;
- Validator проходит;
- clause существует;
- requirement связан с clause;
- requirement имеет ожидаемый тип;
- structured JSON записан.

## История исправлений Generator

Во время тестовой реализации были обнаружены и исправлены:

1. неверный путь к JSON Schema;
2. `sha256: null`, нарушавший schema;
3. пропуск семантики в строке-заголовке пункта;
4. неоднозначный тестовый текст, который классифицировался как conditional.

Эти исправления были сделаны до перехода к реальному СП.

## Эксперимент на реальном СП

Для первого реального прогона нельзя менять Generator только ради получения PASS.

Сначала фиксируем исходный результат:

```
PDF
→ JSON 2.0
→ Validator
→ результат
```

Если Validator FAIL:

1. сохраняем JSON;
2. сохраняем `normative_generation.json`;
3. фиксируем реальные ошибки;
4. исправляем Generator;
5. повторяем генерацию;
6. снова запускаем regression;
7. только после PASS запускаем Index.

Если Generator создаёт JSON 2.0 и Validator PASS, следующим отдельным этапом запускается Index.

## Что необходимо сохранить после реального прогона

Для каждой реальной версии сохраняются:

- исходный PDF;
- имя исходного файла;
- `version_id`;
- generated Normative JSON 2.0;
- `normative_generation.json`;
- результат Validator;
- индекс FAISS;
- metadata chunks;
- commit SHA кода, которым выполнена генерация.

Это позволяет впоследствии сравнивать результаты разных версий Generator.

## Правило сравнения результатов

При изменении Generator нельзя сравнивать только факт `PASS/FAIL`.

Для реального СП необходимо сравнивать как минимум:

- количество страниц;
- количество sections;
- количество clauses;
- количество requirements;
- количество references;
- количество tables;
- распределение requirement types;
- покрытие страниц;
- наличие ссылок на несуществующие clauses/references/tables;
- количество warnings;
- содержимое representative clauses/requirements;
- metadata нормативных связей в chunks.

## Контрольная точка

На момент создания этого документа:

**тестовый Generator и Validator готовы; реальный СП ещё не считается успешно проиндексированным.**

Первый production-like эксперимент:

```
СП_30.13330.2020 Изм.5 01.03.2025.pdf
        ↓
JSON 2.0
        ↓
Validator PASS
        ↓
Index
```

После успешного контрольного прогона этот документ дополняется фактическими статистиками и результатами индексации.
