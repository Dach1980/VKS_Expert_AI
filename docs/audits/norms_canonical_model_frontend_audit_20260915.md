# Точечный аудит модуля «Нормы»: canonical model v2 и подключение frontend JS

**Дата:** 2026-09-15  
**Проект:** Project Expert AI  
**Репозиторий:** `Dach1980/VKS_Expert_AI`

## 1. Цель аудита

Проверить текущее состояние перехода модуля «Нормы» на canonical model v2 и точно установить, какие JavaScript-файлы модуля «Нормы» реально исполняются при загрузке `frontend/index.html`, в каком порядке и какие compatibility-файлы фактически остаются неиспользуемыми.

Аудит является подготовительным этапом перед минимальным patch-планом:

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

Архитектура индексации, RAG, FAISS, `SPIndexBuilder`, semantic parser, chunk builder, embedding builder, normative router и Qwen в рамках этого аудита не изменяются.

---

## 2. Итог предыдущего аудита backend/frontend

### `app/api/norms.py`

Текущий upload-flow всё ещё смешивает старую и новую модели.

Обнаружены следующие legacy-участки:

- `effective_from` автоматически заполняется через `date.today().isoformat()`;
- в `RegistryManager.register_version()` передаётся legacy-поле `effective_from`;
- после сохранения PDF вызывается `_classify_uploaded_filename()`;
- затем в объект версии вручную записываются `type`, `change_number`, `change_date`, `pages_count`, `sha256`, `original_filename`;
- duplicate detection использует `original_filename` / `file` вместо canonical `source.file`;
- GET `/api/norms/{document_id}` реконструирует legacy-поля `version_type`, `effective_from`, `change_number`, `change_date`, `filename`.

### `app/api/norm_files.py`

Осталась прямая работа с legacy-полем:

```python
version.get("file", "")
```

Целевой источник должен быть:

```python
(version.get("source") or {}).get("file", "")
```

### `frontend/assets/js/main-page/norms.js`

Основной UI модуля «Нормы» пока ожидает часть legacy-полей:

- `version.effective_from`;
- `version.change_number`;
- `version.change_date`;
- `version.pages_count`;
- `processing.vector_index`;
- `processing.vector_metadata`;
- `version.original_filename` / `version.filename`.

Кроме того, `norms.js` содержит собственную логику отображения amendment-информации из имени файла.

Целевой frontend должен читать canonical model:

```text
version.edition.date
version.edition.amendment.number
version.source.file
version.index.pages_count
```

при сохранении текущего UX.

---

## 3. Точный порядок загрузки JS из `frontend/index.html`

### 3.1. Что реально подключено непосредственно в `frontend/index.html`

`frontend/index.html` содержит **только один JavaScript entry point**:

```html
<script type="module" src="./assets/js/main-page/main.js?v=20260901-7"></script>
```

Следовательно, четыре compatibility-файла **не подключаются напрямую из HTML**. Они могут исполняться только через импорт из `main.js`.

Это важно: искать отдельные `<script>`-теги для `norms-metadata-fix.js`, `norms-registry-fix.js` и `norms-amendment-label-fix*.js` в `index.html` не нужно.

---

## 4. Реальный import-chain

Текущий `frontend/assets/js/main-page/main.js` содержит следующие side-effect imports в указанном порядке:

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

### Фактическая последовательность для модуля «Нормы»

```text
frontend/index.html
        │
        ▼
main.js
        │
        ├── norms.js
        │
        ├── norms-metadata-fix.js
        │
        ├── norms-registry-fix.js
        │
        └── norms-amendment-label-fix-v2.js
```

Именно эти три compatibility-файла реально входят в module graph и исполняются при загрузке `main.js`.

---

## 5. Судьба четырёх compatibility-файлов

| Файл | Есть в репозитории | Импортируется `main.js` | Исполняется через `frontend/index.html` | Роль |
|---|---:|---:|---:|---|
| `norms-metadata-fix.js` | Да | **Да** | **Да** | legacy metadata normalization / amendment fallback |
| `norms-registry-fix.js` | Да | **Да** | **Да** | regrouping версии по canonical document number + wrapper `loadNorms()` |
| `norms-amendment-label-fix.js` | Да | **Нет** | **Нет** | старый UI guard для amendment labels |
| `norms-amendment-label-fix-v2.js` | Да | **Да** | **Да** | актуальный Cyrillic-safe UI guard для amendment labels |

### Вывод

Из четырёх compatibility-файлов **три реально исполняются**, один — нет:

```text
ИСПОЛНЯЮТСЯ:
1. norms-metadata-fix.js
2. norms-registry-fix.js
3. norms-amendment-label-fix-v2.js

НЕ ИСПОЛНЯЕТСЯ:
4. norms-amendment-label-fix.js
```

`norms-amendment-label-fix.js` является неиспользуемым legacy-файлом в текущем entry point.

---

## 6. Что происходит внутри import-chain

### Шаг 1 — `norms.js`

Сначала загружается основной модуль «Нормы». Он объявляет UI/state/API-функции, включая `loadNorms()` и `renderNorms()`.

### Шаг 2 — `norms-metadata-fix.js`

