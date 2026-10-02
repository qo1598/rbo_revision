"""Recreate the directory layout the analysis scripts expect, from this package, under a target folder.
Usage: python setup_layout.py <target>     (then run the commands in README.md from <target>/revision)
Files are copied, never modified, except that absolute 'C:/rbov2' prefixes in copied scripts are pointed at <target>.
The KorQuAD bank (contexts) is not redistributed; rebuild it with revision/rbo_s_v1/build_korquad_bank.py if needed."""
import shutil, sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
T = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PKG / "layout"
REV = T / "revision"
COPY = [  # (package source, layout destination)
    ("code/rbo_v2", "rbo_v2"), ("protocols/rbo_v2", "rbo_v2"), ("outputs/rbo_v2", "rbo_v2/runs"),
    ("code/judge_and_banks", "rbo_s_v1"), ("data/koalpaca350/bank_orig350.jsonl", "rbo_s_v1/bank_orig350.jsonl"),
    ("outputs/koalpaca350", "rbo_s_v1/runs"), ("judgments/koalpaca350", "rbo_s_v1/runs"),
    ("code/scorer", "experiments/klue_objective/prelaunch"),
    ("code/manuscript", "manuscript_v3"), ("derived", "manuscript_v3"),
    ("code/human_eval", "human_eval_2026_10"), ("protocols/human_eval", "human_eval_2026_10"),
    ("human_eval/returns", "human_eval_2026_10/returns"), ("human_eval/mapping9.json", "human_eval_2026_10/private/mapping9.json"),
    ("data/koalpaca350/KOALPACA_350_SOURCE_ROW_MAP.csv", "reproducibility/KOALPACA_350_SOURCE_ROW_MAP_2026-09-24.csv"),
]
for src, dst in COPY:
    s, d = PKG / src, REV / dst
    if not s.exists():
        print("skip (not in package):", src)
        continue
    if s.is_dir():
        shutil.copytree(s, d, dirs_exist_ok=True)
    else:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
root = T.as_posix()
for f in REV.rglob("*.py"):
    t = f.read_text(encoding="utf-8")
    if "C:/rbov2" in t:
        f.write_text(t.replace("C:/rbov2", root), encoding="utf-8")
print("layout ready under", REV)
