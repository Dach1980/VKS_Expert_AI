# Normative RAG Pipeline Audit — 2026-09

**Project:** Project Expert AI  
**Repository:** `Dach1980/VKS_Expert_AI`  
**Audit type:** read-only architecture / data-flow audit  
**Audit scope:** Registry → selected current version → storage paths → source PDF → parsed/pages → enriched pages → chunks → embeddings → Retriever → production RAG  
**Audit date:** 2026-09  
**Production changes during audit:** none

---

## 1. Purpose

This document records the actual normative-document pipeline found in the repository so that the pipeline can be reconstructed later without relying on memory or assumptions.

The audit was performed before any production correction of normative versioning or canonical requirement linkage.

The main question was: **why does the production check of СП 30.13330 currently use the base version, and where is Изменение №5 lost?**

### Main conclusion

The current production RAG is technically version-aware, but the Registry currently contains only the base version of СП 30.13330. That base version is marked as the selected current version. Therefore every downstream version-aware stage correctly follows the Registry and ultimately uses the base PDF and embeddings built from it.

**Изменение №5 is not lost inside PageEnricher, FAISS, or Retriever. It is absent from the Registry/version-ingestion layer before the indexing pipeline starts.**

---

## 2. Actual production chain

The current chain is:

```text
knowledge/registry/documents.json
        │
        ▼
DocumentRegistry.get_current_version()
        │
        ▼
SP_30.13330_2020_base
        │
        ▼
KnowledgeStorage.paths(document_id, version_id)
        │
        ├── source PDF
        ├── parsed JSON
        ├── structured JSON
        ├── pages/
        ├── enriched/
        ├── document_chunks/
        └── embeddings/
                ├── index.faiss
                └── metadata.json
        │
        ▼
PDFPageProcessor
        │
        ▼
page_*.json
        │
        ▼
PageEnricher
        │
        ▼
page_*_enriched.json
        │
        ▼
DocumentChunkBuilder
        │
        ▼
all_chunks.json
        │
        ▼
EmbeddingBuilder
        │
        ▼
FAISS + metadata.json
        │
        ▼
Retriever(document_id, version_id)
        │
        ▼
production RAG retrieval
        │
        ▼
select_normative_requirements()
        │
        ▼
LLM audit decision
```

The production checker obtains normative versions through `_indexed_norms()` in `app/checking/resilient.py`. It calls `storage.get_current_version()` and then constructs a `Retriever` for that exact version.

---

## 3. Registry: why base is currently selected

The current Registry record for `SP_30.13330` contains the base version as the available/current version.

Conceptually the current state is:

```text
SP_30.13330
└── SP_30.13330_2020_base
    type: base
    status: current
    current_selected_by_user: true
    file: СП_30.13330_базовая_версия.pdf
```

There is no separate Registry version representing **Изменение №5**.

`DocumentRegistry.get_current_version()` selects a version only when both conditions are true:

```python
status == "current"
current_selected_by_user is True
```

Therefore the Registry deterministically resolves:

```text
СП 30.13330
        ↓
SP_30.13330_2020_base
```

This is not a Retriever bug and not an accidental fallback in FAISS. It is the expected result of the current Registry state.

---

## 4. Where Изменение №5 is absent

The loss occurs at the **normative version registry / ingestion boundary**.

The repository does not currently represent Изменение №5 as a separately registered normative version for СП 30.13330. Consequently there is no version-specific PDF path, parsed tree, structured tree, enriched pages, chunks, or embeddings for that amendment participating in the current selected-version chain.

The downstream stages therefore receive:

```text
SP_30.13330_2020_base
        ↓
СП_30.13330_базовая_версия.pdf
```

rather than an amendment-inclusive/current version.

### Important distinction

The absence of Изменение №5 in the Registry is the **primary defect**.

The fact that downstream artifacts are based on `base` is a **consequence** of that Registry state.

---

## 5. Storage and source PDF

`KnowledgeStorage.paths(document_id, version_id)` resolves paths from the selected Registry version. It does not independently decide which PDF is current.

The selected version therefore determines the concrete source PDF used by the indexing pipeline.

For the current СП 30 state the effective source is:

```text
knowledge/regulations/SP_30.13330/СП_30.13330_базовая_версия.pdf
```

This path is then consumed by `PDFPageProcessor`.

`PDFPageProcessor` opens the resolved PDF with PyMuPDF and creates page-level JSON containing text blocks, page geometry, source PDF path, document ID, and version.

Therefore the base PDF enters the pipeline **before** PageEnricher.

---

## 6. PageEnricher: actual role

`app/knowledge/page_enricher.py` creates:

```text
page_*_enriched.json
```

Its input is the already extracted page representation:

```text
pages/page_*.json
```

plus optional formula artifacts under the formula work area.

PageEnricher normalizes/enriches page blocks and creates embedding-oriented text/context. It is not responsible for deciding which normative version is current.

