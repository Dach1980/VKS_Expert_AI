# AI Testing & Evaluation

This directory documents **AI quality methodology**, not ordinary software tests.

## Benchmark model

```text
SKILL → REFERENCE → TEST CASE → MODEL → COMPARISON → SCORE
```

## Evaluation dimensions

- accuracy
- precision
- recall
- citation accuracy
- hallucination rate
- false-positive rate
- false-negative rate

## What a test case should preserve

A test case should identify the Skill, project input/evidence, expected normative source/version/clause or expected decision, model/RAG configuration, actual output, evidence and logs.

## Technical tests vs AI evaluation

- Root `tests/`: unit/integration/regression tests for code.
- `docs/testing/`: methodology for evaluating retrieval and expert decisions.
- Benchmark results must be reproducible and configuration-aware.

## Future administration

Target UI: `/admin/ai` with Models, Knowledge, Skills, References, Test Cases, Runs, Results, Logs and Benchmark.

Training/fine-tuning is a separate future capability. It must not be conflated with RAG configuration or evaluation.