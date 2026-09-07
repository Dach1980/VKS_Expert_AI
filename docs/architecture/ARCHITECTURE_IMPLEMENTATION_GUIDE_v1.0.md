# Project Expert AI — Architecture & Implementation Guide v1.0

**Status:** ACCEPTED BASELINE  
**Version:** 1.0  
**Date:** 2026-09-07  
**Scope:** architecture and implementation state of the repository at the time of documentation.

> This document is a factual architecture snapshot. `CURRENT` describes implemented repository behavior; `LEGACY` describes retained/older paths; `PLANNED` describes future work and must not be mistaken for implemented functionality.

## 1. Purpose

Project Expert AI is a local AI-assisted engineering-document audit system. The initial domain is ВК (водоснабжение и канализация), with planned expansion to КР, АР, ЭОМ and other disciplines.

The core design is not a generic `PDF → embeddings → RAG → LLM` chatbot. The implemented system is an expert audit pipeline in which Skills define what must be checked, Vision extracts project evidence, deterministic routing limits applicable normative sources, RAG retrieves evidence, requirements are structured, numeric rules are compared deterministically, and the result is reported with audit evidence.

## 2. Architectural principles

1. **Knowledge Base ≠ RAG ≠ Skill ≠ Evaluation.**
2. **Normative source selection precedes broad retrieval.**
3. **LLM output is not the sole authority for numeric compliance.**
4. **Every finding should remain auditable:** project page/evidence, normative source/version/clause, values and comparison must be traceable.
5. **Versioning is first-class:** one logical normative document may contain multiple versions/changes; retrieval is performed against the selected version.
6. **Local-first execution:** LM Studio provides local embedding and chat/vision model APIs.
7. **Future improvements must be recorded separately from the current architecture.**

## 3. System layers

```text
PROJECT DOCUMENTS
      │
      ▼
VISION / PROJECT FACT EXTRACTION
      │
      ▼
SKILL
what must be checked
      │
      ▼
NORMATIVE ROUTER
which normative documents are applicable
      │
      ▼
RAG / RETRIEVAL
semantic + lexical + formula-aware ranking
      │
      ▼
NORMATIVE REQUIREMENT
clause / requirement / value / unit
      │
      ▼
DETERMINISTIC COMPARISON
      │
      ▼
LLM DECISION / EXPLANATION
      │
      ▼
AUDIT FINDING + EVIDENCE + REPORT
```

## 4. Normative knowledge pipeline — CURRENT

```text
Regulatory PDF
  ↓
PDF page processing
  ↓
Structure parsing / enrichment
  ↓
Formula extraction and recognition
  ↓
DocumentChunkBuilder
  ↓
embedding_text
  ↓
LM Studio Embedding API
  ↓
text-embedding-nomic-embed-text-v1.5
  ↓
FAISS IndexFlatIP
  ├── index.faiss
  ├── vectors.npy
  └── metadata.json
```

The current chunk builder is `app/knowledge/document_chunk_builder.py`. It creates `text` and `formula_context` chunks. Formula context combines nearby text with recognized LaTeX and adds engineering metadata such as ВК, internal water supply and hydraulic calculation.

Storage is version-aware:

```text
vector_index_root/
└── document_id/
    └── version_id/
        ├── pages/
        ├── enriched/
        ├── document_chunks/
        └── embeddings/
```

The repository also contains older/experimental chunking and embedding paths. They are **LEGACY/EXPERIMENTAL**, not the canonical architecture.

## 5. Embeddings — CURRENT

The embedding model is separate from the chat/vision model. `app/rag/embedding_client.py` calls the OpenAI-compatible LM Studio endpoint `http://localhost:1234/v1` and uses model `text-embedding-nomic-embed-text-v1.5`.

```text
chunk.embedding_text
      ↓
EmbeddingClient
      ↓
LM Studio
      ↓
text-embedding-nomic-embed-text-v1.5
      ↓
float vector
```

The client itself reports vector dimension by measuring a generated vector in its demo. The repository snapshot does **not** hard-code a dimension in architecture configuration; therefore the exact dimension must be treated as runtime/model metadata rather than invented in this document.