It also does not currently read the semantic `structured/*.json` representation and does not create canonical normative requirements.

Therefore PageEnricher must be understood as a **physical/page-level enrichment stage**, not as a normative semantic interpretation stage.

### Consequence

If the input PDF is the base PDF, PageEnricher cannot recover or add content from Изменение №5 by itself.

The amendment must already be represented by the selected source/version before this stage.

---

## 7. `structured` → `enriched/chunks` is currently disconnected

The indexing builder runs both structural parsing and page enrichment:

```text
PDF
 ├──> PDFPageProcessor ──> pages ──> PageEnricher ──> enriched
 │                                             │
 │                                             ▼
 │                                      DocumentChunkBuilder
 │                                             │
 │                                             ▼
 │                                      all_chunks.json
 │                                             │
 │                                             ▼
 │                                      EmbeddingBuilder
 │                                             │
 │                                             ▼
 │                                      embeddings
 │
 └──> StructureParser ──> structured/*.json
```

The two branches originate from the same PDF but are not subsequently joined.

`DocumentChunkBuilder` reads the enriched page files, not the structured clause tree. Consequently the current chunk/embedding pipeline does not automatically inherit semantic clause identity from `structured`.

This is an important architectural gap because `structured` already provides a useful semantic hierarchy such as:

```text
section → clause → clause text → source page(s)
```

while the embedding branch currently operates mainly on page/block text.

---

## 8. `clause` is not the same thing as `canonical requirement`

A `structured.clause` represents a structural unit of the source normative document.

It does **not** automatically represent the final semantic checking object required by Project Expert AI.

A canonical requirement may need additional information such as:

```text
requirement_id
requirement_type
norm / document identity
version identity
clause
system
segment
object
parameter
condition
exception
normative value
normative unit
applicability rules
source provenance
```

Therefore the following equivalence is unsafe:

```text
structured.clause == canonical requirement
```

The correct conceptual model is:

```text
STRUCTURED CLAUSE
        │
        ▼
CANONICAL REQUIREMENT
        │
        ├── requirement_id
        ├── scope
        ├── condition
        ├── exception
        ├── requirement_type
        └── semantic checking fields
```

A stable canonical requirement ID should therefore be introduced at a dedicated semantic normalization stage rather than generated opportunistically by Retriever or PageEnricher.

Experiment-local IDs such as `EXP001-R001` must remain benchmark IDs and must not become production canonical IDs.

---

## 9. Current `knowledge/index` sequential IDs are not canonical IDs

`app/knowledge/normative_index.py` currently produces an index from structured clauses, but its generated IDs are sequential entries.

Such an ID is an index position, not a stable semantic identity.

For example, an ID equivalent to:

```text
1
2
3
...
```

must not be treated as the production `requirement_id`.

A production canonical identity must remain stable across indexing runs and must be tied to the semantic normative requirement, not merely its current position in a generated list.

---

## 10. Retriever and FAISS are downstream consumers, not version selectors

`app/rag/retriever.py` is explicitly version-aware.

It receives `document_id` and `version_id`, resolves the corresponding storage paths, and opens that version's:

```text
embeddings/index.faiss
embeddings/metadata.json
```

Therefore Retriever does not independently select `base`.

The important distinction is:

```text
Registry selects version
        ↓
Storage resolves paths
        ↓
Indexing builds embeddings for that version
        ↓
Retriever reads embeddings for that version
```

This means fixing the amendment problem at the Retriever level would be the wrong architectural layer.

---

## 11. Legacy `document_enricher.py`

`app/knowledge/document_enricher.py` contains a separate older artifact-building path with hard-coded values equivalent to:

```python
DOCUMENT = "СП 30.13330.2020"
VERSION = "base"
PDF_PATH = ".../СП_30.13330_базовая_версия.pdf"
```

This is a versioning hazard.

Even after Registry/version ingestion is corrected, this legacy component can continue to create artifacts explicitly tied to the base version.

It should therefore be treated as **legacy / non-authoritative** until its role is deliberately removed, replaced, or made version-aware.

No such change is made by this audit.

---

## 12. Known architectural shortcomings

### NORM-RAG-001 — amendment-complete current version is not represented

**Severity:** high

The Registry does not currently represent Изменение №5 as part of the selected current normative version of СП 30.13330.

**Effect:** production RAG can be technically correct while retrieving from an outdated/incomplete normative basis.

---

### NORM-RAG-002 — legacy hard-coded base enricher

**Severity:** medium/high

`app/knowledge/document_enricher.py` hard-codes `VERSION = "base"` and the base PDF.

**Effect:** parallel/legacy processing can create artifacts that contradict the Registry-based version model.

---

### NORM-RAG-003 — structured semantic branch is not connected to embedding chunks

**Severity:** high for future canonical requirement work

`structured` is generated, but the current chunk/embedding path is based on enriched page data and does not automatically propagate structured clause identity.

**Effect:** canonical semantic requirement identity cannot currently be reliably propagated from structured knowledge into RAG metadata without an explicit joining stage.

