# Project Expert AI — Audit Skill/RAG readiness (recovered baseline + JSON 2.0 update)

**Revision:** 2026-09-25  
**Purpose:** восстановление исходной матрицы аудита Skill/RAG и фиксация только подтверждённых изменений после перехода нормативной базы на Normative JSON 2.0.

## 1. Источник исходного аудита

Исходная матрица восстановлена по фактическому diagnostic report запуска проверки документа:

- document_id: `53c22e43fcc843ef81f950516e81e68d`
- skill_id: `vk_wastewater`
- checks: 13
- pages_checked: 30
- pages_available: 30
- max_pages: null
- check_scope.limited: false
- report schema: 1.1

Это именно baseline старого аудита. Его значения не пересчитываются и не переинтерпретируются задним числом.

## 2. Исходная матрица

| Check ID | Проверка | Candidates | Violations | Compliant | Unchecked | Baseline status |
|---|---|---:|---:|---:|---:|---|
| `wastewater_flow` | Расчётные расходы | 3 | 0 | 0 | 3 | evidence_found |
| `sewer_diameter` | Диаметры | 2 | 0 | 0 | 2 | evidence_found |
| `sewer_slope` | Уклоны | 1 | 0 | 0 | 1 | evidence_found |
| `sewer_ventilation` | Вентиляция | 1 | 1 | 0 | 0 | evidence_found |
| `sewer_outlets` | Выпуски | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `sewer_cleanouts` | Ревизии и прочистки | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `sewer_material` | Материалы | 2 | 0 | 0 | 2 | evidence_found |
| `storm_separation` | Разделение систем | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `noise_insulation` | Шумоизоляция | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `irrigation` | Поливочные устройства | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `meters` | Приборы учёта | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `emergency_outlets` | Аварийные решения | 0 | 0 | 0 | 0 | no_evidence_candidate |
| `ar_coordination` | Координация с АР | 2 | 0 | 1 | 1 | evidence_found |

### Важное замечание по baseline

Baseline показывает поведение конкретного запуска документа, а не окончательную готовность каждого Skill.

В частности, старый отчёт содержал одно нарушение по `sewer_ventilation`, но это значение **не изменяется в этой ревизии**, потому что текущая задача — не повторная экспертная переоценка старого результата, а фиксация подтверждённых изменений после JSON 2.0.

## 3. Что изменилось после внедрения Normative JSON 2.0

Для СП 30.13330.2020 подтверждена рабочая цепочка:

`PDF → parsed JSON → Normative JSON 2.0 → FAISS index → retrieval → normative requirement`

Актуальная версия:

- document_id: `СП_30.13330.2020`
- version_id: `СП_30.13330.2020_20260925_111345_046143`
- pages: 97
- schema_version: 2.0
- requirements: 181
- references: 17
- validation: PASS
- FAISS vectors/chunks: 1887
- vector index: present

Это подтверждено отдельным реальным экспериментом `sewer_diameter`.

## 4. Подтверждённое изменение: sewer_diameter

Эксперимент:

`training/evaluation/experiment_sewer_diameter_real_chain_20260915.py`

Результат:

- STATUS: `PASS`
- retrieved: 6
- expected internal norm selected: `true`
- expected clause selected: `true`
- forbidden external norm excluded: `true`

Ключевое найденное нормативное требование:

**СП 30.13330.2020, п. 18.34**

> Диаметр и уклон выпуска следует определять расчетом. Конструктивно диаметр выпуска должен быть не меньше диаметра наибольшего из стояков, присоединяемых к выпуску.

Таким образом, для `sewer_diameter` впервые подтверждена полная рабочая часть цепочки:

`Skill → normative routing → JSON 2.0 → FAISS retrieval → exact clause 18.34 → requirement extraction → Qwen input gate`

### Что именно исправлено

Ранее chunk-level metadata могла указывать на страницу с несколькими пунктами как на точный clause. Это приводило к выбору структурно связанного, но семантически другого пункта.

Теперь extraction использует фактический текст chunk и выделяет точный clause segment. Для реального кейса это позволило корректно выделить **18.34**.

## 5. Матрица обновления

