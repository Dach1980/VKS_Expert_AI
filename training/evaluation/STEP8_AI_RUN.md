# Step 8 — AI Engineer benchmark run

## Purpose

Run Qwen against Experiment 001 without exposing the expected Golden decisions. The model receives project evidence plus the candidate normative requirement pool and must independently determine applicability and decision.

## Input boundary

The runner does **not** send `expected_decision`, `negative_case`, or Golden reasoning to Qwen. Those values are used only after the model response to calculate metrics.

## Model

Default model: `qwen3.5-9b`

The model can be overridden with `--model`.

## LM Studio

Start the selected Qwen model in LM Studio and make the OpenAI-compatible API available at:

`http://127.0.0.1:1234/v1`

## Run from repository root

```powershell
python training/evaluation/run_experiment_001.py --model qwen3.5-9b
```

If the loaded LM Studio model uses another identifier:

```powershell
python training/evaluation/run_experiment_001.py --model <loaded-model-id>
```

The result is saved to:

`training/evaluation/experiment_001_run_latest.json`

## What is measured

- `decision_accuracy`
- `false_violation_rate`
- applicability field validity
- evidence trace completeness
- critical failure: any `violation` predicted for N001 or N002

## Interpretation

The first run is an engineering experiment, not a production quality claim.

A wrong `violation` on a negative case is treated as a critical failure even if overall accuracy is high.

The Golden Dataset files remain immutable evaluation references; the AI run output is stored separately.

## Next step after the first run

Inspect every case individually, especially:

- G001 — outdated normative reference
- G002 — compliant material
- G003 — conditional applicability / insufficient roof evidence
- N001 — generic project identifier
- N002 — semantically similar but non-proven normative context

Only after this inspection should we decide whether to change the AI Engineer prompt, knowledge representation, or applicability architecture.