---

### NORM-RAG-004 — clause identity is not canonical requirement identity

**Severity:** high for future expert reasoning

A clause is a structural source unit, while a canonical requirement is a semantic checking unit.

**Effect:** assigning requirement IDs directly to arbitrary chunks or clause index positions risks unstable or semantically incorrect identities.

---

### NORM-RAG-005 — version correctness is not yet an explicit invariant of the final RAG artifact

**Severity:** high

The pipeline is version-aware in code, but there is not yet a sufficiently explicit end-to-end invariant proving that the selected current version, its PDF, parsed/structured artifacts, chunks, and embeddings all correspond to exactly the same version.

**Effect:** stale or cross-version artifacts could become difficult to detect if directories are reused or generated by legacy paths.

---

## 13. Future corrections — NOT TO BE APPLIED BY THIS AUDIT

The following are architectural recommendations only. They are deliberately **not implemented** in this commit.

### FUTURE-01 — make Registry amendment-aware

Represent the actual normative history of СП 30.13330, including the required amendment/version information, as explicit Registry records.

The Registry should make it possible to distinguish:

```text
base
amendment №N
edition
current selected version
```

The exact data model must be designed and approved before implementation.

---

### FUTURE-02 — establish one authoritative version-selection path

All normative indexing must start from the Registry-selected version and its resolved source PDF.

Legacy hard-coded PDF/version paths should eventually be removed or isolated from the authoritative pipeline.

---

### FUTURE-03 — introduce an explicit semantic normalization stage

Create a controlled stage conceptually between `structured` and embedding/chunk generation:

```text
structured clause
      ↓
semantic normalization
      ↓
canonical requirement
      ↓
requirement_id
      ↓
chunk metadata
      ↓
embeddings
```

This stage should be responsible for semantic requirement identity, not PageEnricher.

---

### FUTURE-04 — propagate canonical requirement provenance into RAG metadata

Once canonical requirements exist, their stable IDs and provenance should be propagated into chunks and ultimately `embeddings/metadata.json`.

Retriever should preserve the identity rather than invent it.

`normative_requirement.py` should consume/preserve that identity when transforming RAG results into production requirement objects.

---

### FUTURE-05 — add version-consistency validation

Before a normative index becomes production-usable, validate that:

```text
Registry version
      == PDF version
      == parsed version
      == structured version
      == enriched version
      == chunks version
      == embeddings version
```

A mismatch should fail indexing rather than silently produce a mixed-version knowledge base.

---

### FUTURE-06 — explicitly validate amendment coverage

For a current normative version with amendments, indexing should eventually provide a machine-checkable statement of what source material is included.

For example:

```text
Document: СП 30.13330.2020
Current version: ...
Included amendments: [№1, №2, ..., №5]
Source PDF(s): ...
```

The exact representation remains to be designed.

---

### FUTURE-07 — retire or isolate legacy `document_enricher.py`

After the authoritative version-aware pipeline is confirmed, the legacy hard-coded builder should either be removed, clearly marked as legacy, or refactored to use the same Registry/Storage version contract.

---

## 14. What must NOT be changed as a consequence of this audit

This audit does **not** authorize or implement changes to:

- production `resilient.py`;
- Retriever behavior;
- evaluator logic;
- benchmark EXP001;
- applicability experiments;
- PageEnricher;
- canonical requirement IDs;
- Registry contents;
- current normative PDF files;
- RAG index contents;
- production Skills;
- LLM prompts.

Those changes require separate design/approval and controlled implementation/testing.

---

## 15. Recommended implementation order for a future cycle

The recommended order is:

```text
1. Confirm normative source/version model
        ↓
2. Register actual current СП 30 version + amendment coverage
        ↓
3. Rebuild parsed/structured/enriched/chunks/embeddings
        ↓
4. Verify version consistency end-to-end
        ↓
5. Design structured clause → canonical requirement normalization
        ↓
6. Introduce stable requirement_id
        ↓
7. Propagate requirement_id into chunks/embeddings/RAG
        ↓
8. Add applicability resolver to production checking
        ↓
9. Re-run controlled benchmarks
```

This ordering intentionally puts **normative source/version correctness before canonical requirement and applicability work**.

---

## 16. Audit conclusion

The current СП 30 production behavior is now explained by the repository's actual data flow:

```text
Registry has only base
        ↓
base is marked current
        ↓
Storage resolves base
        ↓
base PDF is indexed
        ↓
base pages are enriched
        ↓
base chunks are embedded
        ↓
Retriever reads base embeddings
        ↓
production RAG uses base
```

Therefore the primary correction is **not** to Retriever or PageEnricher.

The first architectural problem to solve in a future approved change is the **normative version/Registry model and the explicit inclusion of Изменение №5**. Only after that is verified should the project connect structured clauses to canonical requirements and propagate stable requirement identity into RAG.

This document is intended to serve as the recovery reference for that future work.
