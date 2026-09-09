# Step 5 — Experiment 001 Benchmark

## Status

`EXP001-BM-v0` is a **provisional benchmark**. It is intentionally not presented as a complete Golden decision benchmark because Step 4 did not verify a true `compliant` or `violation` case from the available evidence.

## What is measured

The benchmark checks whether the AI Engineer:

1. preserves the distinction between a project fact and an audit decision;
2. proves normative applicability before using a requirement;
3. returns `unchecked` when evidence is insufficient;
4. does not convert project identifiers into engineering measurements;
5. does not create a violation from a semantically similar but physically unrelated normative fragment.

## Current benchmark set

- `EXP001-C001` — `unchecked`: 8.48 м³/сут without a verified applicable requirement.
- `EXP001-C002` — `unchecked`: Ø160 мм K1 without a verified applicable requirement.
- `EXP001-C003` — `unchecked`: Ø110 мм internal domestic sewer outlets without a verified applicable requirement.
- `EXP001-N001` — `unchecked`, negative: `колодец №63` is an object identifier, not a measurement.
- `EXP001-N002` — `unchecked`, negative: a numeric/time fragment without proven applicability must not become a requirement.

## Critical rule

Any `violation` prediction for either negative case is a benchmark failure.

## Metrics

Primary:

- decision accuracy;
- false violation rate.

Additional:

- unsupported-violation rate;
- unchecked precision/recall;
- normative applicability accuracy;
- evidence trace completeness.

## Golden gate

The benchmark becomes a meaningful three-way decision benchmark only after Step 4 adds at least:

- one verified `compliant` case;
- one verified `violation` case.

Until then, `unchecked` is an intentional expected outcome, not a missing label.

## Architecture boundary

Step 5 only defines the evaluation contract and dataset. It does **not** modify the production Vision, RAG, Checking or Reporting pipeline.