| Check ID | Baseline | JSON 2.0 verification | Изменение статуса |
|---|---|---|---|
| `wastewater_flow` | evidence_found | не проверялся заново | без изменения |
| `sewer_diameter` | evidence_found / 2 unchecked | **PASS — реальный retrieval, clause 18.34** | **подтверждён RAG/requirement path на JSON 2.0** |
| `sewer_slope` | evidence_found / 1 unchecked | не проверялся заново | без изменения |
| `sewer_ventilation` | evidence_found / 1 violation | не проверялся заново | без изменения |
| `sewer_outlets` | no_evidence_candidate | не проверялся заново | без изменения |
| `sewer_cleanouts` | no_evidence_candidate | не проверялся заново | без изменения |
| `sewer_material` | evidence_found / 2 unchecked | не проверялся заново | без изменения |
| `storm_separation` | no_evidence_candidate | не проверялся заново | без изменения |
| `noise_insulation` | no_evidence_candidate | не проверялся заново | без изменения |
| `irrigation` | no_evidence_candidate | не проверялся заново | без изменения |
| `meters` | no_evidence_candidate | не проверялся заново | без изменения |
| `emergency_outlets` | no_evidence_candidate | не проверялся заново | без изменения |
| `ar_coordination` | evidence_found / 1 compliant / 1 unchecked | не проверялся заново | без изменения |

## 6. Текущий технический статус pipeline

### Подтверждено

- Skill `vk_wastewater` существует и содержит 13 проверок.
- Vision → Skill filtering → RAG chain существует.
- Normative Router для внутреннего водоотведения работает.
- Normative JSON 2.0 для СП 30.13330.2020 валидирован.
- Индекс на JSON 2.0 создан.
- Retrieval по актуальной версии нормы работает.
- Exact clause extraction работает на реальном кейсе `sewer_diameter`.
- Requirement extraction возвращает текст п. 18.34.
- Qwen input gate для реального кейса проходит.

### Пока НЕ подтверждено этой ревизией

Нельзя считать автоматически подтверждёнными на JSON 2.0:

- `wastewater_flow`
- `sewer_slope`
- `sewer_ventilation`
- `sewer_outlets`
- `sewer_cleanouts`
- `sewer_material`
- `storm_separation`
- `noise_insulation`
- `irrigation`
- `meters`
- `emergency_outlets`
- `ar_coordination`

Для них нужны отдельные реальные проверки через актуальный normative index.

## 7. Отдельно зафиксированный gap

Для п. 18.34 нормативное условие является **реляционным**, а не числовым:

`D_выпуска >= D_наибольшего_стояка`

Проектное доказательство в реальном эксперименте содержит `Ø110 мм` для выпуска, но не содержит подтверждённого диаметра наибольшего присоединённого стояка.

Поэтому сам факт успешного retrieval **не означает**, что compliance decision уже можно считать завершённым.

Корректная следующая проверка для этого кейса должна установить наличие/отсутствие второго проектного факта. При его отсутствии результат должен оставаться `unchecked`, а не превращаться в violation/compliant.

## 8. Что НЕ входит в эту ревизию

Эта ревизия сознательно не включает:

- проектирование Canonical Audit Case;
- внедрение Normative Trace;
- новую архитектуру evidence model;
- массовую переработку Skill Registry;
- повторную экспертную оценку старых findings;
- изменение старых результатов без нового подтверждающего эксперимента.

Текущая цель остаётся прежней:

**довести существующие Skill + RAG + Requirement + Decision цепочки до реально работающего состояния, а уже после этого переходить к Canonical Audit Case / Normative Trace.**

## 9. Следующий этап аудита

Следующий шаг — не переписывать архитектуру, а последовательно прогнать существующие Skill/check_id через актуальную нормативную базу и заполнить для каждого:

`Visual → Skill → Routing → JSON 2.0 RAG → Requirement → Decision → E2E`

Первым подтверждённым baseline является:

`sewer_diameter → СП 30.13330.2020 JSON 2.0 → 18.34 → PASS`

Остальные строки матрицы остаются без изменения до появления аналогичного фактического подтверждения.
