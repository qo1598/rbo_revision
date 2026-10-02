# RBO v2 on HRM8K-GSM8K (math) and KorQuAD 1.0 (extractive QA) — frozen confirmatory protocol (2026-09-27)

Written after dev tuning and BEFORE any confirm output. Same role order as IFEval-Ko RBO-T2
(Planner -> Generator -> Checker(tools + LLM) -> branch Reviser -> Gate, <= 2 rounds), task-specific role contents in
`rbo_math.py` and `rbo_qa.py`. Local Ollama, greedy (SC samples 2-3 at temperature 0.7, fixed seeds).

## Data and splits
- HRM8K GSM8K subset (HAERAE-HUB/HRM8K `HRM8K/gsm8k_test.csv`, 1,319): `SPLIT_HRM8K.json` dev 50 / confirm 400
  (salted SHA-256 order). Metric: numeric answer equals gold (relative tolerance 1e-6).
- KorQuAD 1.0 validation bank (`rbo_s_v1/bank_korquad.jsonl`, 950 contexts, previously used by the RBO-S study):
  `SPLIT_KORQUAD.json` dev 50 / confirm 900. Metric: pinned whole-answer EM (same scorer as RBO-S).

## Dev record (disclosed design choices)
- HRM8K: first reviser 0.82 vs single A.X 0.84; code-aware reviser (program shown, 2048 tokens) 0.84. Adopted; no
  further tuning. Prediction before confirm: no reliable gain (boundary candidate).
- KorQuAD: RBO 0.76 vs single A.X 0.60, SC3 0.60, SR 0.60, GPT-4o 0.62 (dev, n=50). No design change after dev.

## Systems (confirm, both tasks)
single A.X; single Qwen3-8B; SC3 A.X (3 samples, majority, ties -> greedy sample; compute-comparable control);
Self-Refine A.X; RBO v2 (P=C=R=Qwen3-8B, G=A.X); RBO v2 with submitted models (P=C=Midm-2.3B, R=HCX-3B, G=A.X);
GPT-4o-2024-11-20 reference with the single-model prompt.

## Hypotheses per task (two-sided exact McNemar, Holm over H1-H2 within task)
H1 RBO v2 vs single A.X; H2 RBO v2 vs SC3 A.X. Secondary: vs Qwen3-8B, vs Self-Refine, submitted-model RBO vs single
A.X, attainment vs GPT-4o (paired bootstrap 10,000, seed 20260927). Nonsignificance is not equivalence.
