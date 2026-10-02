"""Judge RBO-S policy outputs against comparators with the 3-judge panel.

Usage: python gen_eval.py BANK POLICIES_FILE POLICY COMPARATOR [COMPARATOR ...]
  POLICY / COMPARATOR: a policy name in the policies file (resolved to a proposer's text),
  or 'archived:<label>' (orig350 archived outputs), or 'ext:<name>' (runs/{BANK}_ext_<name>.jsonl).
Writes runs/eval_{BANK}_{POLICY}_vs_{COMP}.jsonl and prints W/L/T/U over unique items.
"""
import json, sys, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gen_select as GS
import gen_judge as GJ

HERE = Path(__file__).resolve().parent


def resolver(bank, polfile):
    items = {json.loads(l)["row"]: json.loads(l) for l in (HERE / f"bank_{bank}.jsonl").read_text(encoding="utf-8").splitlines()}
    props = GS.load_props(bank)
    pols = {json.loads(l)["row"]: json.loads(l) for l in (HERE / "runs" / polfile).read_text(encoding="utf-8").splitlines()}
    ext = {}

    def get(row, spec):
        if spec.startswith("archived:"):
            return items[row]["archived"][spec.split(":", 1)[1]]
        if spec.startswith("ext:"):
            name = spec.split(":", 1)[1]
            if name not in ext:
                p = HERE / "runs" / f"{bank}_ext_{name}.jsonl"
                ext[name] = {json.loads(l)["row"]: json.loads(l).get("text", "") for l in p.read_text(encoding="utf-8").splitlines()}
            return ext[name].get(row, "")
        m = pols[row]["policies"][spec]
        return ((props[row].get(m) or {}).get("response") or "").strip()
    return items, get


def main():
    bank, polfile, policy, comps = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    items, get = resolver(bank, polfile)
    for comp in comps:
        out = HERE / "runs" / f"eval_{bank}_{policy.replace(':','-')}_vs_{comp.replace(':','-')}.jsonl"

        def one(row):
            r = GJ.judge_pair(items[row], get(row, policy), get(row, comp))
            return {"row": row, **r}
        rows = list(items)
        shard = __import__("os").environ.get("SHARD")  # "i/n": judge only rows[i::n] to fill the cache in parallel
        if shard:
            i, n = map(int, shard.split("/"))
            rows = rows[i::n]
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(one, rows))
        if shard:
            print(f"shard {shard} done ({len(rows)} rows); rerun without SHARD to write the full result")
            continue
        out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in res), encoding="utf-8")
        c = collections.Counter(x["panel"] for x in res)
        w, l = c["x"], c["y"]
        print(f"{policy} vs {comp}: W/L/T/U/identical = {w}/{l}/{c['tie']}/{c['unresolved']}/{c['identical']}"
              f"  cond.win={w/(w+l) if w+l else float('nan'):.3f}")


if __name__ == "__main__":
    main()
