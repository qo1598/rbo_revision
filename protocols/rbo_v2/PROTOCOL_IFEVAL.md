# RBO v2 on IFEval-Ko — frozen confirmatory protocol (2026-09-26)

Written after dev tuning and BEFORE any confirm-split RBO/SR output exists. Only single-A.X outputs existed for
11 confirm items (see SPLIT_NOTE.md).

## Data
allganize/IFEval-Ko (342 prompts, official evaluator files unmodified, SHA-256 in LOCK). Split: `SPLIT_IFEVAL.json`
(dev 50 / confirm 292). All numbers below are on confirm only.

## Frozen system: RBO-T2  (`python rbo.py confirm T2 qwen8 ax7 qwen8 qwen8`)
Planner Qwen3-8B (JSON, verbatim-quote guard) -> Generator A.X-4.0-Light 7B -> Checker (generic text tools in code +
Qwen3-8B for non-measurable requirements) -> if any FAIL: Reviser branch [only at-least word/sentence shortfall ->
Extender (A.X) appends; otherwise Qwen3-8B regenerates with failure feedback] -> Checker -> Gate (accept only if
pass count rises and no passed requirement fails); at most 2 rounds. Greedy decoding, Ollama local, max 1280 tokens.
No dataset labels or official scorer inside the pipeline.
Model-to-role assignment rule fixed before dev results of RBO: Generator = best single model on dev strict
(A.X .76 > Qwen3-8B .72 > EXAONE-7.8B .58); Planner/Checker = Qwen3-8B. Reviser = Qwen3-8B was chosen on dev
(reviser replay, `replay_reviser.py`), which is disclosed as a dev design choice.

## Comparators (confirm)
single A.X (official prompt), single Qwen3-8B, Self-Refine A.X (2 rounds), GPT-4o-2024-11-20 (official prompt,
temperature 0, max 1280 tokens) for attainment.

## Primary endpoint
Prompt-level strict accuracy (official). Secondary: instruction-level strict, prompt/instruction loose, tokens, calls.

## Hypotheses (two-sided exact McNemar, Holm over H1-H2, alpha .05)
- H1: RBO-T2 != single A.X (expected RBO higher).
- H2: RBO-T2 != Self-Refine A.X.
Secondary/descriptive: vs single Qwen3-8B; attainment = RBO / GPT-4o with paired bootstrap 95% CI (10,000, seed
20260926); gate counterfactual (first-round candidates accepted without gate) computed from stored traces.
A nonsignificant result is reported as such, not as equivalence.
