"""Post hoc sensitivity of the human evaluation (no model calls): item verdicts recomputed without the rater with the
fastest viewing times (P02); for block-A pairs the two remaining ratings must then agree. Writes HUMAN_SENSITIVITY.json."""
import collections, glob, json
from math import comb
from pathlib import Path
HE = Path(__file__).resolve().parent.parent / "human_eval_2026_10"
m = json.loads((HE / "private" / "mapping9.json").read_text(encoding="utf-8"))
votes = collections.defaultdict(list)
for f in glob.glob(str(HE / "returns" / "P0*.json")):
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    for x in d["ratings"]:
        mm = m[f"{d['rater']}:{x['code']}"]
        if mm["kind"] != "core" or d["rater"] == "P02":
            continue
        lab = x.get("label") or ""
        dec = {"left": "A" if mm["a_side"] == "left" else "B", "right": "A" if mm["a_side"] == "right" else "B", "tie": "tie"}.get(lab)
        votes[(mm["comp"], mm["row"])].append(dec)
out = {}
for comp in ("O1", "O2", "R1", "R2", "R3"):
    c = collections.Counter()
    for (cc, _), v in votes.items():
        if cc == comp:
            c[next((k for k in ("A", "B", "tie") if v.count(k) >= 2), "U")] += 1
    w, l = c["A"], c["B"]
    p = min(1.0, 2 * sum(comb(w + l, i) for i in range(min(w, l) + 1)) / 2 ** (w + l))
    out[comp] = {"W": w, "L": l, "T": c["tie"], "U": c["U"], "cond_win": w / (w + l), "sign_p": p}
(Path(__file__).parent / "HUMAN_SENSITIVITY.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(out)
