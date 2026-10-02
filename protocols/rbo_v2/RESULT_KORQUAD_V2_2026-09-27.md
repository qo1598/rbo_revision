# RBO v2 on KorQuAD 1.0 — confirmatory result (2026-09-27)
Protocol `PROTOCOL_MATH_QA.md`, lock `MATHQA_LOCK.json` (no drift), `analyze_mathqa.py korquad` -> `KORQUAD_CONFIRM_RESULT.json`.
Confirm n = 900, pinned whole-answer EM.

| System | EM | % of GPT-4o |
|---|---|---|
| RBO v2 (Qwen3-8B P/C/R, A.X G) | **.762** | 101.2% (95% CI 97.6-105.0) |
| RBO v2, submitted models (Midm P/C, HCX R, A.X G) | .727 | 96.5% |
| single A.X | .707 | 93.8% |
| SC3 A.X | .701 | 93.1% |
| Self-Refine A.X | .702 | 93.2% |
| single Qwen3-8B | .662 | 87.9% |
| GPT-4o-2024-11-20 | .753 | — |

Primary (exact McNemar, Holm): H1 vs single A.X 80W/30L, p_holm 2.0e-6; H2 vs SC3 84W/29L, p_holm 4.4e-7. Both supported.
Secondary: vs Qwen3-8B 163/73 (p 4.5e-9); vs Self-Refine 84/30 (p 4.3e-7); vs GPT-4o 84/76 (p .58, not a parity claim);
submitted-model RBO vs single A.X 50/32 (p .060, not significant).
Note: the bank was used earlier by the RBO-S study; no RBO v2 design decision used confirm items.