Сразу после `norms.js` запускается compatibility layer метаданных.

Он:

- разбирает amendment из filename;
- умеет использовать legacy metadata как fallback;
- нормализует `window.normsData`;
- запускает повторные проходы через `setInterval`;
- может изменять отображение карточек и строк версий.

Это означает, что этот файл уже является самостоятельным слоем интерпретации нормативных версий поверх основного UI.

### Шаг 3 — `norms-registry-fix.js`

Следующим запускается registry compatibility layer.

Он:

- группирует версии по document number;
- объединяет несколько API-элементов в одну logical Norms card;
- оборачивает `window.loadNorms`;
- после оригинального `loadNorms()` нормализует результат;
- вызывает `renderNorms()`.

То есть этот compatibility layer влияет не только на отображение, но и на результат `loadNorms()`.

### Шаг 4 — `norms-amendment-label-fix-v2.js`

Последним из трёх активных compatibility-файлов запускается UI guard.

Он:

- ждёт `DOMContentLoaded`, если документ ещё загружается;
- ждёт появления `#normsGrid`;
- патчит labels карточек;
- устанавливает `MutationObserver` на `#normsGrid`;
- повторно исправляет labels при изменении DOM.

Таким образом, текущая схема содержит несколько независимых механизмов, которые повторно интерпретируют одну и ту же нормативную metadata.

---

## 7. Важное архитектурное наблюдение

Текущий frontend имеет следующую цепочку:

```text
canonical/backend data
        ↓
 norms.js
        ↓
 norms-metadata-fix.js
        ↓
 norms-registry-fix.js
        ↓
 norms-amendment-label-fix-v2.js
        ↓
 DOM
```

При этом часть compatibility-кода всё ещё использует legacy-поля:

```text
original_filename
filename
file
change_number
effective_from
type
```

Следовательно, переход на canonical model v2 нельзя считать завершённым только потому, что RegistryManager уже хранит canonical structure.

Основная проблема сейчас — **frontend всё ещё имеет собственную legacy-нормализацию нормативных версий**.

---

## 8. Что НЕ следует делать на этом этапе

Не следует сейчас:

- удалять все compatibility-файлы одновременно;
- менять `SPIndexBuilder`;
- менять FAISS/RAG;
- менять semantic parser;
- менять embedding pipeline;
- менять `normative_router`;
- менять Qwen prompt;
- добавлять новый Applicability Resolver;
- добавлять Graph RAG.

Сначала нужно перевести основной backend/frontend на canonical model v2 и доказать работоспособность на одном контрольном PDF.

---

## 9. Минимальный patch-план

### Этап A — backend

`app/api/norms.py`:

1. `filename` → `parse_normative_filename()`.
2. Получить canonical:
   - `document_number`;
   - `version_id`;
   - `edition.date`;
   - `edition.amendment.number` при наличии;
   - `source.file`.
3. Не подставлять `date.today()` как нормативную дату.
4. Не записывать legacy `type/change_number/change_date/effective_from` в Registry.
5. Duplicate detection перевести на `source.file`.
6. GET API возвращает canonical metadata.

### Этап B — file API

`app/api/norm_files.py`:

```python
version.get("source", {}).get("file", "")
```

вместо legacy `version.get("file", "")`.

### Этап C — frontend

`norms.js`:

- читать `edition.date`;
- читать `edition.amendment.number`;
- читать `source.file`;
- читать `index.pages_count`;
- убрать собственную интерпретацию amendment из filename там, где canonical metadata уже доступна.

### Этап D — compatibility layer

После перевода `norms.js` на canonical model:

1. проверить UI на одном PDF;
2. проверить API payload;
3. проверить Registry;
4. проверить physical storage;
5. проверить index metadata;
6. только после PASS определить, какие compatibility-файлы можно удалить.

`norms-amendment-label-fix.js` уже сейчас не подключён и не исполняется через `frontend/index.html`, поэтому его нельзя считать частью runtime-path.

Удаление этого файла должно быть отдельным cleanup-коммитом после контрольного теста, а не частью canonical migration patch.

---

## 10. Контрольный сценарий после patch

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

Проверить одновременно:

- Registry содержит только canonical model;
- нет искусственного `date.today()`;
- amendment/date взяты из filename;
- UI не требует legacy fields;
- index связан с конкретной `version.id`;
- документ корректно отображается как действующая редакция.

После PASS выполняется полная переиндексация 15 PDF:

```text
СП 30.13330.2020 — 5 PDF
СП 31.13330.2021 — 3 PDF
СП 32.13330.2018 — 6 PDF
-------------------------
Всего — 14 PDF
```

Если в рабочем наборе учитывается отдельный контрольный PDF вне этих трёх групп, его считать отдельно; количество файлов перед массовым запуском должно быть подтверждено фактическим каталогом.

---

## 11. Git/репозиторный статус аудита

Документ создан как отдельная запись аудита и **не меняет production-код**.

Следующий технический шаг — выполнить минимальный canonical patch в `app/api/norms.py`, `app/api/norm_files.py` и `frontend/assets/js/main-page/norms.js`, после чего провести контрольный upload/index одного PDF.
