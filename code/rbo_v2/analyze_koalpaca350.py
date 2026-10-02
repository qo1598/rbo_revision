"""KoAlpaca350 judged comparisons (PROTOCOL_KOALPACA350.md + Amendment 1): counts, conditional win rate with 95% item
bootstrap (10,000, seed 20260927), exact sign test, and length diagnostics. No model calls."""
import json, random, statistics
from math import comb
from pathlib import Path
S = Path(r"C:/rbov2/revision/rbo_s_v1")
items = {json.loads(l)["row"]: json.loads(l) for l in (S / "bank_orig350.jsonl").read_text(encoding="utf-8").splitlines()}
ext = lambda n: {json.loads(l)["row"]: json.loads(l)["text"] for l in (S / "runs" / f"orig350_ext_{n}.jsonl").read_text(encoding="utf-8").splitlines()}
texts = {"rbov2": ext("rbov2"), "v2single_ax7": ext("v2single_ax7"), "gpt4o_matched": ext("gpt4o_matched"), "deepseek_matched": ext("deepseek_matched"),
         "gpt4o_archived": {k: v["archived"]["gpt4o_archived"] for k, v in items.items()}, "rbo_v1_main": {k: v["archived"]["rbo_v1_main"] for k, v in items.items()}}
C = [("ext-v2single_ax7", "v2single_ax7", "primary: role structure vs single"), ("ext-gpt4o_matched", "gpt4o_matched", "primary: % of SOTA (matched prompt)"),
     ("ext-deepseek_matched", "deepseek_matched", "% of SOTA (matched prompt)"), ("archived-rbo_v1_main", "rbo_v1_main", "improvement over submitted V1"),
     ("archived-gpt4o_archived", "gpt4o_archived", "secondary: submitted-study GPT-4o outputs (concise system prompt; confounded)")]
out = {}
for f, t, role in C:
    ev = {json.loads(l)["row"]: json.loads(l)["panel"] for l in (S / "runs" / f"eval_orig350_ext-rbov2_vs_{f}.jsonl").read_text(encoding="utf-8").splitlines()}
    labs = list(ev.values()); w, l = labs.count("x"), labs.count("y")
    rnd = random.Random(20260927); bs = []
    for _ in range(10000):
        s = [labs[rnd.randrange(len(labs))] for _ in labs]; a, b = s.count("x"), s.count("y")
        if a + b: bs.append(a / (a + b))
    bs.sort()
    p = min(1.0, 2 * sum(comb(w + l, i) for i in range(min(w, l) + 1)) / 2 ** (w + l))
    strata = {}
    for k, pl in ev.items():
        if pl in ("x", "y"):
            r = len(texts["rbov2"][k]) / max(1, len(texts[t][k]))
            key = "rbo_shorter(<0.67)" if r < 0.67 else ("similar(0.67-1.5)" if r < 1.5 else "rbo_longer(>1.5)")
            strata.setdefault(key, []).append(pl == "x")
    out[t] = {"role": role, "W": w, "L": l, "T": labs.count("tie"), "U": labs.count("unresolved"), "identical": labs.count("identical"),
              "cond_win": w / (w + l), "ci95": [bs[250], bs[9749]], "sign_p": p,
              "median_chars": {"rbov2": statistics.median(len(x) for x in texts["rbov2"].values()), t: statistics.median(len(x) for x in texts[t].values())},
              "cond_win_by_length": {k: {"n": len(v), "cond_win": sum(v) / len(v)} for k, v in strata.items()}}
Path(r"C:/rbov2/revision/rbo_v2/KOALPACA350_RESULT.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
for t, v in out.items():
    print(t, v["W"], v["L"], v["T"], v["U"], v["identical"], round(v["cond_win"], 3), [round(x, 3) for x in v["ci95"]], f"p={v['sign_p']:.2g}", v["median_chars"], {k: (x["n"], round(x["cond_win"], 2)) for k, x in v["cond_win_by_length"].items()})
