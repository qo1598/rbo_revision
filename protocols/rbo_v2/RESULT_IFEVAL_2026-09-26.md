# RBO v2 (RBO-T2) on IFEval-Ko — confirmatory result (2026-09-26)

Protocol `PROTOCOL_IFEVAL.md`, lock `IFEVAL_LOCK.json` (no drift), analysis `analyze_ifeval.py` ->
`IFEVAL_CONFIRM_RESULT.json`. Confirm split n = 292 prompts. Official IFEval-Ko evaluator.

| System | prompt strict | prompt loose | inst strict | mean calls | mean output tokens |
|---|---|---|---|---|---|
| RBO-T2 (Qwen3-8B P/C/R, A.X G) | **.822** | .846 | .866 | 3.51 | 580 |
| single A.X-4.0-Light 7B | .723 | .753 | .776 | 1 | 272 |
| single Qwen3-8B | .726 | .760 | .793 | 1 | 386 |
| Self-Refine A.X (2 rounds) | .729 | .757 | .780 | 2.33 | 478 |
| GPT-4o-2024-11-20 | .767 | .801 | .829 | 1 | — |

Primary (exact McNemar, Holm): H1 RBO-T2 vs single A.X 37W/8L, p_holm = 3.1e-5; H2 vs Self-Refine 35W/8L,
p_holm = 4.2e-5. Both supported. Difference vs single A.X +9.9 pp, 95% bootstrap CI [+5.8, +14.4].
Secondary: vs single Qwen3-8B 44W/16L (p = .0004); vs GPT-4o 35W/19L (p = .040); single A.X vs GPT-4o 20W/33L
(p = .098). Attainment vs GPT-4o: RBO-T2 107.1% (95% CI 100.8-113.9%); single A.X 94.2%; Self-Refine 95.1%.

Mechanism notes: revisions tried/accepted — regenerate 60/27, extend 16/11. Gate counterfactual (accept every
first-round candidate) gives the same strict accuracy (.822), so on this set the Gate did not change the net score;
its protective effect is not demonstrated here. The contributions of Planner-conditioned generation vs Checker/Reviser
are not yet separated (ablations pending).

Scope: IFEval-Ko measures verifiable format/length/lexical constraint following, not content quality. The GPT-4o
comparison shows constraint-compliance competitiveness only. IFEval-Ko prompts were machine-translated (GPT-4o) and
public benchmarks may be in model training data. One model assignment only; generalization over assignments pending.
