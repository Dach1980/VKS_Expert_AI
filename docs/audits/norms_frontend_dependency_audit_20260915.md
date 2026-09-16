# Audit: frontend Norms dependency chain

**Date:** 2026-09-15  
**Scope:** `frontend/assets/js/main-page/norms.js` and the currently loaded compatibility modules  
**Repository:** `Dach1980/VKS_Expert_AI`  

## 1. Audit objective

Determine the actual dependency chain around:

```text
norms.js
   ├── who calls loadNorms()
   ├── who calls renderNorms()
   ├── who reads/writes normsData
   └── which version.* fields are used

norms-metadata-fix.js
norms-registry-fix.js
norms-amendment-label-fix-v2.js
```

The audit distinguishes **data/runtime mutations** from **DOM-only corrections** and evaluates what must eventually be moved into the canonical Norms model v2 before compatibility files can be removed.

## 2. Runtime loading confirmed in browser

The browser resource audit showed:

```text
norms.js                         loaded = true
norms-metadata-fix.js            loaded = true
norms-registry-fix.js            loaded = true
norms-amendment-label-fix.js     loaded = false
norms-amendment-label-fix-v2.js  loaded = true
```

`main.js` statically imports the same four active modules in this order:

```js
import './norms.js?v=20260903-2';
import './norms-metadata-fix.js?v=20260903-6';
import './norms-registry-fix.js?v=20260903-4';
import './norms-amendment-label-fix-v2.js?v=20260903-1';
```

The old `norms-amendment-label-fix.js` is physically present in the repository but is not part of the current runtime.

## 3. `norms.js`: primary owner of Norms data and rendering

`norms.js` is the primary implementation, not a compatibility layer.

It:

- initializes/uses `window.normsData`;
- defines `getNormsData()` and `setNormsData()`;
- defines `getNormByIdLocal()`;
- defines `renderNorms()`;
- defines `loadNorms()`;
- fetches `/api/norms`;
- maps API documents into the frontend `normsData` structure;
- maps every API version and normalizes `original_filename` / `filename`;
- renders the cards and version rows;
- implements indexing, activation and deletion interactions.

The API-to-frontend mapping currently creates/uses these document-level fields:

```text
id
number
title
version_id
effective_from
current_change_number
current_change_date
status
processing
versions
raw
```

Each version is copied and currently receives compatibility aliases:

```text
original_filename
filename
```

The rendering code uses version fields including:

```text
version_id / id
document_id
original_filename / filename / file
effective_from
change_date
pages_count
processing.indexing
processing.vector_index
processing.vector_metadata
status
change_number
```

The current implementation also uses `norm.version_id`, `norm.current_change_number` and `norm.title` when constructing the card header.

## 4. Who calls `loadNorms()`

### 4.1 `main.js`

`main.js` is the normal application bootstrap caller:

```js
setTimeout(function(){
    if(window.loadDocs)window.loadDocs();
    if(window.loadNorms)window.loadNorms();
    if(window.loadReports)window.loadReports();
    ...
},100)
```

Therefore the application startup calls the global `window.loadNorms`.

### 4.2 `norms.js` internal calls

`norms.js` itself calls `loadNorms()` after operations that need fresh server state, notably after activating a version and during version/status workflows. Because `norms-registry-fix.js` replaces `window.loadNorms`, these later calls can pass through the registry wrapper depending on which function reference is used at runtime.

### 4.3 `norms-registry-fix.js`

This is the most important dependency mutation. It saves the original function:

```js
var originalLoad = window.loadNorms;
```

and replaces it with:

```js
window.loadNorms = async function (expandIds) {
    var data = await originalLoad(expandIds);
    var normalized = normalize(data);
    window.normsData = normalized;
    if (typeof window.renderNorms === 'function') window.renderNorms();
    ...
    return normalized;
};
```

Thus after installation, the public `window.loadNorms` is a wrapper around the original `norms.js` implementation.

### 4.4 `norms-metadata-fix.js`

