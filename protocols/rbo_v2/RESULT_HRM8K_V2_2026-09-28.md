# RBO v2 on HRM8K-GSM8K — confirmatory result (2026-09-28)
Protocol `PROTOCOL_MATH_QA.md`, lock `MATHQA_LOCK.json` (no drift), `analyze_mathqa.py hrm8k` -> `HRM8K_CONFIRM_RESULT.json`.
Confirm n = 400; numeric answer accuracy. Run paused by the user once (sc3 at 260/400) and resumed from journals.

| System | acc | % of GPT-4o |
|---|---|---|
| GPT-4o-2024-11-20 | .923 | — |
| RBO v2 (Qwen3-8B P/C/R, A.X G) | .885 | 95.9% (95% CI 93.0-98.9) |
| single Qwen3-8B | .880 | 95.4% |
| SC3 A.X | .875 | 94.9% |
| Self-Refine A.X | .850 | 92.1% |
| single A.X | .848 | 91.9% |
| RBO v2, submitted models (Midm P/C, HCX R) | .818 | 88.6% |

Primary (exact McNemar, Holm): H1 vs single A.X 30W/15L, p .036, p_holm .071 — not supported after correction;
H2 vs SC3 24W/20L, p_holm .65 — not supported. Secondary: vs Qwen3-8B 20/18 (p .87); vs GPT-4o 8/23 (p .011, RBO lower);
submitted-model RBO vs single A.X 19/31 (p .12). Consistent with the pre-confirm prediction (no reliable gain; boundary).
