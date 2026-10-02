# Reproducibility package: When Does Role-Based Orchestration Help Small Language Model Agents?

Code, frozen protocols, model outputs and judgments for the revised manuscript (Applied Intelligence, APIN-D-26-06245).

## Contents

| Folder | What it holds |
|---|---|
| `code/rbo_v2/` | RBO v2 (`rbo.py` IFEval-Ko, `rbo_qa.py` KorQuAD, `rbo_math.py` HRM8K), baselines (single, Self-Refine, self-consistency), GPT-4o/DeepSeek reference runners, analysis scripts. `data/ifeval_ko/` is the official IFEval-Ko evaluator, unmodified. |
| `code/scorer/` | Pinned whole-answer exact-match scorer used for KorQuAD. |
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
| `RENAMING_PATCHES.json`, `verify_locks.py` | See "Design name and lock verification" below. |

## Reproducing

1. Install Ollama and pull the local models listed in the manuscript (Appendix E). Decoding is greedy; context 8,192 tokens.
2. Scripts use absolute paths from the authors' machine (`C:/rbov2/...`); adjust `HERE`/`ROOT` constants at the top of each script.
3. API keys are read from a local `.env` file that is not included. Frontier models were called with temperature 0. The judge models and DeepSeek-V3.2 were accessed through an OpenAI-compatible API gateway, and GPT-4o through the OpenAI API.
4. KorQuAD contexts are not redistributed (CC BY-ND 4.0). Download KorQuAD 1.0 validation (`KorQuAD/squad_kor_v1`) and rebuild the bank with `code/judge_and_banks/build_korquad_bank.py`; `data/korquad/bank_korquad_ids.jsonl` lists the GUIDs in bank order.
5. Each analysis script checks its lock file and reports `lock_drift`. Because of the renaming below, run `python verify_locks.py` for the lock check of this package.

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
- Self-consistency (SC3) uses temperature 0 for the first sample and 0.7 with seeds 1 and 2 for the others; all other local calls are greedy.
