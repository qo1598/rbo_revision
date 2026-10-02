"""Figure: boundary summary for the revised manuscript (fig_boundary.pdf). No model calls.
(a) Paired accuracy difference vs single A.X on the confirmatory splits (percentage points, 95% paired bootstrap CI,
10,000 resamples, seed 20261001) for RBO v2, the compute-comparable control and GPT-4o.
(b) KoAlpaca350 conditional win rate of RBO v2 (three-provider panel) with 95% item bootstrap CI (from
rbo_v2/KOALPACA350_RESULT.json). Palette: dataviz reference slots 1-2 (validated, light mode); GPT-4o in neutral ink."""
import json, random
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent / "rbo_v2"
OUT = Path(__file__).resolve().parent
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d4"


def load(stem, key, keep):
    rows = {}
    for l in (R / "runs" / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(l)
        if x["id"] in keep:
            rows[x["id"]] = float(bool(x[key]))
    return rows


def diff_ci(a, b, seed=20261001, B=10000):
    ids = sorted(set(a) & set(b))
    assert len(ids) == len(a) == len(b), "unpaired"
    d = [a[i] - b[i] for i in ids]
    rnd = random.Random(seed)
    n = len(d)
    bs = sorted(sum(d[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B) - 1]


TASKS = [  # label, split file, key, stems: rbo, single, control (label), gpt4o
    ("IFEval-Ko\n(n=292)", "SPLIT_IFEVAL.json", "strict", "ifeval_rboT2_qwen8-ax7-qwen8-qwen8", "ifeval_single_ax7", ("Self-Refine", "ifeval_sr_ax7"), "ifeval_gpt4o"),
    ("KorQuAD 1.0\n(n=900)", "SPLIT_KORQUAD.json", "em", "korquad_rbo_qwen8-ax7-qwen8-qwen8", "korquad_single_ax7", ("SC3", "korquad_sc3_ax7"), "korquad_gpt4o"),
    ("HRM8K\n(n=400)", "SPLIT_HRM8K.json", "correct", "hrm8k_rbo_qwen8-ax7-qwen8-qwen8", "hrm8k_single_ax7", ("SC3", "hrm8k_sc3_ax7"), "hrm8k_gpt4o"),
]

res = {}
for label, sp, key, rbo, single, (cname, ctrl), g4 in TASKS:
    keep = set(json.loads((R / sp).read_text())["confirm"])
    base = load(single, key, keep)
    res[label] = {"RBO v2": diff_ci(load(rbo, key, keep), base), cname: diff_ci(load(ctrl, key, keep), base),
                  "GPT-4o": diff_ci(load(g4, key, keep), base), "_control": cname}
ko = json.loads((R / "KOALPACA350_RESULT.json").read_text(encoding="utf-8"))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.linewidth": 0.6})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.7), gridspec_kw={"width_ratios": [1.35, 1]})

# (a)
ys = list(range(len(TASKS)))[::-1]
off = {"RBO v2": 0.22, "control": 0.0, "GPT-4o": -0.22}
for y, (label, *_rest) in zip(ys, TASKS):
    r = res[label]
    for name, color, mk, fill in (("RBO v2", BLUE, "o", True), (r["_control"], ORANGE, "s", True), ("GPT-4o", MUTED, "D", False)):
        m, lo, hi = r[name]
        yy = y + off["RBO v2" if name == "RBO v2" else ("GPT-4o" if name == "GPT-4o" else "control")]
        ax1.plot([lo, hi], [yy, yy], color=color, lw=1.6, solid_capstyle="round", zorder=2)
        ax1.plot([m], [yy], marker=mk, ms=6, color=color, mfc=color if fill else "white", mew=1.4, zorder=3)
        if name != "RBO v2":
            ax1.annotate(name, (hi, yy), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7, color=MUTED)
        else:
            ax1.annotate(f"RBO v2  {m:+.1f}", (hi, yy), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7, color=INK)
ax1.axvline(0, color=MUTED, lw=0.8, zorder=1)
ax1.set_yticks(ys)
ax1.set_yticklabels([t[0] for t in TASKS])
ax1.set_xlabel("Accuracy difference vs single A.X (points, 95% CI)")
ax1.set_xlim(-6, 21)
ax1.grid(axis="x", color=GRID, lw=0.5)
ax1.set_axisbelow(True)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)
ax1.set_title("(a) Accuracy benchmarks", loc="left", fontsize=8.5, color=INK)

# (b)
rows = [("vs RBO v1", "rbo_v1_main"), ("vs single A.X", "v2single_ax7"),
        ("vs DeepSeek-V3.2", "deepseek_matched"), ("vs GPT-4o", "gpt4o_matched")]
yb = list(range(len(rows)))[::-1]
for y, (lab, k) in zip(yb, rows):
    v = ko[k]
    lo, hi = v["ci95"]
    ax2.plot([lo, hi], [y, y], color=BLUE, lw=1.6, solid_capstyle="round", zorder=2)
    ax2.plot([v["cond_win"]], [y], "o", ms=6, color=BLUE, zorder=3)
    ax2.annotate(f"{v['cond_win']:.2f}", (hi, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7, color=INK)
ax2.axvline(0.5, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=1)
ax2.set_yticks(yb)
ax2.set_yticklabels([r[0] for r in rows])
ax2.set_xlim(0, 1.05)
ax2.set_xlabel("RBO v2 conditional win rate W/(W+L)")
ax2.grid(axis="x", color=GRID, lw=0.5)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
ax2.set_title("(b) Open-ended KoAlpaca350", loc="left", fontsize=8.5, color=INK)

fig.tight_layout(w_pad=2.0)
fig.savefig(OUT / "fig_boundary.pdf")
fig.savefig(OUT / "fig_boundary.png", dpi=200)
(OUT / "FIG_BOUNDARY_DATA.json").write_text(json.dumps({"accuracy_diff_vs_single_ax": res, "koalpaca": {k: ko[k] for _, k in rows}},
                                                     indent=1, ensure_ascii=False), encoding="utf-8")
for k, v in res.items():
    print(k.replace("\n", " "), {n: tuple(round(x, 1) for x in t) for n, t in v.items() if n != "_control"})