It does **not** replace `window.loadNorms` and does not call `loadNorms()` itself. It works against the current `window.normsData` and retries its normalization on a timer because API loading is asynchronous.

## 5. Who calls/owns `renderNorms()`

### Primary owner: `norms.js`

`norms.js` defines the actual renderer and writes `grid.innerHTML` for the complete Norms UI.

### Calls from `norms.js`

The main data-loading and mutation paths call `renderNorms()` after data changes, including the initial `loadNorms()` path and version/indexing state updates.

### Calls from `norms-metadata-fix.js`

When its `normalizeState()` detects a data mutation it calls:

```js
if (changed && typeof window.renderNorms === 'function') window.renderNorms();
```

It also patches already rendered rows directly.

### Calls from `norms-registry-fix.js`

Its `window.loadNorms` wrapper calls `renderNorms()` after replacing `window.normsData` with the normalized registry representation.

### `norms-amendment-label-fix-v2.js`

It does **not** call/replace `renderNorms()`. It waits for the rendered grid and modifies DOM text after rendering. A `MutationObserver` repeats the DOM correction when the grid changes.

## 6. Who reads/writes `window.normsData`

### `state.js`

`state.js` initializes the global runtime state:

```js
var normsData = [];
window.normsData = normsData;
```

It also exposes `getNormById()` using `window.normsData`.

### `norms.js`

Primary read/write owner:

```text
window.normsData
```

`getNormsData()` reads it and `setNormsData()` writes it. `loadNorms()` populates it from `/api/norms`.

### `main.js`

Reads `window.normsData.length` for the navigation badge and calls `window.renderNorms()` when switching to the Norms section.

### `norms-metadata-fix.js`

Reads and mutates `window.normsData` in place. It changes version metadata and document-level derived metadata, and may trigger `renderNorms()`.

### `norms-registry-fix.js`

Reads the result of the original `loadNorms()`, creates a normalized document/version structure and then assigns the new array to:

```js
window.normsData = normalized;
```

### `norms-amendment-label-fix-v2.js`

Does not read/write `window.normsData`. It reads only the rendered DOM.

## 7. `norms-metadata-fix.js`: what it actually changes

This module is substantially more than a visual patch.

It mutates version/document runtime data:

### Version-level mutations

```text
version.change_number
version.status
```

It determines amendment number using a priority chain:

1. PDF filename;
2. explicit base-version marker;
3. existing explicit `change_number`;
4. version id.

It explicitly avoids deriving amendment number from array order or effective dates.

### Document-level mutations

```text
norm.current_change_number
norm.version_id
norm.title
```

It also contains a hard-coded title normalization for:

```text
СП 30.13330.2020
СП 31.13330.2021
СП 32.13330.2018
```

### DOM mutations

It additionally rewrites:

```text
.norm-version-label
.norm-card-title
.norm-card-subtitle
```

Therefore this file currently combines **data compatibility + derived-state correction + DOM correction**.

### What remains necessary after canonical v2

The parts that belong in the target architecture are the semantics, not the compatibility implementation:

- amendment number must come from canonical version metadata derived from the authoritative source filename;
- current version must be represented by canonical version state, not reconstructed repeatedly in the UI;
- canonical document title/number should come from registry/API data rather than frontend hard-coded title mappings.

The following should disappear from the final frontend architecture:

- repeated inference from `version.id`;
- reliance on `version.type`/legacy `file` fields;
- frontend mutation of canonical data after API loading;
- timer-based repeated repair;
- hard-coded title mappings for specific SP numbers.

## 8. `norms-registry-fix.js`: what it actually changes

This module is the runtime registry compatibility layer.

Its `normalize()` function:

1. groups API documents by canonical document number;
2. combines their `versions` arrays;
3. adds `document_id` to versions;
4. adds `version_id` aliases;
5. recalculates amendment numbers from filenames;
6. deduplicates versions using `document_id:version_id`;
7. identifies the current version using `status=current` and `current_selected_by_user=true`;
8. rebuilds document-level `version_id`, `current_change_number`, `effective_from` and `processing`;
9. replaces `window.normsData` with the normalized result;
10. invokes `renderNorms()`.

