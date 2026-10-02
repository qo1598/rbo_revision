# Reproducibility package: When Does Role-Based Orchestration Help Small Language Model Agents?

Code, frozen protocols, model outputs and judgments for the revised manuscript (Applied Intelligence, APIN-D-26-06245).

## Contents

| Folder | What it holds |
|---|---|
| `code/rbo_v2/` | RBO v2 (`rbo.py` IFEval-Ko, `rbo_qa.py` KorQuAD, `rbo_math.py` HRM8K), baselines (single, Self-Refine, self-consistency), GPT-4o/DeepSeek reference runners, analysis scripts. `data/ifeval_ko/` is the official IFEval-Ko evaluator, unmodified. |
| `code/scorer/` | Pinned whole-answer exact-match scorer used for KorQuAD, with the KLUE-baseline metric utilities it imports (`official_klue_metrics_utils.py`, copied verbatim from KLUE-baseline commit 8a03c944 under that repository's license). |
| `code/judge_and_banks/` | Three-provider pairwise judge (`gen_judge.py`, `gen_eval.py`), API client, and the scripts that built the KoAlpaca350 and KorQuAD banks. |
| `code/human_eval/` | Human-evaluation packet builder (3- and 9-rater designs), intake check and analysis. |
| `code/manuscript/` | Resource accounting, prompt-token reconstruction and figure scripts. |
| `protocols/` | Confirmatory protocols, amendments, lock files (SHA-256 of code and data at freeze time), splits and result summaries. |
| `data/` | KorQuAD bank as IDs only; KoAlpaca350 items with the initial-study outputs. IFEval-Ko (Apache-2.0) and the HRM8K GSM8K subset (MIT) are under `code/rbo_v2/data/`, where the lock files expect them. |
| `outputs/` | Every confirmatory model output with per-call traces (role, model, tokens, seconds). |
| `judgments/` | KoAlpaca350 LLM-panel judgments: per-judge labels for both presentation orders and the panel label (derived labels; raw judge responses are not included). |
| `v1_reexamination/` | Summary results for the initial design (RBO v1) cited in Table 1 and Section 3; the underlying RBO v1 runs and judgments are not included. |
| `derived/` | Tables behind the manuscript (resources, reconstructed prompt tokens, per-category results, figure data). |
| `human_eval/` | Anonymized human ratings and the code-to-pair mapping. Released fields are the label, reason tags and viewing time rounded to seconds; rater profile fields, free-text notes and exact timestamps were removed. |
| `MANIFEST.json` | SHA-256 of every file in this package. |
| `setup_layout.py`, `requirements.txt` | Layout and environment for re-running the analyses (below). |
| `RENAMING_PATCHES.json`, `verify_locks.py` | See "Design name and lock verification" below. |

## Reproducing

### Environment
- Python 3.11 with the packages in `requirements.txt` (`pip install -r requirements.txt`). The listed versions are those used when the released analyses were re-run; the versions used at generation time were not recorded.
- To regenerate model outputs: Ollama with the local models in Appendix E of the manuscript, context 8,192 tokens. All local calls use greedy decoding except self-consistency (SC3), whose first sample is greedy and whose other two samples use temperature 0.7 with seeds 1 and 2. Frontier models were called with temperature 0; the judge models and DeepSeek-V3.2 through an OpenAI-compatible API gateway and GPT-4o through the OpenAI API. API keys are read from a local `.env` file that is not included.

### Re-running the analyses
The scripts expect the directory layout of the original project. Recreate it from this package:

```
python setup_layout.py <target>
cd <target>/revision
```

Then, from `<target>/revision`:

| Manuscript item | Command |
|---|---|
| Table 4 (IFEval-Ko) | `python rbo_v2/analyze_ifeval.py` |
| Tables 5–6 (ablations, assignments) | `python rbo_v2/analyze_ext.py` |
| Table 8, Appendix D (KoAlpaca350) | `python rbo_v2/analyze_koalpaca350.py` |
| Table 9 (human evaluation) | `python human_eval_2026_10/analyze.py human_eval_2026_10/returns --nine` |
| Section 6.1 post hoc analyses | `python manuscript/ifeval_coverage.py` |
| Section 6.5 rater sensitivity | `python manuscript/human_sensitivity.py` |
| Calls, tokens and times (Tables 4, 7) | `python manuscript/resources.py` |
| Figure 2 | `python manuscript/figures.py` |
| Table 7 (KorQuAD, HRM8K) | `python rbo_v2/analyze_mathqa.py korquad` and `... hrm8k` (see below) |
| Lock verification | `python verify_locks.py` (run in the package root, not in the layout) |

`analyze_mathqa.py` first checks `MATHQA_LOCK.json`, which includes the KorQuAD bank. KorQuAD contexts are not redistributed (CC BY-ND 4.0), so restore the bank before running it. Download the KorQuAD 1.0 validation split (`KorQuAD/squad_kor_v1`, 5,774 rows) as a JSON list of rows with fields `id`, `title`, `context`, `question` and `answers` into `rbo_s_v1/korquad_v1_validation.json`, then run `python rbo_s_v1/restore_korquad_bank.py rbo_s_v1/korquad_v1_validation.json`. The script selects the 950 released GUIDs (`bank_korquad_ids.jsonl`) in their released order, writes `bank_korquad.jsonl` with the fields `guid`, `title`, `question`, `instruction` (the question followed by the fixed answer-only instruction), `context` and `answers` (one JSON object per line, keys sorted, UTF-8, LF), and prints its SHA-256, which must equal the value in `MATHQA_LOCK.json`. For reference, the original selection (`build_korquad_bank.py`) used validation rows 0-5,699 (rows 5,700-5,773 were not downloaded because of rate limiting, decided before any output), skipped contexts longer than 3,000 characters, kept one question per distinct context (the one with the smallest salted SHA-256 of its ID) and ordered the bank by a second salted hash (salt in the script); it therefore needs exactly those 5,700 rows, whereas the GUID-based script works from the full split. `reconstruct_prompt_tokens.py` also needs this bank.

The judging runner `rbo_s_v1/gen_eval.py` imports modules from an earlier experiment that are not part of this paper. To re-judge pairs, call `gen_judge.judge_pair(item, text_a, text_b)` directly with the outputs in `rbo_s_v1/runs/`.

## Data licenses and attribution

- Code: MIT License (see `LICENSE`).

- IFEval-Ko: allganize/IFEval-Ko, Apache-2.0 (translation of google/IFEval).
- HRM8K: HAERAE-HUB/HRM8K, MIT.
- KorQuAD 1.0: CC BY-ND 4.0; IDs only.
- KoAlpaca: Beomi/KoAlpaca; distributed under the license stated in its repository (data license CC BY-NC 4.0). The 350-item bank, its categories and model outputs on it are provided for non-commercial research use with attribution.
- Model outputs from GPT-4o and DeepSeek are included as research records; their use is subject to the providers' terms.

## Design name and lock verification

The manuscript calls the redesigned system RBO v2 and the initial design RBO v1. During development the redesign carried a different internal version label. For this package every occurrence of that label in folder names, file names and file contents was changed to v2. The lock files must stay byte-identical, because they hold SHA-256 hashes of the code, data and protocols frozen before the confirmatory outputs; changing them would remove that evidence. `RENAMING_PATCHES.json` therefore records every renamed path and every replaced text span. `verify_locks.py` restores the original bytes from these records, confirms each restored file against its recorded original hash, and then checks every lock entry. Two kinds of strings were deliberately not changed: model names (DeepSeek-V3.2) and the salt strings of the split scripts, which are hash seeds whose change would produce different splits.

## Notes

- `outputs/rbo_v2/` also contains development runs; confirmatory items are those in `protocols/rbo_v2/SPLIT_*.json` under `confirm`.
- Development explorations that are not part of the manuscript are not included.
- In `human_eval/returns/`, rater P07's file carries `"complete": false` because one decisive rating lacks a reason tag; all 61 main ratings of that rater are present and labeled.
- `code/judge_and_banks/judge_client.py` also lists endpoints for judges that are not part of the reported panel; the reported panel is claude-opus-5, gemini-3-1-pro and kimi-k3 (`gen_judge.JUDGES`).
