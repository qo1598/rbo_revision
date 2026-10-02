"""Amendment 1 (before any rating): same 175 sampled pairs (SAMPLE.json), split into three blocks balanced by
comparison and category; each block rated by three raters (P01-P09), so every pair still receives three ratings.
Per rater: 3 practice + block core (58-59) + 3 swapped repeats. Reuses build.py loading and HTML. No model calls."""
from __future__ import annotations

import json
from pathlib import Path

import build as B

HERE = B.HERE
OUT = HERE / "packets9"
MAP = HERE / "private" / "mapping9.json"
SEED = "he-2026-10-present-9"
BLOCKS = {"A": ("P01", "P02", "P03"), "B": ("P04", "P05", "P06"), "C": ("P07", "P08", "P09")}
N_REPEAT = 3


def main() -> None:
    if OUT.exists() or MAP.exists():
        raise FileExistsError("9-rater packets already built; do not rebuild after distribution")
    items, texts, _ = B.load()
    sample = json.loads((HERE / "SAMPLE.json").read_text(encoding="utf-8"))
    a_b = B.COMPARISONS
    pairs = []
    for x in sample:
        a, b = a_b[x["comp"]]
        ta, tb = texts[a][x["row"]], texts[b][x["row"]]
        assert B.sha(ta) == x["a_sha256"] and B.sha(tb) == x["b_sha256"], x
        pairs.append({"comp": x["comp"], "row": x["row"], "category": x["category"], "a": ta, "b": tb})
    # block assignment: within each comparison, order by category then hash, deal round-robin with a rotating start
    block_of, names, k = {}, list(BLOCKS), 0
    for comp in a_b:
        group = sorted((p for p in pairs if p["comp"] == comp), key=lambda p: (p["category"], B.sha(f"{SEED}:block:{p['row']}")))
        for p in group:
            block_of[(comp, p["row"])] = names[k % 3]
            k += 1
    used = {x["row"] for x in sample}
    rest = sorted((r for r in items if r not in used), key=lambda r: B.sha(f"{B.SAMPLE_SEED}:practice:{r}"))
    practice = [{"comp": "PRACTICE", "row": r, "a": texts["rbov2"][r], "b": texts["gpt4o_matched"][r]} for r in rest[:B.N_PRACTICE]]
    OUT.mkdir()
    mapping, counts = {}, {}
    for blk, raters in BLOCKS.items():
        bpairs = [p for p in pairs if block_of[(p["comp"], p["row"])] == blk]
        for ri, rater in enumerate(raters):
            core, sides = [], {}
            for comp in a_b:
                group = sorted((p for p in bpairs if p["comp"] == comp), key=lambda p: B.sha(f"{SEED}:{rater}:{comp}:{p['row']}:side"))
                sides[comp] = [0, len(group)]
                for rank, p in enumerate(group):
                    a_left = (rank + ri) % 2 == 0
                    sides[comp][0] += a_left
                    core.append((p, a_left, "core"))
            core.sort(key=lambda x: B.sha(f"{SEED}:{rater}:{x[0]['comp']}:{x[0]['row']}:order"))
            # repeats: three different comparisons, taken from the first half and shown in the last third
            first = core[: len(core) // 2]
            reps, seen = [], set()
            for p, a_left, _ in sorted(first, key=lambda x: B.sha(f"{SEED}:{rater}:{x[0]['row']}:repeat")):
                if p["comp"] not in seen and len(reps) < N_REPEAT:
                    seen.add(p["comp"])
                    reps.append((p, not a_left, "repeat"))
            seq = list(core)
            third = len(seq) * 2 // 3
            for i, r in enumerate(reps):
                seq.insert(third + i * ((len(seq) - third) // (N_REPEAT + 1)) + i, r)
            seq = [(p, (ri + j) % 2 == 0, "practice") for j, p in enumerate(practice)] + seq
            rows = []
            for p, a_left, kind in seq:
                code = B.sha(f"{SEED}:{rater}:{kind}:{p['comp']}:{p['row']}")[:12].upper()
                it = items[p["row"]]
                left, right = (p["a"], p["b"]) if a_left else (p["b"], p["a"])
                mapping[f"{rater}:{code}"] = {"rater": rater, "block": blk, "code": code, "kind": kind, "comp": p["comp"],
                                              "row": p["row"], "item_id": it["item_id"], "category": it["category"],
                                              "a_side": "left" if a_left else "right",
                                              "left_sha256": B.sha(left), "right_sha256": B.sha(right)}
                rows.append({"code": code, "kind": "practice" if kind == "practice" else "main",
                             "instruction": it["instruction"], "input": it["input"], "left": left, "right": right})
            payload = json.dumps({"rater": rater, "rows": rows}, ensure_ascii=False, sort_keys=True)
            psha = B.sha(payload)
            (OUT / f"{rater}_packet.json").write_text(payload, encoding="utf-8")
            (OUT / f"{rater}_평가.html").write_text(B.render(rater, rows, psha), encoding="utf-8")
            counts[rater] = {"block": blk, "practice": len(practice), "core": len(core), "repeat": len(reps), "total": len(rows),
                             "a_left_of_n_by_comp": sides, "packet_sha256": psha}
    MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    blocks = {blk: {c: sum(1 for (cc, _), b in block_of.items() if b == blk and cc == c) for c in a_b} for blk in BLOCKS}
    manifest = {"amendment": "AMENDMENT1_9RATERS.md", "build9_sha256": B.fsha(Path(__file__)), "sample_sha256": B.fsha(HERE / "SAMPLE.json"),
                "blocks": blocks, "raters": counts, "mapping_sha256": B.fsha(MAP),
                "html_sha256": {r: B.fsha(OUT / f"{r}_평가.html") for r in counts}}
    (HERE / "MANIFEST9.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"blocks": blocks, "per_rater": {r: (v["block"], v["core"], v["repeat"], v["total"]) for r, v in counts.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