The current implementation clearly generates embeddings for the normative retrieval index. The repository does not establish a canonical second embedding index for project-document pages; project-document visual analysis is primarily handled by the checking pipeline.

## 6. Vector store — CURRENT

FAISS is the current vector store. The active retriever uses `faiss.IndexFlatIP`. Query and stored vectors are L2-normalized before search, making inner product equivalent to cosine similarity for normalized vectors.

Persistent artifacts are `index.faiss`, `vectors.npy` and `metadata.json` under the selected document/version storage path.

ChromaDB and Graph-RAG concepts may exist in research/experimental material, but they are **not** the current production retrieval store.

## 7. RAG pipeline — CURRENT

```text
USER / CHECKING REQUEST
        ↓
query
        ↓
query embedding
        ↓
FAISS semantic retrieval
        ↓
lexical candidates
        ↓
formula-aware candidates when relevant
        ↓
ranking
        ↓
context
        ↓
LLM
```

The current retriever is a deterministic hybrid-style implementation, but not a full BM25+dense+cross-encoder stack.

`Retriever.search()` performs:
- dense FAISS retrieval;
- lexical terminology scoring;
- formula-specific scoring for formula-oriented queries;
- merging and ranking of candidates.

The lexical component uses normalized tokens and domain-specific boosts, for example for pipe diameter terminology. It is not a dedicated BM25 engine.

## 8. Audit-specific retrieval — CURRENT

`app/rag/audit_retrieval.py` adds engineering context before retrieval.

```text
Visual candidate
      ↓
Skill / normative routing
      ↓
Allowed normative retrievers only
      ↓
Primary audit query
      ↓
Retrieval
      ↓
Concrete-clause check
      ↓
Fallback query only when necessary
      ↓
Value / keyword / numeric / unit relevance
      ↓
Ranked normative context
```

This design deliberately avoids embedding every possible fallback query for every candidate. A second query is used only when the first retrieval does not expose a concrete normative clause.

## 9. Normative routing — CURRENT

`app/rag/normative_router.py` performs deterministic routing from a project fact to an allowed set of normative SPs. The current ВК skill distinguishes internal/external and water/wastewater contexts and filters retrievers accordingly.

The router is conservative: it does not invent a normative source. Ambiguous facts can fall back to the skill's cross-boundary source set, after which requirement selection must establish applicability.

## 10. Skill system — CURRENT

A Skill is an expert specification, not merely a prompt. The registry defines, among other things:

- `what_to_find`
- `fact_types`
- `parameters`
- `systems`
- `segments`
- `normative_documents`
- `requirement_type`
- `numeric_comparison`
- `evidence_required`
- `violation_when`
- `compliant_when`
- `unchecked_when`

The current repository contains a `vk_wastewater` skill with checks such as flows, diameters, slopes, ventilation, outlets, cleanouts, materials and system separation.

## 11. Vision / project checking pipeline — CURRENT

```text
Project PDF
  ↓
Render page
  ↓
Vision model
  ↓
Visual candidates
  ├── check_id
  ├── parameter
  ├── project_value
  ├── evidence_text
  ├── bbox
  └── confidence
  ↓
Skill filtering / selection
  ↓
Normative Router
  ↓
Audit Retrieval
  ↓
Normative Requirement
  ↓
LLM decision / explanation
  ↓
Deterministic numeric comparison where applicable
  ↓
Audit finding
  ↓
Evidence image
  ↓
Report
```

The intended optimization is one Vision pass per page producing reusable candidates, rather than one Vision call for every individual Skill check.

## 12. Normative requirement extraction — CURRENT

`app/rag/normative_requirement.py` transforms retrieved chunks into auditable structured requirements:

```text
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
```

Concrete clause-bearing and numeric requirements receive higher selection priority than generic text fragments.

This is a key distinction between generic RAG and an auditable engineering RAG: retrieval is not the final answer; retrieved text must become a structured normative requirement before comparison.

## 13. Deterministic engineering comparison — CURRENT

