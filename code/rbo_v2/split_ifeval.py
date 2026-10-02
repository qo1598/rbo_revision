"""Freeze IFEval-Ko dev/confirm split before any design tuning.

Stratified by the first sorted instruction type; within a stratum, items are ordered by salted SHA-256 and the
first k go to dev, with k allocated proportionally (largest remainder) so that |dev| = 50.
Revision 2026-09-26: dev reduced from 101 (30%) to 50 at the user's request to enlarge confirm. Because the salt
and ordering are unchanged and every k <= the old per-stratum dev count, the new dev is a subset of the old dev;
no item that enters confirm was used for any design decision (only 10 single-A.X baseline outputs existed).
"""
import json, collections, hashlib
import score_ifeval as S
from common import HERE

SALT = "rbo-v3-ifeval-split-20260926"
N_DEV = 50
items = S.items()
strata = collections.defaultdict(list)
for x in items:
    strata[sorted(x["instruction_id_list"])[0]].append(x)
quota = {k: N_DEV * len(v) / len(items) for k, v in strata.items()}
alloc = {k: int(q) for k, q in quota.items()}
for k in sorted(quota, key=lambda k: (-(quota[k] - alloc[k]), k))[:N_DEV - sum(alloc.values())]:
    alloc[k] += 1
old = set(json.loads((HERE / "SPLIT_IFEVAL.superseded_dev101.json").read_text())["dev"])
dev, confirm = [], []
for k in sorted(strata):
    xs = sorted(strata[k], key=lambda x: hashlib.sha256(f"{SALT}|{x['key']}".encode()).hexdigest())
    dev += [x["key"] for x in xs[:alloc[k]]]
    confirm += [x["key"] for x in xs[alloc[k]:]]
assert set(dev) <= old, "new dev must be a subset of the superseded dev"
out = {"salt": SALT, "source": "allganize/IFEval-Ko data/train-00000-of-00001.parquet",
       "parquet_sha256": hashlib.sha256((HERE / "data" / "ifeval_ko.parquet").read_bytes()).hexdigest(),
       "n_total": len(items), "dev": sorted(dev), "confirm": sorted(confirm)}
(HERE / "SPLIT_IFEVAL.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print(len(dev), len(confirm))
