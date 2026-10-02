# RBO v2 on IFEval-Ko — prespecified extension: ablations and model-assignment generalization (2026-09-26)

Written after the confirm result of the locked RBO-T2 (RESULT_IFEVAL_2026-09-26.md) and BEFORE any output below.
Same confirm split (292), official evaluator, greedy decoding, local Ollama. The RBO-T2 code path is unchanged;
`rbo.py` gained only the L2 ablation branch; `common.py` maps `qwen4` to the original hybrid Qwen3-4B
(`qwen3:4b-q4_K_M`; the `qwen3:4b` tag is the 2507 thinking-only model and was removed before use).

## E1 Role ablations (locked assignment P=C=R=Qwen3-8B, G=A.X)
- A_plan  : Planner + Generator only (the draft stored in RBO-T2 traces; no new run).
- A_L2    : Checker without tools (Qwen3-8B judges every requirement); Reviser regenerate only (extend needs tools).
- A_T1    : tools on, but no failure-type branch (single edit-style Reviser prompt, Qwen3-8B).
Reported descriptively with exact McNemar vs RBO-T2 and vs single A.X.

## E2 Original-submission models in the RBO v2 roles
G = A.X-4.0-Light 7B (submitted Generator), Planner and Checker = Midm-2.0-Mini 2.3B (submitted Critiquer),
Reviser = HyperCLOVA 3B (submitted Reviser); Extender = G. Compared with single A.X (exact McNemar).

## E3 Homogeneous generalization: every role filled by the same model m, compared with single m
m in {Qwen3-1.7B, Qwen3-4B, Qwen3-8B, EXAONE-3.5-2.4B, Midm-2.0-Mini-2.3B, HyperCLOVA-3B, EXAONE-3.5-7.8B,
A.X-4.0-Light-7B} (fixed list, no model dropped after seeing results; a model whose run fails technically is
reported as failed, not omitted). Per model: gain = RBO_m - single_m (prompt strict), exact McNemar, Holm over the 8.
Summary: number of models with positive gain and a two-sided sign test over models; gain vs parameter count is
descriptive only (8 points, no causal claim).
Run order (fixed): A_L2, E2, E3[qwen4, qwen1.7, qwen8, exaone2, midm2, hcx3, exaone8, ax7], A_T1.

## Amendment 1 (2026-09-26, during E2/E3, before those runs completed)
Two technical crashes: (a) E2 Planner (Midm) returned `reqs` as plain strings -> AttributeError at item 237;
(b) E3 Qwen3-4B produced degenerate output and Ollama returned HTTP 500 after 3 retries. Fix (robustness only):
non-dict Planner entries are dropped; a failed model call returns "" and is logged with `error` in `calls`
(consequences listed in code). Neither path occurred in the locked RBO-T2/L2 confirm runs, whose outputs are unchanged.
Crashed runs resume from their journals. Lock refreshed as IFEVAL_EXT_LOCK_A1.json.

## Amendment 2 (2026-09-26 evening)
The single Qwen3-1.7B run crashed at item 143 on an Ollama HTTP 500 (same failure as in Amendment 1). `run_single.py`
now applies the same rule as RBO: a failed call yields an empty answer (scored as failure) and the error is logged.
The crashed run resumes from its journal (queued at the end of run_ext.sh). Lock: IFEVAL_EXT_LOCK_A2.json.
