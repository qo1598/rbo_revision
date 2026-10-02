# Amendment 1 to PROTOCOL_KOALPACA350.md (2026-09-27)

## What happened
Comparison (1) RBO v2 vs archived GPT-4o was completed (panel W/L/T/U/identical 171/73/24/70/12, conditional win .701;
`rbo_s_v1/runs/eval_orig350_ext-rbov2_vs_archived-gpt4o_archived.jsonl`). A length check then showed the archived GPT-4o
outputs are very short (median 65 chars; DeepSeek 94; RBO v2 287), and RBO v2 won 73% of decided pairs where it was longer
vs 25% where shorter. The submitted study's generation code (the original-study generation scripts) shows the SOTA
comparator used the system prompt "You are a concise assistant. Follow the instruction precisely and answer directly."
(temperature 0.7, top_p 0.9, max_tokens 512). RBO v2 received no such instruction, so comparison (1) confounds system with
prompt/length condition. Judging was stopped during comparison (2); partial (2) judgments remain in the cache, unused.

## Change (decided after seeing (1), before any matched-prompt output)
Primary frontier comparisons are replaced by matched-prompt comparators: GPT-4o-2024-11-20 (OpenAI direct) and
DeepSeek-V3.2 (`deepseek-v3-2` via billing-ai; the submitted study's `deepseek-chat` snapshot is not available) receive the
exact RBO v2 request text (instruction + input), no system prompt, temperature 0, max 1,280 tokens (`run_frontier_koalpaca.py`).
Model versions are reported as used; they are not claimed identical to the submitted study's comparators.
New fixed judging order: (1') RBO v2 vs matched GPT-4o, (2') vs single A.X, (3') vs matched DeepSeek, (4') vs archived V1.
The archived-GPT-4o comparison (1) is reported as a secondary result with the prompt/length caveat. Length is reported for
every comparison (median chars; win rate by longer/shorter).
