"""Single-model baseline: the IFEval-Ko prompt as the sole user message (official protocol), greedy.
Usage: python run_single.py SPLIT MODEL_KEY
"""
import sys, json
import score_ifeval as S
from common import HERE, RUNS, chat, journal

split, mkey = sys.argv[1], sys.argv[2]
keys = set(json.loads((HERE / "SPLIT_IFEVAL.json").read_text())[split])
done, add = journal(RUNS / f"ifeval_single_{mkey}.jsonl")
for x in S.items():
    if x["key"] not in keys or x["key"] in done:
        continue
    try:
        r = chat(mkey, [{"role": "user", "content": x["prompt"]}])
    except Exception as e:  # amendment 2: same failure handling as RBO (failed call -> empty answer, scored as failure)
        r = {"text": "", "error": str(e)[:200], "prompt_tokens": 0, "output_tokens": 0, "done_reason": "error", "seconds": 0}
    sc = S.score(x, r["text"])
    add({"id": x["key"], "policy": f"single_{mkey}", **r, **sc})
rows = [done[k] for k in keys if k in done]
print(mkey, len(rows), "strict", round(sum(r["strict"] for r in rows) / len(rows), 3), "loose", round(sum(r["loose"] for r in rows) / len(rows), 3))
