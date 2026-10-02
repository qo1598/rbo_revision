# RBO v2 on IFEval-Ko — ablations and assignment generalization (2026-09-27)

Protocol `PROTOCOL_IFEVAL_EXT.md` (+ amendments 1-2), lock `IFEVAL_EXT_LOCK_A2.json` (no drift), analysis
`analyze_ext.py` -> `IFEVAL_EXT_RESULT.json`. Confirm n = 292, prompt-level strict, exact McNemar.

## E1 role ablations (P/C/R = Qwen3-8B, G = A.X)
| Configuration | strict | vs single A.X (W/L, p) | full RBO-T2 vs this (W/L, p) |
|---|---|---|---|
| single A.X | .723 | — | 37/8, 1.5e-5 |
| Planner + Generator only | .757 | 19/9, .087 | 20/1, 2.1e-5 |
| LLM-only Checker (no tools, regenerate) | .753 | 19/10, .136 | 20/0, 1.9e-6 |
| Tools, single edit-style Reviser (no branch) | .781 | 25/8, .0046 | 16/4, .012 |
| RBO-T2 (tools + failure-type branch) | .822 | 37/8, 1.5e-5 | — |

## E2 submitted models in RBO v2 roles (Midm P/C, HCX R, A.X G)
.767 vs single A.X .723: 20W/7L, p = .019.

## E3 homogeneous assignment (all roles = m) vs single m
| m | single | RBO | gain | W/L | p (Holm) | Checker unparsable (/292) |
|---|---|---|---|---|---|---|
| Qwen3-1.7B | .486 | .555 | +6.8 | 40/20 | .013 (.067) | 24 |
| Qwen3-4B | .692 | .767 | +7.5 | 32/10 | .0009 (.0066) | 13 |
| Qwen3-8B | .726 | .791 | +6.5 | 31/12 | .0054 (.032) | 3 |
| EXAONE-3.5-2.4B | .637 | .616 | -2.1 | 24/30 | .50 (.99) | 68 |
| Midm-2.0-Mini 2.3B | .705 | .654 | -5.1 | 16/31 | .040 (.12) | 188 |
| HyperCLOVA 3B | .568 | .565 | -0.3 | 25/26 | 1.0 (1.0) | 120 |
| EXAONE-3.5-7.8B | .620 | .747 | +12.7 | 46/9 | 4e-7 (3.5e-6) | 39 |
| A.X-4.0-Light 7B | .723 | .774 | +5.1 | 25/10 | .017 (.067) | 48 |
Positive gains 5/8 (sign test p = .73). Holm-significant: Qwen3-4B, Qwen3-8B, EXAONE-7.8B.

## Reading (confirmatory vs exploratory)
- Confirmatory: every orchestration component adds over its ablation; the submitted-model configuration improves on
  single A.X; RBO improves 5 of 8 models when every role is the same model (3 Holm-significant).
- Not supported: "any sLM can fill every role" (3 of 8 show no gain or a loss; sign test ns).
- Exploratory (post hoc, not tested): the three non-gaining models are the three 2-3B Korean-specialized models, which
  also have the highest Checker output failure (68-188 of 292) and lower plan-conditioned drafts; Qwen3-1.7B, despite
  its size, gains. Role competence (structured output / requirement analysis) rather than size alone is the candidate
  explanation; it needs its own prespecified test.
