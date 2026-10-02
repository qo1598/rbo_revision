# RBO v2 on the submitted KoAlpaca bank (350) — judged result (2026-09-27)
Protocol `PROTOCOL_KOALPACA350.md` + `PROTOCOL_KOALPACA350_AMENDMENT1.md`; panel Claude Opus 5 / Gemini 3.1 Pro / Kimi K3,
both orders, order-consistent labels, >=2 votes else unresolved. `analyze_koalpaca350.py` -> `KOALPACA350_RESULT.json`.
RBO v2 = IFEval-locked RBO-T2 transferred unchanged. Conditional win rate = W/(W+L), 95% item bootstrap; exact sign test.

| RBO v2 vs | W/L/T/U/identical | cond. win [95% CI] | median chars (RBO v2 / comparator) | cond. win, similar length |
|---|---|---|---|---|
| single A.X (same request) | 61/139/44/83/23 | **.305** [.242, .370] | 287 / 559 | .33 (n=84) |
| GPT-4o-2024-11-20, matched prompt | 38/204/36/68/4 | **.157** [.112, .204] | 287 / 329 | .16 (n=98) |
| DeepSeek-V3.2, matched prompt | 62/212/10/61/5 | **.226** [.178, .278] | 287 / 517 | .19 (n=107) |
| submitted RBO V1 (archived) | 255/27/22/41/5 | **.904** [.869, .937] | 287 / 171 | .89 (n=56) |
| submitted GPT-4o (archived, concise system prompt) | 171/73/24/70/12 | .701 [.642, .759] | 287 / 66 | .42 (n=50) |

Reading: RBO v2 is a large improvement over the submitted V1 (robust within length strata), but on open-ended KoAlpaca
instructions it is worse than its own single Generator and far below matched-prompt GPT-4o/DeepSeek. The archived-GPT-4o
comparison is confounded by the submitted study's concise system prompt (similar-length pairs .42) and is not a
frontier-competitiveness result. Mechanism (descriptive): only ~3% of Planner requirements were tool-measurable; Checker
passed 313/350 drafts; 8 accepted revisions went 2W/4L/2T; differences from single A.X come mainly from plan-conditioned
drafting, which shortened answers. Consistent with the prespecified boundary prediction (open-ended = weak regime).
Credits: ~19.8M estimated from call counts x per-call rates (actual balance to be confirmed from billing).


**Correction (2026-10-01):** the archived GPT-4o outputs were most likely produced by `논문2/rbo/gpt4o_efficiency_local.py` (no system prompt; user template ending "최종 답변만 출력하라" = output only the final answer), not by the "concise assistant" system prompt in original-study experiment folders. The comparison is still prompt-asymmetric (different templates for RBO V1 and the frontier models). See STATUS.md 2026-10-01.
