"""Analyze returned 2026-10 human ratings exactly as PROTOCOL.md specifies. Reads returns/R0X*.json (unedited),
private/mapping.json and the LLM panel files; writes RESULT.json into the returns dir. No model calls.
Usage: python analyze.py [returns_dir] [--nine]   (--nine: 9-rater block design, AMENDMENT1_9RATERS.md)"""
from __future__ import annotations

import hashlib
import json
import random
import statistics
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent / "rbo_s_v1" / "runs"
NINE = "--nine" in sys.argv
RATERS = tuple(f"P0{i}" for i in range(1, 10)) if NINE else ("R01", "R02", "R03")
MAPFILE, MANFILE = ("mapping9.json", "MANIFEST9.json") if NINE else ("mapping.json", "MANIFEST.json")
COMPS = ("R1", "R2", "R3", "O1", "O2")
# panel files: label "x" = first-named system (system A in this study), "y" = second
PANEL = {"R1": "eval_orig350_ext-rbov2_vs_ext-v2single_ax7.jsonl", "R2": "eval_orig350_ext-rbov2_vs_ext-gpt4o_matched.jsonl",
         "R3": "eval_orig350_ext-rbov2_vs_archived-rbo_v1_main.jsonl",
         "O1": "eval_orig350_archived-rbo_v1_main_vs_archived-gpt4o_archived.jsonl",
         "O2": "eval_orig350_archived-rbo_v1_ds_run_vs_archived-deepseek_archived.jsonl"}
CATS3 = ("A", "B", "tie")


def load_returns(rdir: Path, mapping: dict) -> tuple[dict, dict]:
    labels, meta = {}, {}
    manifest = json.loads((HERE / MANFILE).read_text(encoding="utf-8"))
    for r in RATERS:
        files = sorted(p for p in rdir.glob(f"{r}_*.json") if "중간" not in p.name)
        if len(files) != 1:
            raise SystemExit(f"{r}: expected exactly one final return file, found {[p.name for p in files]}")
        raw = files[0].read_bytes()
        d = json.loads(raw)
        assert d["rater"] == r, (r, d["rater"])
        assert d["packet_sha256"] == manifest["raters"][r]["packet_sha256"], f"{r}: packet hash mismatch"
        meta[r] = {"file": files[0].name, "file_sha256": hashlib.sha256(raw).hexdigest(), "saved_at": d["saved_at"],
                   "complete": d["complete"], "consent": d["meta"].get("consent"), "pledge": d["meta"].get("pledge"),
                   "years": d["meta"].get("years"), "degree": d["meta"].get("degree")}
        for x in d["ratings"]:
            m = mapping[f"{r}:{x['code']}"]
            lab = x.get("label") or ""
            dec = {"left": "A" if m["a_side"] == "left" else "B", "right": "A" if m["a_side"] == "right" else "B",
                   "tie": "tie", "cannot": "cannot", "": "missing"}[lab]
            labels[(r, m["kind"], m["comp"], m["row"])] = {"label": dec, "side": lab, "reason": x.get("reason", ""),
                                                           "visibleMs": x.get("visibleMs"), "category": m["category"],
                                                           "tags": x.get("reasonTags") or []}
    return labels, meta


def consensus(votes: list[str]) -> str:
    valid = [v for v in votes if v in CATS3]
    for c in CATS3:
        if valid.count(c) >= 2:
            return c
    return "unresolved"


def fleiss(items: list[list[str]]) -> float | None:
    full = [v for v in items if all(x in CATS3 for x in v)]
    if not full:
        return None
    n, k = 3, len(CATS3)
    P = [(sum(v.count(c) ** 2 for c in CATS3) - n) / (n * (n - 1)) for v in full]
    p = [sum(v.count(c) for v in full) / (n * len(full)) for c in CATS3]
    pe = sum(x * x for x in p)
    return None if pe == 1 else (statistics.mean(P) - pe) / (1 - pe)


