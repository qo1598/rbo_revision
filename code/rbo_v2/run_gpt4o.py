"""Frontier reference: GPT-4o-2024-11-20 on IFEval-Ko with the official prompt only (temperature 0, max 1280).
Key read in memory from the project .env (via rbo_s_v1/judge_client), never printed. Usage: python run_gpt4o.py SPLIT"""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, r"C:/rbov2/revision/rbo_s_v1")
import judge_client as JC
import score_ifeval as S
from common import HERE, RUNS, journal

split = sys.argv[1]
keys = set(json.loads((HERE / "SPLIT_IFEVAL.json").read_text())[split])
done, add = journal(RUNS / "ifeval_gpt4o.jsonl")
J = JC.JUDGES["gpt4o"]
for x in S.items():
    if x["key"] not in keys or x["key"] in done:
        continue
    body = {"model": J["model"], "temperature": 0, "max_tokens": 1280, "messages": [{"role": "user", "content": x["prompt"]}]}
    req = urllib.request.Request(J["url"], json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": "Bearer " + JC._key(J["key"])})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):
                raise SystemExit(f"HTTP {e.code}: halt")
            time.sleep(10 * (attempt + 1))
    text = out["choices"][0]["message"]["content"]
    add({"id": x["key"], "policy": "gpt4o", "model_returned": out.get("model"), "text": text, "usage": out.get("usage"), **S.score(x, text)})
rows = [done[k] for k in keys if k in done]
print("gpt4o", len(rows), "strict", round(sum(r["strict"] for r in rows) / len(rows), 3))
