# Project Expert AI — Audit Skill/RAG readiness

**Revision:** 2026-09-25  
**Purpose:** актуализация аудита после перехода на Normative JSON 2.0 и реального запуска проверки через UI. Этот документ фиксирует фактическое состояние цепочки **Visual → Skill → Routing → RAG → Requirement → Decision → Result**. Word/PDF-экспорт в эту ревизию не входит.

## 1. Исходный baseline

Исходная матрица восстановлена по фактическому diagnostic report запуска проверки документа:

- document_id: `53c22e43fcc843ef81f950516e81e68d`
- skill_id: `vk_wastewater`
- checks: 13
- pages_checked: 30
- pages_available: 30
- max_pages: null
- check_scope.limited: false
- report schema: 1.1

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

Baseline не переинтерпретируется задним числом.

## 2. Нормативная база: JSON 2.0

Для СП 30.13330.2020 подтверждена рабочая цепочка индексации:

`PDF → parsed JSON → Normative JSON 2.0 → FAISS index`

Актуальная версия:

- document_id: `СП_30.13330.2020`
- version_id: `СП_30.13330.2020_20260925_111345_046143`
- pages: 97
- schema_version: 2.0
- requirements: 181
- references: 17
- validation: PASS
- FAISS chunks/vectors: 1887
- vector index: present

Таким образом, **нормативная база и её индекс сами по себе подтверждены**.

## 3. Что было подтверждено отдельным реальным RAG-экспериментом

Для `sewer_diameter` выполнен реальный эксперимент:

`training/evaluation/experiment_sewer_diameter_real_chain_20260915.py`

Результат:

- STATUS: `PASS`
- retrieved: 6
- expected internal norm selected: `true`
- expected clause selected: `true`
- forbidden external norm excluded: `true`

Точно извлечён:

**СП 30.13330.2020, п. 18.34**

> Диаметр и уклон выпуска следует определять расчетом. Конструктивно диаметр выпуска должен быть не меньше диаметра наибольшего из стояков, присоединяемых к выпуску.

Для этого искусственно изолированного реального кейса подтверждена цепочка:

`Skill → Routing → JSON 2.0 → FAISS retrieval → exact clause 18.34 → Requirement extraction → Qwen input gate`

Это подтверждение остаётся действующим.

## 4. Критическое уточнение: этот эксперимент НЕ подтверждает E2E-проверку документа через UI

Позднее была предпринята попытка построить матрицу всех 13 Skill/check_id.

Эксперимент:

`training/evaluation/experiment_skill_rag_matrix_20260925.py`

Первоначальная реализация воспроизводила сохранённые кандидаты из старого отчёта. Она была изменена на работу от исходного PDF, но при этом стала напрямую вызывать Vision runner.

Это оказалось **неверной точкой входа для данного аудита**.

Причина:

- UI уже передаёт выбранную пользователем модель;
- UI уже передаёт выбранный диапазон страниц;
- production job передаёт эти параметры в `run_resilient_check`;
- отдельный matrix experiment вызывал `_vision_request()` самостоятельно;
- поэтому он мог использовать другую модель и другой диапазон страниц;
- такой запуск не является эквивалентом реальной проверки документа через UI.

В результате запуск matrix experiment был остановлен и **не используется как доказательство состояния production E2E**.

### Следствие

Нельзя использовать полученные из этого эксперимента значения вроде:

- `NO_CANDIDATE`
- `ROUTE_FAIL`
- `RAG_NO_HIT`
- `NO_REQUIREMENT`

как итоговую оценку 13 Skill.

Они относятся к диагностическому запуску, который не прошёл через production UI job с его моделью и selected_pages.

## 5. Новый факт: реальный production UI запуск

25.09.2026 был выполнен реальный запуск через интерфейс:

- документ: `Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1.pdf`
- model: `qwen3.5-4b`
- страницы: `5–10`
- статус: completed
- результатов: 3
- нарушений: 0
- соответствий: 0
- требуют проверки: 3

Это **важный новый audit fact**, потому что запуск прошёл через настоящий production entrypoint, а не через отдельный диагностический Vision runner.

## 6. Что этот production запуск пока доказывает

Он доказывает:

`UI → job → selected model/pages → production checking pipeline → result`

и показывает, что production pipeline способен завершить проверку и сформировать три результата со статусом `unchecked`.

Однако он **не доказывает наличие полной цепочки для каждого результата**.

В частности, из доступного результата нельзя надёжно установить для каждого из трёх результатов:

`Visual candidate → Skill → Routing → RAG hit → Requirement → Decision`

Также текущий публичный результат не сохраняет/не показывает всю эту диагностическую цепочку как обязательную часть результата проверки.

## 7. Текущий RAG-аудит: что подтверждено, а что нет

