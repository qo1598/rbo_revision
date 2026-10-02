"""Prespecified extension analysis (PROTOCOL_IFEVAL_EXT.md + amendments). Confirm split only; no model calls."""
import json, hashlib
from math import comb
import score_ifeval as S
from common import HERE, RUNS

lock = json.loads((HERE / "IFEVAL_EXT_LOCK_A2.json").read_text())
drift = [f for f, h in lock.items() if not f.startswith("_") and hashlib.sha256(open(HERE / f, "rb").read()).hexdigest() != h]
keys = json.loads((HERE / "SPLIT_IFEVAL.json").read_text())["confirm"]
it = {x["key"]: x for x in S.items()}
L = lambda f: {r["id"]: r for r in map(json.loads, open(RUNS / f"ifeval_{f}.jsonl", encoding="utf-8"))}


def strict(R):
    return {k: bool(R[k]["strict"]) for k in keys}


def mc(a, b):
    w = sum(a[k] and not b[k] for k in keys); l = sum(b[k] and not a[k] for k in keys); n = w + l
    return {"W": w, "L": l, "p": min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n) if n else 1.0}


acc = lambda d: sum(d.values()) / len(keys)
out = {"lock_drift": drift, "n": len(keys)}
t2 = strict(L("rboT2_qwen8-ax7-qwen8-qwen8")); ax = strict(L("single_ax7"))
draft = {k: S.score(it[k], next(t for t in L("rboT2_qwen8-ax7-qwen8-qwen8")[k]["trace"] if t["step"] == "draft")["answer"])["strict"] for k in keys}
E1 = {"A_plan": draft, "A_L2": strict(L("rboL2_qwen8-ax7-qwen8-qwen8")), "A_T1": strict(L("rboT_qwen8-ax7-qwen8-qwen8"))}
out["E1"] = {n: {"acc": acc(d), "vs_T2": mc(t2, d), "vs_single_ax7": mc(d, ax)} for n, d in E1.items()}
out["E1"]["T2_ref"] = acc(t2)
e2 = strict(L("rboT2_midm2-ax7-midm2-hcx3"))
out["E2"] = {"acc": acc(e2), "single_ax7": acc(ax), "vs_single_ax7": mc(e2, ax)}
E3 = {}
for m in ["qwen1.7", "qwen4", "qwen8", "exaone2", "midm2", "hcx3", "exaone8", "ax7"]:
    s = L(f"single_{m}"); r = L(f"rboT2_{m}-{m}-{m}-{m}")
    assert all(k in s and k in r for k in keys), m
    sd, rd = strict(s), strict(r)
    errs = sum(1 for k in keys for c in r[k]["calls"] if c.get("error")) + sum(1 for k in keys if s[k].get("error"))
    E3[m] = {"single": acc(sd), "rbo": acc(rd), "gain": acc(rd) - acc(sd), **mc(rd, sd), "failed_calls": errs,
             "checker_unparsable": sum(any(t.get("reason") == "checker_unparsable" for t in r[k]["trace"]) for k in keys)}
order = sorted(E3, key=lambda m: E3[m]["p"])
for i, m in enumerate(order):
    E3[m]["p_holm"] = min(1.0, max(E3[o]["p"] * (len(order) - j) for j, o in enumerate(order[:i + 1])))
pos = sum(E3[m]["gain"] > 0 for m in E3); n = len(E3)
out["E3"] = E3
out["E3_summary"] = {"positive": pos, "of": n, "sign_test_p_two_sided": min(1.0, 2 * sum(comb(n, i) for i in range(min(pos, n - pos) + 1)) / 2 ** n)}
(HERE / "IFEVAL_EXT_RESULT.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(out, indent=1, ensure_ascii=False))
