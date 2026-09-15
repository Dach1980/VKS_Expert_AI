# Root-cause audit: `sewer_diameter` routed to `external_wastewater`

**Date:** 2026-09-15  
**Project:** Project Expert AI  
**Repository:** `Dach1980/VKS_Expert_AI`  
**Case:** production `report.json`, finding `id=5`, `check_id=sewer_diameter`  
**Status:** confirmed root cause; production code is **not changed** by this audit.

## Why this document exists

This is the canonical bookmark for the confirmed routing bug found during the production-chain audit. Future work on this case should start here before changing the router, RAG, or Qwen prompt.

## Confirmed causal chain

```text
Vision candidate
  -> project evidence explicitly says "внутренней самотечной бытовой канализации"
  -> app/rag/normative_router.py::_is_external()
  -> substring "внутриплощад" matches external_terms
  -> external=True
  -> route_candidate() returns scope=external_wastewater
  -> filter_retrievers() permits СП 32.13330.2018
  -> retrieve_audit_context() retrieves external-wastewater chunks
  -> СП 32.13330.2018 §6.3.5 enters normative context
  -> select_normative_requirements() ranks the concrete numeric clause highly
  -> Qwen receives Ø110 mm vs 1000 mm
  -> violation is produced
```

## Exact root cause

`app/rag/normative_router.py::_is_external()` currently treats the substring `"внутриплощад"` as an unconditional external-network indicator:

```python
external_terms = (
    "наружн",
    "внутриплощад",
    "колодец",
    "от колодца",
    "до точки подключения",
    "сети нк",
    "сети нв",
)
```

The saved project evidence contains:

> Бытовые стоки отводятся системой внутренней самотечной бытовой канализации по пяти выпускам Ø110мм в внутриплощадочную сеть бытовой канализации Ø160 мм.

The checked object is the **internal wastewater outlet Ø110 mm**. The phrase `в внутриплощадочную сеть` describes the destination/boundary context and must not, by itself, reclassify the checked object as an external wastewater segment.

## What is and is not the root cause

| Component | Finding |
|---|---|
| Vision | No evidence that Vision invented the internal/external classification; the candidate contains explicit internal-wastewater evidence. |
| `_is_external()` | **Root cause.** `внутриплощад` causes `external=True`. |
| `route_candidate()` | Propagates the wrong boolean into `external_wastewater`. |
| `filter_retrievers()` | Downstream executor of the wrong route; not the root cause. |
| `retrieve_audit_context()` | Correctly searches the wrongly scoped retrievers. |
| `select_normative_requirements()` | Amplifies a concrete but inapplicable requirement; not the first cause. |
| Qwen | Receives contaminated normative context; prompt already contains an instruction not to mix internal and external systems. |
| Numeric comparison | `110 < 1000` is mathematically correct; the normative requirement is the wrong one. |
| `report.json` | Preserves the upstream error; it does not create it. |

## Expected routing for this saved candidate

```text
system = wastewater
segment = internal
scope = internal_wastewater
allowed normative document for sewer_diameter = СП 30.13330.2020
```

The false production requirement `СП 32.13330.2018 §6.3.5` must therefore be outside the scoped normative retrievers and cannot enter the Qwen normative context.

## Deterministic A/B experiment

The companion experiment is:

`training/evaluation/experiment_sewer_diameter_route_ab_20260915.py`

It does **not** change production routing or the Qwen prompt. It compares the current deterministic classifier with an experiment-only corrected classifier on the exact saved `sewer_diameter` candidate and checks the normative-document gate.

Expected/observed result:

| | Current production logic | Experiment-only corrected logic |
|---|---|---|
| scope | `external_wastewater` | `internal_wastewater` |
| segment | `external` | `internal` |
| allowed SP | СП 32.13330.2018 | СП 30.13330.2020 |
| СП 32 §6.3.5 allowed into Qwen context | yes | **no** |

The experiment result is stored in:

`training/evaluation/experiment_sewer_diameter_route_ab_20260915_result.json`

## Important boundary

This audit does **not** authorize or imply a production code fix. The next production change should be a separate minimal patch to routing, followed by the same A/B test against the saved candidate and inspection of the resulting Qwen input before any broader RAG changes.
