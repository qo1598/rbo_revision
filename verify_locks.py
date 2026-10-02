"""Verify the frozen-protocol lock files against this package.
The package renames the development label of the design to 'RBO v2' (the manuscript's name). RENAMING_PATCHES.json
records every renamed path and replaced span; this script restores each file's original bytes from those records,
checks them against the recorded original SHA-256, and then checks every lock entry against the restored files.

Some locks were superseded by documented amendment locks after the main analysis (for example, the ablation runs added
a branch to the pipeline code and re-locked it). For a superseded lock, files changed by the later amendment are
expected to differ; the analysis that used the earlier lock recorded no drift at the time (`lock_drift: []` in its
result file). The current state must match the latest lock of each chain. Usage: python verify_locks.py"""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUPERSEDED = {"IFEVAL_LOCK.json": "IFEVAL_EXT_LOCK_A2.json", "IFEVAL_EXT_LOCK.json": "IFEVAL_EXT_LOCK_A2.json",
              "IFEVAL_EXT_LOCK_A1.json": "IFEVAL_EXT_LOCK_A2.json", "KOALPACA350_LOCK.json": "KOALPACA350_LOCK_A1.json"}
patches = json.loads((ROOT / "RENAMING_PATCHES.json").read_text(encoding="utf-8"))
renamed = {r["original_path"]: (new, r) for new, r in patches.items()}
current = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
originals = set(renamed) | {p for p in current if p not in patches}


def original_bytes(orig):
    if orig in renamed:
        new, r = renamed[orig]
        raw = (ROOT / new).read_bytes()
        if r["edits"]:
            t = raw.decode("utf-8", "surrogateescape")
            for start, n, old in sorted(r["edits"], key=lambda e: -e[0]):
                t = t[:start] + old + t[start + n:]
            raw = t.encode("utf-8", "surrogateescape")
        assert hashlib.sha256(raw).hexdigest() == r["original_sha256"], f"restore failed: {orig}"
        return raw
    return (ROOT / orig).read_bytes()


def find(f):
    key = f.split("/")[-1] if f.startswith("../") else f
    hits = sorted((o for o in originals if o == key or o.endswith("/" + key)), key=lambda o: (not o.startswith("code/"), len(o)))
    return hits[0] if hits else None


failed = False
for lock in sorted(o for o in originals if Path(o).name.endswith(".json") and "LOCK" in Path(o).name):
    name = Path(lock).name
    entries = json.loads(original_bytes(lock).decode("utf-8"))
    ok, diff, missing = [], [], []
    for f, h in entries.items():
        if f.startswith("_") or not isinstance(h, str) or len(h) != 64:
            continue
        hit = find(f)
        if hit is None:
            missing.append(f)
        elif hashlib.sha256(original_bytes(hit)).hexdigest() == h:
            ok.append(f)
        else:
            diff.append(f)
    status = "OK" if not diff else (f"superseded by {SUPERSEDED[name]}; changed later: {', '.join(diff)}" if name in SUPERSEDED else "MISMATCH: " + ", ".join(diff))
    failed |= bool(diff) and name not in SUPERSEDED
    print(f"{name}: {len(ok)} verified, {len(missing)} not redistributed{(' (' + ', '.join(missing) + ')') if missing else ''} -> {status}")
print("RESULT:", "FAIL" if failed else "all current locks verified")
