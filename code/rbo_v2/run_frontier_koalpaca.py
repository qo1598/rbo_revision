"""Matched-prompt frontier outputs for the KoAlpaca350 bank (Amendment 1). Usage: python run_frontier_koalpaca.py gpt4o|deepseek
Same request text as RBO v2 / single A.X, no system prompt, temperature 0, max 1,280 tokens. Keys read in memory only."""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, r"C:/rbov2/revision/rbo_s_v1")
import judge_client as JC
import run_koalpaca as K
from common import journal

client = sys.argv[1]
J = JC.JUDGES[client]
items = [json.loads(l) for l in K.BANK.read_text(encoding="utf-8").splitlines()]
done, add = journal(K.OUT / f"orig350_ext_{client}_matched.jsonl")
for x in items:
    if x["row"] in done:
        continue
    body = {"model": J["model"], "temperature": 0, "max_tokens": 1280, "messages": [{"role": "user", "content": K.request(x)}]}
    req = urllib.request.Request(J["url"], json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": "Bearer " + JC._key(J["key"])})
    out = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):
                raise SystemExit(f"HTTP {e.code}: halt")
            time.sleep(10 * (attempt + 1))
    if out is None:
        raise SystemExit("repeated failure: halt")
    add({"id": x["row"], "row": x["row"], "text": out["choices"][0]["message"]["content"], "model_returned": out.get("model"), "usage": out.get("usage")})
print(client, len(done))
