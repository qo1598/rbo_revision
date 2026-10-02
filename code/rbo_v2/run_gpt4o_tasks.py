"""Frontier reference on HRM8K / KorQuAD with the same single-model prompts (GPT-4o-2024-11-20, temperature 0).
Key read in memory via rbo_s_v1/judge_client; never printed. Usage: python run_gpt4o_tasks.py TASK SPLIT"""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, r"C:/rbov2/revision/rbo_s_v1")
import judge_client as JC
from common import HERE, RUNS, journal

task, split = sys.argv[1], sys.argv[2]
J = JC.JUDGES["gpt4o"]


def ask(prompt, max_tokens):
    body = {"model": J["model"], "temperature": 0, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(J["url"], json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": "Bearer " + JC._key(J["key"])})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):
                raise SystemExit(f"HTTP {e.code}: halt")
            time.sleep(10 * (attempt + 1))
    raise SystemExit("repeated failure: halt")


if task == "hrm8k":
    import rbo_math as T
    keys = set(T.split_keys(split))
    done, add = journal(RUNS / "hrm8k_gpt4o.jsonl")
    for x in T.items():
        if x["key"] in keys and x["key"] not in done:
            out = ask(T.SOLVE.format(q=x["question"]), 1024)
            a = T.parse_answer(out["choices"][0]["message"]["content"])
            add({"id": x["key"], "policy": "gpt4o", "model_returned": out.get("model"), "answer": a, "correct": T.same(a, x["gold"]), "usage": out.get("usage")})
    rows = [done[k] for k in keys]
    print("hrm8k gpt4o", len(rows), "acc", round(sum(r["correct"] for r in rows) / len(rows), 3))
else:
    import rbo_qa as T
    keys = set(json.loads((HERE / "SPLIT_KORQUAD.json").read_text())[split])
    done, add = journal(RUNS / "korquad_gpt4o.jsonl")
    for x in T.items():
        if x["key"] in keys and x["key"] not in done:
            out = ask(T.ANSWER.format(instruction=x["instruction"], context=x["context"]), 128)
            a = T.clean(out["choices"][0]["message"]["content"])
            s = T.official_scores(a, x["answers"])
            add({"id": x["key"], "policy": "gpt4o", "model_returned": out.get("model"), "answer": a, "em": s["em"], "rouge_w": s.get("rouge_w"), "usage": out.get("usage")})
    rows = [done[k] for k in keys]
    print("korquad gpt4o", len(rows), "EM", round(sum(r["em"] for r in rows) / len(rows), 3))