| Этап | Статус | Основание |
|---|---|---|
| Normative PDF | PASS | СП 30.13330.2020, 97 страниц |
| Parsed normative JSON | PASS | актуальная версия существует |
| Normative JSON 2.0 | PASS | schema 2.0, validation PASS |
| FAISS index | PASS | 1887 chunks/vectors |
| Normative routing | PASS | подтверждено на `sewer_diameter` |
| RAG retrieval | PASS в изолированном `sewer_diameter` кейсе | 6 retrieved |
| Exact clause extraction | PASS на `18.34` | подтверждено реальным экспериментом |
| Requirement extraction | PASS на `18.34` | точный текст требования получен |
| UI → production job | PASS | реальный запуск 25.09.2026 |
| UI → Vision model/pages | PASS | `qwen3.5-4b`, страницы 5–10 |
| Production Visual → Skill → RAG для всех результатов | **НЕ ПОДТВЕРЖДЕНО** | полной трассировки в результате нет |
| Production RAG → Requirement для всех результатов | **НЕ ПОДТВЕРЖДЕНО** | полной трассировки в результате нет |
| Production Decision trace | **НЕ ПОДТВЕРЖДЕНО** | виден только итог `unchecked` |
| Полная E2E цепочка по документу | **НЕ ПОДТВЕРЖДЕНА** | промежуточные стадии теряются/не сохраняются в доступном результате |

## 8. Главный текущий дефект аудируемости

Сейчас существует разрыв между двумя уровнями:

### Уровень A — отдельный RAG-кейс

`Skill → Routing → RAG → Requirement`

Для `sewer_diameter` он реально работает.

### Уровень B — реальная проверка документа

`PDF → Vision → Skill → Routing → RAG → Requirement → Decision → Result`

UI-запуск завершается, но **аудит не может надёжно доказать прохождение всей цепочки**, потому что промежуточные данные либо не попадают в конечный result, либо не представлены в сохранённой диагностике так, чтобы связать конкретный candidate с конкретным RAG hit, requirement и decision.

Именно это сейчас является главным предметом проверки.

## 9. Что НЕ надо делать на этом этапе

Пока не следует:

- исправлять Word-отчёт;
- менять формат публичного отчёта ради отображения `unchecked`;
- проектировать Canonical Audit Case;
- внедрять новую Normative Trace architecture;
- добавлять новые hardcoded `if/else` для отдельных проверок;
- повторно гонять весь документ отдельным Vision experiment вне UI;
- считать старый matrix experiment доказательством состояния production RAG.

Причина простая: пока не доказана целостность существующей цепочки, изменения уровня отчёта будут маскировать проблему ниже по pipeline.

## 10. Что именно нужно восстановить следующим этапом

Следующая задача аудита:

**не новая архитектура, а сохранение существующей цепочки в production check.**

Для каждого фактического кандидата должно быть возможно проследить:

`page`
→ `visual candidate`
→ `check_id / Skill`
→ `route`
→ `normative document/version`
→ `RAG query`
→ `retrieved chunks`
→ `normative requirement`
→ `decision`
→ `final result`

При этом необходимо использовать **тот же production UI запуск**, который выбирает:

- модель;
- страницы;
- Skill.

Отдельный Vision experiment для этого не нужен.

## 11. Актуальная матрица проверки Skill

| Check ID | Baseline | JSON 2.0 | Production E2E | Текущий статус |
|---|---|---|---|---|
| `wastewater_flow` | evidence_found / 3 unchecked | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `sewer_diameter` | evidence_found / 2 unchecked | PASS, clause 18.34 | UI E2E trace не подтверждён | **RAG подтверждён отдельно; E2E НЕ ПОДТВЕРЖДЁН** |
| `sewer_slope` | evidence_found / 1 unchecked | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `sewer_ventilation` | evidence_found / 1 violation | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `sewer_outlets` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `sewer_cleanouts` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `sewer_material` | evidence_found / 2 unchecked | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `storm_separation` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `noise_insulation` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `irrigation` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `meters` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `emergency_outlets` | no_evidence_candidate | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |
| `ar_coordination` | evidence_found / 1 compliant / 1 unchecked | не проверялся отдельно | не трассирован | **НЕ ПОДТВЕРЖДЁН** |

## 12. Вывод текущего аудита

На 25.09.2026 нельзя утверждать, что RAG в целом не работает: отдельный реальный кейс `sewer_diameter` доказал работающий retrieval и extraction по актуальному JSON 2.0.

Но также **нельзя утверждать, что RAG полноценно работает в production-проверке документа**.

Текущая проблема аудита сформулирована точнее:

> **Production UI check завершается и выдаёт результаты, но полная цепочка взаимодействия Visual → Skill → Routing → RAG → Requirement → Decision не сохраняется/не прослеживается в достаточном виде для аудита.**

Именно это нужно исправить/проверить прежде, чем переходить к Word-отчёту или Canonical Audit Case.

---

**Следующий практический шаг:** взять один уже выполненный production UI результат от 25.09.2026 и восстановить по нему трассу конкретного результата `unchecked` от страницы и Skill до RAG, normative requirement и decision. Если на каком-то этапе данных нет, фиксируем точное место разрыва и исправляем именно его.
