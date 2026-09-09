# Step 6 — Experiment 001 Evaluation

## Status

`EXP001-BM-v0` remains a **provisional benchmark**. Step 6 verified the first real Golden decision: `EXP001-G001` is a verified `violation` concerning an outdated normative reference. A verified `compliant` case is still missing, so the benchmark is not yet a complete three-way decision benchmark.

## Current benchmark set

- `EXP001-C001` — `unchecked`: 8.48 м³/сут without a verified applicable requirement.
- `EXP001-C002` — `unchecked`: Ø160 мм K1 without a verified applicable requirement.
- `EXP001-C003` — `unchecked`: Ø110 мм internal domestic sewer outlets without a verified applicable requirement.
- `EXP001-G001` — `violation`: project explicitly cites replaced `СП 30.13330.2012` as the normative basis for an internal wastewater ventilation decision.
- `EXP001-N001` — `unchecked`, negative: `колодец №63` is an object identifier, not a measurement.
- `EXP001-N002` — `unchecked`, negative: a numeric/time fragment without proven applicability must not become a requirement.

## Step 6 rule

A case enters the Golden Dataset only when project evidence, normative requirement, applicability and expert decision are all verified. If a numerical conclusion depends on an unproven condition, the case remains `unchecked`.

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

The benchmark becomes a meaningful three-way decision benchmark only after it contains at least:

- one verified `compliant` case;
- one verified `violation` case.

The second condition is now satisfied by `EXP001-G001`; the first is still open.

## Architecture boundary

Step 6 only verifies and records Training cases. It does **not** modify the production Vision, RAG, Checking or Reporting pipeline.