def cohen(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    po = sum(a == b for a, b in pairs) / len(pairs)
    pe = sum((sum(a == c for a, _ in pairs) / len(pairs)) * (sum(b == c for _, b in pairs) / len(pairs)) for c in CATS3)
    return None if pe == 1 else (po - pe) / (1 - pe)


def clopper(w: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    def cdf(k, p):
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if w == 0 else solve(lambda p: 1 - cdf(w - 1, p) < 0.025)
    upper = 1.0 if w == n else solve(lambda p: cdf(w, p) > 0.025)
    return [lower, upper]


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--nine"]
    rdir = Path(args[0]) if args else HERE / "returns"
    mapping = json.loads((HERE / "private" / MAPFILE).read_text(encoding="utf-8"))
    sample = json.loads((HERE / "SAMPLE.json").read_text(encoding="utf-8"))
    labels, meta = load_returns(rdir, mapping)
    rng = random.Random(20261001)
    out = {"returns": meta, "comparisons": {}, "raters": {}}
    all_items = []
    for comp in COMPS:
        rows = [x for x in sample if x["comp"] == comp]
        votes = {x["row"]: [labels[(r, "core", comp, x["row"])]["label"] for r in RATERS if (r, "core", comp, x["row"]) in labels] for x in rows}
        assert all(len(v) == 3 for v in votes.values()), f"{comp}: every pair must have exactly three ratings"
        cons = {k: consensus(v) for k, v in votes.items()}
        all_items += list(votes.values())
        c = list(cons.values())
        w, l, t, u = c.count("A"), c.count("B"), c.count("tie"), c.count("unresolved")
        bs, undefined = [], 0
        keys = list(cons)
        for _ in range(20000):
            s = [cons[keys[rng.randrange(len(keys))]] for _ in keys]
            a, b = s.count("A"), s.count("B")
            if a + b:
                bs.append(a / (a + b))
            else:
                undefined += 1
        bs.sort()
        panel_path = S / PANEL[comp]
        agree = None
        if panel_path.exists():
            pan = {json.loads(z)["row"]: json.loads(z)["panel"] for z in panel_path.read_text(encoding="utf-8").splitlines()}
            pmap = {"x": "A", "y": "B", "tie": "tie"}
            pp = [(cons[k], pmap[pan[k]]) for k in cons if cons[k] in CATS3 and pan.get(k) in pmap]
            agree = {"n_both_resolved": len(pp), "raw_agreement": sum(a == b for a, b in pp) / len(pp) if pp else None,
                     "cohen_kappa": cohen(pp), "panel_unresolved": sum(pan.get(k) not in pmap for k in cons)}
        tags = {}
        for x in rows:
            for r in RATERS:
                v = labels.get((r, "core", comp, x["row"]))
                if v and v["label"] in ("A", "B"):
                    for tg in v["tags"]:
                        tags.setdefault(v["label"], {}).setdefault(tg, 0)
                        tags[v["label"]][tg] += 1
        cats = {}
        for x in rows:
            cats.setdefault(x["category"], []).append(cons[x["row"]])
        out["comparisons"][comp] = {
            "n_items": len(rows), "W": w, "L": l, "T": t, "U": u,
            "cond_win": w / (w + l) if w + l else None,
            "bootstrap95": [bs[int(.025 * len(bs))], bs[int(.975 * len(bs)) - 1]] if bs else None,
            "bootstrap_undefined_resamples": undefined, "clopper_pearson95": clopper(w, w + l),
            "sign_test_p": min(1.0, 2 * sum(comb(w + l, i) for i in range(min(w, l) + 1)) / 2 ** (w + l)) if w + l else None,
            "fleiss_kappa": fleiss(list(votes.values())), "human_vs_llm_panel": agree, "reason_tags_by_preferred_system": tags,
            "by_category": {k: {z: v.count(z) for z in ("A", "B", "tie", "unresolved")} for k, v in sorted(cats.items())}}
    kb = []
    for _ in range(2000):
        s = [all_items[rng.randrange(len(all_items))] for _ in all_items]
        k = fleiss(s)
        if k is not None:
            kb.append(k)
    kb.sort()
    out["fleiss_kappa_all"] = {"kappa": fleiss(all_items), "bootstrap95": [kb[50], kb[1949]] if kb else None}
    for r in RATERS:
        core = [v for (rr, kind, _, _), v in labels.items() if rr == r and kind == "core"]
        reps = [(k, v) for k, v in labels.items() if k[0] == r and k[1] == "repeat"]
        same = sum(labels[(r, "core", k[2], k[3])]["label"] == v["label"] for k, v in reps)
        ms = [v["visibleMs"] for v in core if isinstance(v["visibleMs"], (int, float))]
        dec = [v for v in core if v["side"] in ("left", "right")]
        out["raters"][r] = {
            "labels": {z: sum(v["label"] == z for v in core) for z in ("A", "B", "tie", "cannot", "missing")},
            "left_rate_among_decisive": sum(v["side"] == "left" for v in dec) / len(dec) if dec else None,
            "repeat_consistency": f"{same}/{len(reps)}",
            "median_visible_s": statistics.median(ms) / 1000 if ms else None,
            "share_under_10s": sum(x < 10000 for x in ms) / len(ms) if ms else None,
            "decisive_without_reason_tag": sum(not v["tags"] for v in dec),
            "decisive_with_memo": sum(len(v["reason"].strip()) >= 2 for v in dec)}
    yrs = []
    for m in meta.values():  # teaching experience in whole years (user decision 2026-10-01)
        try:
            yrs.append(int(float(str(m.get("years") or "").strip())))
        except ValueError:
            pass
    deg = ["master" if "석사" in str(m.get("degree") or "") else "bachelor" for m in meta.values()]
    out["panel_profile"] = {"n_raters": len(meta), "years_min": min(yrs) if yrs else None, "years_max": max(yrs) if yrs else None,
                            "degree_counts": {d: deg.count(d) for d in sorted(set(deg))},
                            "saved_first": min(m["saved_at"] for m in meta.values()), "saved_last": max(m["saved_at"] for m in meta.values())}
    reasons = [(k, v["reason"].strip()) for k, v in labels.items() if k[1] == "core" and len(v["reason"].strip()) >= 10]
    dup = {}
    for k, txt in reasons:
        dup.setdefault(txt, set()).add(k[0])
    out["reason_integrity"] = {"reasons_ge10_chars": len(reasons),
                               "identical_reason_across_raters": sum(1 for v in dup.values() if len(v) > 1)}
    (rdir / "RESULT.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({c: {k: v[k] for k in ("W", "L", "T", "U", "cond_win", "fleiss_kappa")} for c, v in out["comparisons"].items()}, ensure_ascii=False))
    print(json.dumps(out["raters"], ensure_ascii=False))


if __name__ == "__main__":
    main()
