# Gramax — Improvement Card v0.1

**Status:** IDEA / PLANNED

## Source

Research material supplied for Project Expert AI review: Gramax automatic structural chunking for RAG.

## Problem

Normative PDFs contain headings, clauses, tables, formulas and semantic blocks. Naive fixed-size chunking can separate a requirement from its qualifier, formula or table context.

## Gramax approach

The useful idea to evaluate is structure-aware chunking: preserve document structure and semantic boundaries when creating retrieval units instead of relying only on character/token windows.

## What may be useful for Project Expert AI

- preserve clause boundaries;
- keep headings attached to their content;
- preserve formula context;
- preserve table context;
- improve retrieval precision for normative requirements;
- retain page/location metadata for auditability.

## Applicability

Potentially high for normative knowledge indexing. It must be adapted to Russian regulatory documents and must not break version metadata, formulas, tables or evidence locations.

## Proposed implementation

1. Define a benchmark set of normative questions and expected clauses.
2. Implement a structure-aware chunking variant alongside the current `DocumentChunkBuilder`.
3. Rebuild a separate vector index for the variant.
4. Run the same benchmark against current and experimental chunking.
5. Compare retrieval recall, citation/clause accuracy and downstream audit metrics.

## Risks

- chunks may become too large;
- semantic grouping can accidentally cross clause boundaries;
- formula/table context may be duplicated;
- improved retrieval can increase context size and latency.

## Acceptance criterion

Do not replace the current chunker solely on qualitative inspection. Promote the variant only when benchmark evidence demonstrates a meaningful improvement without unacceptable latency or traceability regressions.