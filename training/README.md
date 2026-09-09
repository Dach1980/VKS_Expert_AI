# Training / Engineering Knowledge

This module is the experimental knowledge layer for Project Expert AI.

## Purpose

The module stores engineering audit datasets, checklists, expert cases and evaluation artifacts. It is intentionally separated from the production checking pipeline.

The first experiment is based on the current VK project and `СП 30.13330.2020`. ТЗ and ТУ will be added in a later experiment after the normative report is stable.

## Principle

Training data is not the same as model fine-tuning. The dataset may be used for prompt engineering, few-shot examples, RAG evaluation, agentic reasoning and, later, possible fine-tuning.

## Current scope — Step 1

Step 1 creates the module structure and a functional UI shell. It does not change Vision, RAG, Checking or Report logic.

## Planned dataset entities

- `engineering_fact` — an observed fact from project documentation.
- `normative_requirement` — a normative requirement with applicability and requirement type.
- `checklist` — an engineering question/check definition.
- `audit_case` — a complete expert-reviewed engineering situation.

## Experiment 001

`training/datasets/experiment_001/` is reserved for the first Golden Dataset based on the current VK project and `СП 30.13330.2020`.

No expert cases are populated yet; schemas are defined before data collection starts.
