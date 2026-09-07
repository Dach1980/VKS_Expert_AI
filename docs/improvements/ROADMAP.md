# Improvements Roadmap

## v0.1

- Evaluate structure-aware chunking based on the Gramax approach.
- Remove hard-coded normative context from `ContextBuilder`.
- Consolidate embedding rebuild paths.
- Consolidate canonical chunking path.
- Record runtime embedding dimension in index metadata.

## v0.2

- Evaluate stronger hybrid retrieval (BM25 + dense retrieval).
- Evaluate a reranker where benchmark evidence justifies the added latency.
- Expand benchmark coverage across Skills, normative versions and models.

## v1.x architectural candidates

- Project-document semantic index where justified by benchmark results.
- Graph-based retrieval if it demonstrably improves cross-reference and normative navigation tasks.
- Administrative AI evaluation/benchmark interface.

No roadmap item is considered implemented until it has code, tests and benchmark evidence.