# RBO v2 on the original-submission KoAlpaca bank (350) — frozen protocol (2026-09-27)

Written BEFORE any RBO v2 or new single-A.X output on these items. Purpose: rerun the submitted study's comparison
with the revised architecture (reviewer-facing core result).

## Systems
- RBO v2 = IFEval-locked RBO-T2 (`rbo.py`, P=C=R=Qwen3-8B, G=A.X-4.0-Light 7B), transferred unchanged; no tuning or
  inspection on these 350 items. Request = instruction + input (`run_koalpaca.py`).
- single A.X (new, same request text and decoding: greedy, max 1,280 tokens).
- Archived comparators (unchanged, SHA-256-bound in `rbo_s_v1/bank_orig350.jsonl`): GPT-4o and DeepSeek outputs from
  the submitted study; submitted RBO V1 main outputs.

## Judging (paid, billing-ai; panel of JUDGE_PANEL_AMENDMENT: Claude Opus 5, Gemini 3.1 Pro, Kimi K3)
Blind pairwise, both orders per judge; a judge's label counts only if both orders agree; panel label needs >= 2 votes,
else unresolved; unresolved/identical never become ties; fail-closed on account/quota errors (`gen_judge.py`).
Order of comparisons (fixed): (1) RBO v2 vs GPT-4o, (2) vs DeepSeek, (3) vs V1, (4) vs single A.X.
Budget rule: after (1)-(3) the actual credits are checked; if (4) would exceed the remaining balance, the user decides
(top-up, or a random 175-item subset fixed by salted hash BEFORE any (4) judgment). No comparison is dropped silently.

## Estimands and tests
Per comparison: W/L/T/U counts and conditional win rate W/(W+L) with 95% item bootstrap (10,000, seed 20260927);
two-sided exact sign test on W vs L. Primary for the revision: (1) and (4). "% of SOTA" reported descriptively as the
conditional win rate vs each archived frontier output, as in the submitted manuscript; no parity/equivalence wording.