Numeric compliance must not depend exclusively on an LLM. When a Skill declares numeric comparison, engineering values are normalized and compared using deterministic logic. This supports conclusions such as `project value 100 mm < required 110 mm` without asking the LLM to perform the authoritative arithmetic.

The LLM remains useful for interpretation, explanation and cases where deterministic comparison is not applicable.

## 14. Context construction — CURRENT / TECHNICAL DEBT

`ContextBuilder` converts retrieved results into LLM-ready text and has a special path for formula contexts.

The current formula formatter contains proof-of-concept hard-coded references to `СП 30.13330.2020` and a specific section. This is a documented technical-debt item: production context must be fully derived from version-aware retrieval metadata rather than hard-coded normative text.

## 15. LM Studio roles — CURRENT

```text
LM Studio
 ├── Embedding API
 │     └── text-embedding-nomic-embed-text-v1.5
 │             ↓
 │          FAISS
 │
 └── Chat / Vision API
       └── selected local Qwen / compatible model
```

Changing the chat/vision model should not require rebuilding the normative embedding index. Changing the embedding model does require rebuilding compatible vector indexes.

## 16. Knowledge versioning — CURRENT

The registry treats one logical regulation as one document with versions/changes. Retrieval resolves the requested document and version, and defaults to the current version when no explicit version is supplied.

The version-aware retriever exposes both version ID and a human-readable version label in results.

## 17. Checking job / resilience — CURRENT

The checking subsystem supports background execution, page limits for controlled test runs, progress tracking and retry/checkpoint concepts. Limited runs preserve the full document page count and mark the scope as limited so test results cannot be mistaken for full-document audits.

Operational statuses include queued/preparing/visual/normative/retry/completed/error. Progress can expose completed pages, average processing time and estimated remaining time.

## 18. Current vs legacy vs planned

| Area | State | Current implementation |
|---|---|---|
| Normative PDF parsing | CURRENT | Page processing + structure/enrichment pipeline |
| Formula recognition | CURRENT | Formula extraction/recognition integrated into enrichment/chunking |
| Canonical chunking | CURRENT | `DocumentChunkBuilder` |
| Older formula chunk builder | LEGACY | Retained experimental path |
| Embedding service | CURRENT | LM Studio embedding API |
| Embedding model | CURRENT | `text-embedding-nomic-embed-text-v1.5` |
| Vector store | CURRENT | FAISS `IndexFlatIP` |
| Version-aware index | CURRENT | document/version storage paths |
| Dense retrieval | CURRENT | FAISS |
| Lexical retrieval | CURRENT | deterministic token scoring |
| Formula retrieval boost | CURRENT | formula-aware ranking |
| BM25 engine | PLANNED | not current |
| Cross-encoder reranker | PLANNED | not current |
| Normative router | CURRENT | deterministic skill-based routing |
| Requirement extraction | CURRENT | structured parser/selector |
| Numeric comparison | CURRENT | deterministic engineering comparison |
| Hard-coded ContextBuilder norm | TECH DEBT | must be removed |
| Graph-RAG | PLANNED/EXPERIMENTAL | not current vector architecture |
| ChromaDB | EXPERIMENTAL | not current vector store |
| AI benchmark administration | PLANNED | target evaluation layer |
| Fine-tuning / training | FUTURE | not part of v1.0 runtime architecture |

## 19. AI Evaluation & Training Administration — TARGET ARCHITECTURE

The benchmark model is:

```text
SKILL → REFERENCE → TEST CASE → MODEL → COMPARISON → SCORE
```

Project Expert AI should eventually compare:
- different chat/vision models;
- different RAG implementations;
- different chunking strategies;
- different embedding models;
- different prompts/configurations.

Core metrics:
- accuracy;
- precision;
- recall;
- citation accuracy;
- hallucination rate;
- false-positive rate;
- false-negative rate.

The target administrative surface is `/admin/ai` with sections for Models, Knowledge, Skills, References, Test Cases, Runs, Results, Logs and Benchmark.

A canonical run should preserve the expected result and actual result together with raw logs/evidence so that a score is reproducible rather than manually asserted.

