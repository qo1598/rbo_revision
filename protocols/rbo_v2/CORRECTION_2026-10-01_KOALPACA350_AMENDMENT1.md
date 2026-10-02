# Correction to PROTOCOL_KOALPACA350_AMENDMENT1.md (2026-10-01)

Kept in a separate file so that the locked protocol stays byte-identical to its lock (KOALPACA350_LOCK_A1.json).

**Correction (2026-10-01, appended; text above unchanged):** the attribution of the archived GPT-4o outputs to the
"concise assistant" system prompt of `original-study experiment folders/generate_responses*.py` is not supported by the file that produced them.
`논문2/rbo/gpt4o_efficiency_local.py` wrote `rbo/runs_gpt4o/SOTA_gpt4o_outputs.jsonl` with no system prompt and a user
template ending "최종 답변만 출력하라" (temperature 0.7, max_tokens 1024); DeepSeek used the same template. The
comparison remains prompt-asymmetric, and the amendment's decision (matched-prompt comparators) is unaffected.
See STATUS.md 2026-10-01.
