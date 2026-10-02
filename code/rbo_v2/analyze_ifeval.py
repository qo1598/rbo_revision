"""Frozen confirmatory analysis for PROTOCOL_IFEVAL.md (confirm split only). No model calls."""
import json, random, hashlib
from math import comb
import score_ifeval as S
from common import HERE, RUNS

lock = json.loads((HERE / "IFEVAL_LOCK.json").read_text())
drift = [f for f, h in lock.items() if not f.startswith("_") and hashlib.sha256(open(HERE / f, "rb").read()).hexdigest() != h]
keys = json.loads((HERE / "SPLIT_IFEVAL.json").read_text())["confirm"]
it = {x["key"]: x for x in S.items()}
P = {"rbo_t2": "ifeval_rboT2_qwen8-ax7-qwen8-qwen8.jsonl", "single_ax7": "ifeval_single_ax7.jsonl",
     "single_qwen8": "ifeval_single_qwen8.jsonl", "sr_ax7": "ifeval_sr_ax7.jsonl", "gpt4o": "ifeval_gpt4o.jsonl"}
R = {p: {r["id"]: r for r in map(json.loads, open(RUNS / f, encoding="utf-8"))} for p, f in P.items()}
assert all(set(keys) <= set(R[p]) for p in P), "missing outputs"


def mcnemar(a, b):
    w = sum(R[a][k]["strict"] and not R[b][k]["strict"] for k in keys)
    l = sum(R[b][k]["strict"] and not R[a][k]["strict"] for k in keys)
    n = w + l
    p = min(1.0, 2 * sum(comb(n, i) for i in range(0, min(w, l) + 1)) / 2 ** n) if n else 1.0
    return {"W": w, "L": l, "p_exact_two_sided": p}


def acc(p, level="strict"):
    if level == "inst":
        v = [x for k in keys for x in R[p][k]["strict_list"]]
        return sum(v) / len(v)
    return sum(R[p][k][level] for k in keys) / len(keys)


out = {"lock_drift": drift, "n": len(keys)}
out["accuracy"] = {p: {"prompt_strict": acc(p), "prompt_loose": acc(p, "loose"), "inst_strict": acc(p, "inst")} for p in P}
h = {"H1 rbo_t2 vs single_ax7": mcnemar("rbo_t2", "single_ax7"), "H2 rbo_t2 vs sr_ax7": mcnemar("rbo_t2", "sr_ax7")}
order = sorted(h, key=lambda k: h[k]["p_exact_two_sided"])
for i, k in enumerate(order):
    h[k]["p_holm"] = min(1.0, max(h[o]["p_exact_two_sided"] * (len(order) - j) for j, o in enumerate(order[:i + 1])))
out["primary"] = h
out["secondary"] = {"rbo_t2 vs single_qwen8": mcnemar("rbo_t2", "single_qwen8"), "rbo_t2 vs gpt4o": mcnemar("rbo_t2", "gpt4o"),
                    "single_ax7 vs gpt4o": mcnemar("single_ax7", "gpt4o"), "sr_ax7 vs single_ax7": mcnemar("sr_ax7", "single_ax7")}
rnd = random.Random(20260926)
diffs, att = [], []
for _ in range(10000):
    s = [keys[rnd.randrange(len(keys))] for _ in keys]
    a = sum(R["rbo_t2"][k]["strict"] for k in s); b = sum(R["single_ax7"][k]["strict"] for k in s); g = sum(R["gpt4o"][k]["strict"] for k in s)
    diffs.append((a - b) / len(s)); att.append(a / g if g else float("nan"))
diffs.sort(); att.sort()
out["rbo_minus_single_ax7"] = {"diff": acc("rbo_t2") - acc("single_ax7"), "ci95": [diffs[250], diffs[9749]]}
out["attainment_vs_gpt4o"] = {p: acc(p) / acc("gpt4o") for p in ("rbo_t2", "single_ax7", "single_qwen8", "sr_ax7")}
out["attainment_rbo_ci95"] = [att[250], att[9749]]
# gate counterfactual: accept the first-round candidate regardless of the gate
cf, modes = 0, {}
for k in keys:
    tr = R["rbo_t2"][k]["trace"]
    revs = [t for t in tr if t["step"].startswith("revise")]
    ans = revs[0]["answer"] if revs else R["rbo_t2"][k]["text"]
    cf += S.score(it[k], ans)["strict"]
    for t in revs:
        m = modes.setdefault(t["mode"], {"tried": 0, "accepted": 0})
        m["tried"] += 1; m["accepted"] += bool(t["accepted"])
out["gate_counterfactual_no_gate_round1_strict"] = cf / len(keys)
out["revision_modes"] = modes
cost = lambda p: sum(sum((c["output_tokens"] or 0) for c in R[p][k]["calls"]) if "calls" in R[p][k] else R[p][k]["output_tokens"] for k in keys) / len(keys)
out["mean_output_tokens"] = {p: cost(p) for p in ("rbo_t2", "single_ax7", "single_qwen8", "sr_ax7")}
out["mean_calls"] = {p: (sum(len(R[p][k]["calls"]) for k in keys) / len(keys) if "calls" in R[p][keys[0]] else 1) for p in ("rbo_t2", "single_ax7", "sr_ax7")}
(HERE / "IFEVAL_CONFIRM_RESULT.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(out, indent=1, ensure_ascii=False))
