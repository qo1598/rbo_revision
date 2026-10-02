"""Frozen analysis for PROTOCOL_MATH_QA.md. Usage: python analyze_mathqa.py korquad|hrm8k (confirm split only)."""
import sys, json, random, hashlib
from math import comb
from common import HERE, RUNS

task = sys.argv[1]
lock = json.loads((HERE / "MATHQA_LOCK.json").read_text())
drift = [f for f, h in lock.items() if not f.startswith("_") and hashlib.sha256(open(HERE / f, "rb").read()).hexdigest() != h]
keys = json.loads((HERE / ("SPLIT_KORQUAD.json" if task == "korquad" else "SPLIT_HRM8K.json")).read_text())["confirm"]
metric = "em" if task == "korquad" else "correct"
P = {"rbo": "rbo_qwen8-ax7-qwen8-qwen8", "single_ax7": "single_ax7", "sc3_ax7": "sc3_ax7", "single_qwen8": "single_qwen8",
     "rbo_submitted_models": "rbo_midm2-ax7-midm2-hcx3", "sr_ax7": "sr_ax7", "gpt4o": "gpt4o"}
R = {}
for p, f in P.items():
    d = {r["id"]: bool(r[metric]) for r in map(json.loads, open(RUNS / f"{task}_{f}.jsonl", encoding="utf-8"))}
    assert all(k in d for k in keys), (p, "missing")
    R[p] = d
acc = lambda p: sum(R[p][k] for k in keys) / len(keys)


def mc(a, b):
    w = sum(R[a][k] and not R[b][k] for k in keys); l = sum(R[b][k] and not R[a][k] for k in keys); n = w + l
    return {"W": w, "L": l, "p": min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n) if n else 1.0}


out = {"task": task, "lock_drift": drift, "n": len(keys), "accuracy": {p: acc(p) for p in P}}
h = {"H1 rbo vs single_ax7": mc("rbo", "single_ax7"), "H2 rbo vs sc3_ax7": mc("rbo", "sc3_ax7")}
order = sorted(h, key=lambda k: h[k]["p"])
for i, k in enumerate(order):
    h[k]["p_holm"] = min(1.0, max(h[o]["p"] * (len(order) - j) for j, o in enumerate(order[:i + 1])))
out["primary"] = h
out["secondary"] = {f"rbo vs {c}": mc("rbo", c) for c in ("single_qwen8", "sr_ax7", "gpt4o")}
out["secondary"]["rbo_submitted_models vs single_ax7"] = mc("rbo_submitted_models", "single_ax7")
rnd = random.Random(20260927); att = []
for _ in range(10000):
    s = [keys[rnd.randrange(len(keys))] for _ in keys]
    g = sum(R["gpt4o"][k] for k in s)
    att.append(sum(R["rbo"][k] for k in s) / g if g else float("nan"))
att.sort()
out["attainment_vs_gpt4o"] = {p: acc(p) / acc("gpt4o") for p in P if p != "gpt4o"}
out["attainment_rbo_ci95"] = [att[250], att[9749]]
(HERE / f"{task.upper()}_CONFIRM_RESULT.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(json.dumps(out, indent=1))
