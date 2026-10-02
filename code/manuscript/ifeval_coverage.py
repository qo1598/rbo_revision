"""Post hoc analyses requested in review (no model calls; existing confirmatory outputs only).
(1) Tool coverage: IFEval-Ko instruction types split into those that a checker tool measures directly and those without a
    dedicated tool; instruction-level strict accuracy per group for RBO v2, single A.X, Self-Refine and GPT-4o.
(2) Split sensitivity: prompt-level strict results on the confirmatory prompts that were never in the original
    101-item development split (excluding the 51 prompts moved from development to confirmation).
Writes IFEVAL_COVERAGE.json."""
import json, sys
from math import comb
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "rbo_v2"
sys.path.insert(0, str(R))
import score_ifeval as S  # noqa: E402

TOOL_TYPES = {  # instruction type -> checker tool that measures it directly
    "length_constraints:number_words": "word_count", "length_constraints:number_sentences": "sentence_count",
    "length_constraints:number_paragraphs": "paragraph_count", "detectable_format:number_bullet_lists": "bullet_count",
    "detectable_format:number_highlighted_sections": "highlight_count", "detectable_content:number_placeholders": "placeholder_count",
    "keywords:frequency": "keyword_count", "keywords:existence": "keyword_count", "keywords:forbidden_words": "forbidden_words",
    "punctuation:no_comma": "no_char", "startend:end_checker": "ends_with", "startend:quotation": "wrapped_in",
    "detectable_format:json_format": "json_valid"}
SYSTEMS = {"RBO v2": "ifeval_rboT2_qwen8-ax7-qwen8-qwen8", "single A.X": "ifeval_single_ax7", "Self-Refine A.X": "ifeval_sr_ax7", "GPT-4o": "ifeval_gpt4o"}

items = {x["key"]: x for x in S.items()}
split = json.loads((R / "SPLIT_IFEVAL.json").read_text())
old = json.loads((R / "SPLIT_IFEVAL.superseded_dev101.json").read_text())
confirm = set(split["confirm"])
moved = set(old["dev"]) & confirm
runs = {}
for name, stem in SYSTEMS.items():
    rows = {}
    for l in (R / "runs" / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(l)
        if x["id"] in confirm:
            rows[x["id"]] = x
    assert len(rows) == len(confirm), (name, len(rows))
    runs[name] = rows

out = {"tool_types": sorted(TOOL_TYPES), "no_tool_types": sorted({t for x in items.values() for t in x["instruction_id_list"]} - set(TOOL_TYPES)), "coverage": {}}
for group in ("tool", "no_tool"):
    res = {}
    for name, rows in runs.items():
        ok = n = 0
        for k, r in rows.items():
            for t, passed in zip(items[k]["instruction_id_list"], r["strict_list"]):
                if (t in TOOL_TYPES) == (group == "tool"):
                    n += 1
                    ok += bool(passed)
        res[name] = {"n_instructions": n, "strict": ok / n}
    out["coverage"][group] = res


def mcnemar(a, b, keys):
    w = sum(1 for k in keys if a[k]["strict"] and not b[k]["strict"])
    l = sum(1 for k in keys if b[k]["strict"] and not a[k]["strict"])
    p = min(1.0, 2 * sum(comb(w + l, i) for i in range(min(w, l) + 1)) / 2 ** (w + l)) if w + l else 1.0
    return {"W": w, "L": l, "p_exact": p}


keep = sorted(confirm - moved)
out["split_sensitivity"] = {"n_confirm": len(confirm), "n_moved_from_old_dev": len(moved), "n_kept": len(keep),
                            "strict": {name: sum(rows[k]["strict"] for k in keep) / len(keep) for name, rows in runs.items()},
                            "rbo_vs_single": mcnemar(runs["RBO v2"], runs["single A.X"], keep),
                            "rbo_vs_selfrefine": mcnemar(runs["RBO v2"], runs["Self-Refine A.X"], keep),
                            "rbo_vs_gpt4o": mcnemar(runs["RBO v2"], runs["GPT-4o"], keep)}
(Path(__file__).parent / "IFEVAL_COVERAGE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["coverage"], indent=1))
print(json.dumps(out["split_sensitivity"], indent=1))
print("no-tool types:", out["no_tool_types"])

# ---- additions requested in the second review round (post hoc, unadjusted) ----
import random
homog = {}
for l in (R / "runs" / "ifeval_rboT2_ax7-ax7-ax7-ax7.jsonl").read_text(encoding="utf-8").splitlines():
    x = json.loads(l)
    if x["id"] in confirm:
        homog[x["id"]] = x
allk = sorted(confirm)
out["homogeneous_ax"] = {"strict": sum(homog[k]["strict"] for k in allk) / len(allk),
                         "homog_vs_selfrefine": mcnemar(homog, runs["Self-Refine A.X"], allk),
                         "full_vs_homog": mcnemar(runs["RBO v2"], homog, allk)}
rnd = random.Random(20261002)
cl = {}
for group in ("tool", "no_tool"):
    per = []
    for k in allk:
        a = b = n = 0
        for t, pa, pb in zip(items[k]["instruction_id_list"], runs["RBO v2"][k]["strict_list"], runs["single A.X"][k]["strict_list"]):
            if (t in TOOL_TYPES) == (group == "tool"):
                a += bool(pa); b += bool(pb); n += 1
        if n:
            per.append((a, b, n))
    est = (sum(p[0] for p in per) - sum(p[1] for p in per)) / sum(p[2] for p in per)
    bs = []
    for _ in range(10000):
        smp = [per[rnd.randrange(len(per))] for _ in per]
        bs.append((sum(p[0] for p in smp) - sum(p[1] for p in smp)) / sum(p[2] for p in smp))
    bs.sort()
    cl[group] = {"n_prompts": len(per), "rbo_minus_single": est, "ci95_prompt_cluster": [bs[250], bs[9749]]}
out["coverage_diff_clustered"] = cl
out["split_sensitivity"]["rbo_vs_selfrefine_H2"] = out["split_sensitivity"]["rbo_vs_selfrefine"]
out["tool_mapping"] = TOOL_TYPES
(Path(__file__).parent / "IFEVAL_COVERAGE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({"homogeneous_ax": out["homogeneous_ax"], "coverage_diff_clustered": cl}, indent=1))