It also makes the global `window.loadNorms` a wrapper around the original implementation.

### What must move into canonical `norms.js` / API model v2

The following registry responsibilities should eventually be native to the canonical data contract:

- one logical document object per canonical document number;
- a single authoritative `versions[]` collection;
- stable `document_id` / `version_id` semantics;
- canonical current-version selection;
- canonical amendment metadata;
- canonical source filename;
- canonical processing/index metadata.

The grouping/deduplication/reconstruction logic should not remain as a post-load frontend repair layer once the API already returns the canonical registry model.

## 9. `norms-amendment-label-fix-v2.js`: exact problem it fixes

This module is purely a rendered-DOM guard.

It fixes amendment labels when the normal renderer has produced an incorrect or stale label. It:

- reads the filename from `.norm-version-file-name`;
- extracts `Изм.N` / `Изменение №N` / `amendment N` from the filename;
- rewrites `.norm-version-label` to:
  - `Изменение №N · действующая`, or
  - `Изменение №N · архивная`, or
  - `Без изменений ...`;
- rewrites `.norm-card-title` similarly;
- installs a `MutationObserver` so the correction survives subsequent `renderNorms()` calls.

Its own source explicitly describes the PDF filename as authoritative and the guard as a final UI guard.

### Canonical replacement

The target state is:

```text
canonical version metadata
        ↓
renderNorms()
        ↓
correct label on first render
```

rather than:

```text
renderNorms()
        ↓
DOM mutation observer
        ↓
repair label
```

Therefore `norms-amendment-label-fix-v2.js` should be removable after the canonical renderer has been made authoritative and verified against the existing Norms UI tests.

## 10. Current dependency graph

```text
state.js
   │
   └── window.normsData = []

main.js
   │
   ├── imports norms.js
   ├── imports norms-metadata-fix.js
   ├── imports norms-registry-fix.js
   └── imports norms-amendment-label-fix-v2.js
   │
   └── startup → window.loadNorms()

norms.js
   │
   ├── GET /api/norms
   ├── builds window.normsData
   ├── defines renderNorms()
   └── performs UI/version/index actions
   │
   ▼
norms-metadata-fix.js
   │
   ├── mutates version/document metadata
   ├── may call renderNorms()
   └── patches rendered DOM
   │
   ▼
norms-registry-fix.js
   │
   ├── wraps window.loadNorms()
   ├── normalizes/merges/deduplicates registry data
   ├── replaces window.normsData
   └── calls renderNorms()
   │
   ▼
norms-amendment-label-fix-v2.js
   │
   └── DOM-only label/title repair + MutationObserver
```

## 11. Final audit conclusion

There are currently three active compatibility layers around the primary Norms implementation, but they do different jobs:

| File | Runtime role | Data mutation | `loadNorms` mutation | DOM mutation | Final target |
|---|---|---:|---:|---:|---|
| `norms.js` | primary implementation | yes | defines it | yes | keep |
| `norms-metadata-fix.js` | legacy metadata compatibility | **yes** | no | yes | migrate semantics, then remove |
| `norms-registry-fix.js` | registry normalization compatibility | **yes** | **yes** | indirectly | migrate registry contract, then remove |
| `norms-amendment-label-fix-v2.js` | final UI guard | no | no | **yes** | migrate rendering, then remove |

The old `norms-amendment-label-fix.js` is not loaded by the current application and is therefore not part of the runtime dependency chain.

### Important safety conclusion

**Do not delete the active compatibility files yet.** Their behavior is still functionally used by the current runtime.

The next refactoring should be performed in this order:

1. make the API/frontend Norms payload canonical v2;
2. move registry normalization into the canonical data contract;
3. make `norms.js` render canonical amendment/current-version metadata directly;
4. remove metadata-fix and registry-fix imports/files;
5. remove the final amendment-label guard;
6. run the browser regression check and verify that the Norms cards, version list, current-version selection, amendment labels and indexing state remain correct.

No compatibility file should be deleted merely because it appears redundant by name.
