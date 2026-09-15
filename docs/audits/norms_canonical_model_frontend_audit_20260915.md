# Точечный аудит модуля «Нормы»: canonical model v2 и подключение JS

**Дата:** 2026-09-15  
**Проект:** Project Expert AI  
**Репозиторий:** `Dach1980/VKS_Expert_AI`

## 1. Итог аудита

Модуль «Нормы» находится в переходном состоянии между legacy metadata и canonical model v2.

Главный вывод: **`frontend/index.html` напрямую подключает только `main.js`; все compatibility-файлы модуля «Нормы» входят в runtime только через imports `main.js`.**

Подготовительный порядок работ остаётся:

```text
app/api/norms.py
app/api/norm_files.py
frontend «Нормы»
        ↓
canonical model v2
        ↓
1 контрольный PDF
        ↓
полная переиндексация 15 PDF
```

Production RAG/FAISS/`SPIndexBuilder`/semantic parser/chunk builder/embedding builder/normative router/Qwen в рамках этого аудита не меняются.

---

## 2. Backend: `app/api/norms.py`

В upload-flow остаются legacy-участки:

- `effective_from` автоматически заполняется через `date.today().isoformat()`;
- в Registry передаётся legacy `effective_from`;
- используется `_classify_uploaded_filename()`;
- вручную записываются `type`, `change_number`, `change_date`, `pages_count`, `sha256`, `original_filename`;
- duplicate detection использует `original_filename` / `file`;
- GET `/api/norms/{document_id}` реконструирует legacy metadata.

Цель patch: `filename → parse_normative_filename() → canonical edition/source/index → Registry v2`, без искусственного `date.today()` и без записи legacy-полей в Registry.

---

## 3. File API: `app/api/norm_files.py`

Найден legacy-доступ:

```python
version.get("file", "")
```

Целевой источник:

```python
(version.get("source") or {}).get("file", "")
```

---

## 4. Frontend: `norms.js`

Основной UI пока ожидает legacy metadata:

```text
version.effective_from
version.change_number
version.change_date
version.pages_count
processing.vector_index
processing.vector_metadata
version.original_filename / version.filename
```

Целевой canonical API:

```text
version.edition.date
version.edition.amendment.number
version.source.file
version.index.pages_count
```

`norms.js` также содержит собственную интерпретацию amendment из имени файла. После перехода на canonical model она должна исчезнуть там, где canonical metadata уже доступна.

---

## 5. Точный runtime-порядок из `frontend/index.html`

В `frontend/index.html` находится **один** JavaScript entry point:

```html
<script type="module" src="./assets/js/main-page/main.js?v=20260901-7"></script>
```

Следовательно, compatibility-файлы не подключаются отдельными `<script>`-тегами.

`main.js` импортирует модули в таком порядке:

```javascript
import './state.js?v=20260902-3';
import './utils.js?v=20260902-3';
import './dashboard.js?v=20260902-3';
import './norms.js?v=20260903-2';
import './norms-metadata-fix.js?v=20260903-6';
import './norms-registry-fix.js?v=20260903-4';
import './norms-amendment-label-fix-v2.js?v=20260903-1';
import './documents.js?v=20260907-2';
import './checks.js?v=20260902-3';
import './reports.js?v=20260908-1';
import './settings.js?v=20260902-3';
import './skills.js?v=20260907-2';
import './training.js?v=20260910-3';
```

Для «Нормы» runtime-chain:

```text
frontend/index.html
        ↓
main.js
        ↓
norms.js
        ↓
norms-metadata-fix.js
        ↓
norms-registry-fix.js
        ↓
norms-amendment-label-fix-v2.js
```

---

## 6. Судьба четырёх compatibility-файлов

| Файл | Есть | Импортируется `main.js` | Реально исполняется через `index.html` |
|---|---:|---:|---:|
| `norms-metadata-fix.js` | Да | **Да** | **Да** |
| `norms-registry-fix.js` | Да | **Да** | **Да** |
| `norms-amendment-label-fix.js` | Да | **Нет** | **Нет** |
| `norms-amendment-label-fix-v2.js` | Да | **Да** | **Да** |