## 20. Documentation architecture

```text
PROJECT EXPERT AI
 ├── ARCHITECTURE — как работает
 ├── IMPROVEMENTS — что изменить
 └── TESTS/EVALUATION — как проверить качество AI
```

Recommended repository documentation:

```text
docs/
├── architecture/
│   ├── README.md
│   └── ARCHITECTURE_IMPLEMENTATION_GUIDE_v1.0.md
├── improvements/
│   ├── README.md
│   ├── ROADMAP.md
│   ├── CHANGELOG.md
│   └── v0.1/
│       └── gramax.md
└── testing/
    └── README.md
```

The existing root `tests/` remains the place for technical unit/integration tests. `docs/testing/` describes AI evaluation methodology and benchmark design.

## 21. Improvements lifecycle

Improvements are tracked independently from architecture versions:

```text
IDEA → PLANNED → IN PROGRESS → IMPLEMENTED → TESTED → ACCEPTED
```

The intended evidence chain is:

```text
Problem
  → Improvement
  → Implementation
  → Test
  → Benchmark
  → Result
  → New architecture version
```

## 22. Gramax as an improvement candidate

The Gramax research belongs under `improvements/`, not in the current architecture. Its card should describe the source, problem addressed, Gramax approach, potentially useful mechanisms, applicability to Project Expert AI, proposed implementation, risks and status.

The key architectural question is whether structure-aware/semantic chunking can improve normative retrieval without destroying clause boundaries, formulas, tables, version metadata or audit traceability.

## 23. Embedding documentation requirements

Any future embedding change must record:

1. exact model name;
2. vector dimension as verified at runtime;
3. what text becomes a vector;
4. preprocessing;
5. chunking rules;
6. metadata;
7. storage format;
8. similarity metric;
9. index version/rebuild requirement;
10. whether embeddings are used for normative knowledge, project documents, or both.

## 24. RAG change requirements

Any future RAG implementation must explicitly document:

```text
request
 → query
 → query embedding
 → retrieval
 → candidates
 → filtering
 → ranking
 → context
 → prompt
 → LLM
 → response
```

Every stage must be labeled `CURRENT`, `LEGACY`, `EXPERIMENTAL` or `PLANNED`.

## 25. Benchmark reference model

The evaluation system should separate four concepts:

- **Knowledge:** what the model can access through the normative knowledge base/RAG;
- **Skill:** what the expert system requires it to check;
- **Reference:** authoritative expected evidence/requirement/decision;
- **Evaluation:** how close the actual run is to the reference.

Training/fine-tuning is a later capability and must not be conflated with RAG configuration or benchmark evaluation.

## 26. Architecture versioning

Architecture documentation versions describe the system architecture, not the LLM version.

- `Architecture Documentation v1.0` — first accepted architecture snapshot.
- `v1.1` — minor architectural/documentation changes.
- `v2.0` — major architecture change.

Model versions, RAG variants, chunking variants and benchmark runs are independent dimensions.

## 27. Immediate technical-debt priorities

1. Remove hard-coded normative content from `ContextBuilder`.
2. Declare one canonical embedding rebuild path and mark alternatives legacy/experimental.
3. Declare one canonical chunk builder and isolate the older implementation.
4. Ensure all normative context is version-aware.
5. Record runtime embedding dimension in index metadata.
6. Separate structural normative JSON indexes from vector retrieval indexes in documentation and code naming.
7. Keep benchmark/evaluation artifacts independent from production checking logic.

## 28. Definition of Done for the v1 architecture

The v1 architecture is considered documented when a developer can answer, from the repository documentation alone:

- what enters the system;
- how normative PDFs become chunks;
- what is embedded and with which model;
- where vectors are stored;
- how retrieval works;
- how applicable SPs are selected;
- how a project fact becomes a normative requirement;
- where deterministic comparison occurs;
- how evidence reaches the final finding/report;
- which parts are current, legacy or planned;
- how AI quality will be benchmarked.

This document is the accepted architecture baseline for subsequent implementation and improvement work.