### Фактический вывод

**Из четырёх compatibility-файлов три исполняются, один нет.**

Исполняются:

1. `norms-metadata-fix.js`
2. `norms-registry-fix.js`
3. `norms-amendment-label-fix-v2.js`

Не исполняется:

4. `norms-amendment-label-fix.js`

`norms-amendment-label-fix.js` — legacy-файл, не входящий в текущий module graph `frontend/index.html → main.js`.

---

## 7. Что делает каждый активный compatibility-файл

### `norms-metadata-fix.js`

Исполняется сразу после `norms.js`. Разбирает amendment из filename, использует legacy metadata как fallback, нормализует `window.normsData` и запускает повторные проходы через `setInterval`.

### `norms-registry-fix.js`

Исполняется следующим. Группирует версии по document number и **оборачивает `window.loadNorms()`**. После оригинального `loadNorms()` повторно нормализует данные и вызывает `renderNorms()`.

Следовательно, этот compatibility layer влияет не только на DOM, но и на результат `loadNorms()`.

### `norms-amendment-label-fix-v2.js`

Последний активный compatibility-файл. После `DOMContentLoaded` ждёт `#normsGrid`, патчит labels и устанавливает `MutationObserver` для повторного исправления UI.

---

## 8. Архитектурный вывод

Сейчас frontend фактически содержит несколько самостоятельных механизмов интерпретации одной и той же нормативной metadata:

```text
canonical/backend data
        ↓
     norms.js
        ↓
metadata compatibility
        ↓
registry compatibility
        ↓
amendment UI guard
        ↓
       DOM
```

Compatibility-код продолжает работать с legacy-полями:

```text
original_filename
filename
file
change_number
effective_from
type
```

Поэтому переход на canonical model v2 нельзя считать завершённым только на уровне RegistryManager.

---

## 9. Минимальный patch-план

### A. `app/api/norms.py`

1. Использовать `parse_normative_filename()`.
2. Формировать `document_number`, `version_id`, `edition.date`, `edition.amendment.number`, `source.file`.
3. Не использовать `date.today()` как нормативную дату.
4. Не записывать legacy `type/change_number/change_date/effective_from` в Registry.
5. Перевести duplicate detection на `source.file`.
6. GET API вернуть canonical metadata.

### B. `app/api/norm_files.py`

Перевести `version.file` на `version.source.file`.

### C. `frontend/assets/js/main-page/norms.js`

Перевести чтение metadata на `edition/source/index` и убрать дублирующее толкование amendment из filename.

### D. Compatibility layer

Сначала:

1. canonical patch;
2. один контрольный PDF;
3. проверка API payload;
4. проверка Registry;
5. проверка physical storage;
6. проверка index metadata;
7. проверка UI.

Только после PASS решать, какие compatibility-файлы удалить.

`norms-amendment-label-fix.js` сейчас не участвует в runtime и может быть удалён **отдельным cleanup-коммитом после контрольного теста**, а не в рамках миграционного patch.

---

## 10. Контрольный сценарий

```text
1 контрольный PDF СП 30.13330.2020
        ↓
Нормы → загрузка
        ↓
parse_normative_filename()
        ↓
canonical Registry v2
        ↓
source.file + sha256
        ↓
index
        ↓
metadata.json
        ↓
UI «Нормы»
```

После PASS — полная переиндексация **15 PDF** текущего набора:

```text
СП 30.13330.2020 — 6 PDF
СП 31.13330.2021 — 3 PDF
СП 32.13330.2018 — 6 PDF
-------------------------
Всего — 15 PDF
```

---

## 11. Git-статус

Этот документ фиксирует аудит и **не изменяет production-код**.

Следующий шаг: минимальный canonical patch в `app/api/norms.py`, `app/api/norm_files.py` и `frontend/assets/js/main-page/norms.js`, затем контрольный upload/index одного PDF.
