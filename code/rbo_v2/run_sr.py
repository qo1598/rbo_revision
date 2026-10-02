"""Compute-comparable control: Self-Refine with one model (generate -> generic critique -> revise, 2 rounds).
No roles, no checklist, no gate. Usage: python run_sr.py SPLIT MODEL_KEY
"""
import sys, json
import score_ifeval as S
from common import HERE, RUNS, chat, journal

ROUNDS = 2
CRIT = ("[사용자 요청]\n{prompt}\n\n[답변]\n{answer}\n\n위 답변이 사용자 요청을 얼마나 잘 따랐는지 검토하고, 개선할 점을 구체적으로 적으세요. "
        "고칠 것이 없으면 '수정 불필요'라고만 쓰세요.")
REV = ("[사용자 요청]\n{prompt}\n\n[현재 답변]\n{answer}\n\n[검토 의견]\n{crit}\n\n검토 의견을 반영해 답변을 고치세요. "
       "수정된 최종 답변만 출력하세요. 설명이나 머리말을 붙이지 마세요.")


def main():
    split, m = sys.argv[1], sys.argv[2]
    keys = set(json.loads((HERE / "SPLIT_IFEVAL.json").read_text())[split])
    done, add = journal(RUNS / f"ifeval_sr_{m}.jsonl")
    for x in S.items():
        if x["key"] not in keys or x["key"] in done:
            continue
        calls, trace = [], []

        def call(role, content, max_tokens=None):
            r = chat(m, [{"role": "user", "content": content}], **({"max_tokens": max_tokens} if max_tokens else {}))
            calls.append({"role": role, "model": m, "prompt_tokens": r["prompt_tokens"], "output_tokens": r["output_tokens"], "seconds": r["seconds"]})
            return r["text"]
        answer = call("generator", x["prompt"])
        trace.append({"step": "draft", "answer": answer})
        for rnd in range(ROUNDS):
            crit = call("critic", CRIT.format(prompt=x["prompt"], answer=answer), 600)
            if "수정 불필요" in crit[:40]:
                trace.append({"step": "stop", "crit": crit})
                break
            answer = call("reviser", REV.format(prompt=x["prompt"], answer=answer, crit=crit))
            trace.append({"step": f"revise{rnd+1}", "crit": crit, "answer": answer})
        add({"id": x["key"], "policy": f"sr_{m}", "text": answer, "trace": trace, "calls": calls, **S.score(x, answer)})
    rows = [done[k] for k in keys if k in done]
    print(f"sr_{m}", len(rows), "strict", round(sum(r["strict"] for r in rows) / len(rows), 3),
          "loose", round(sum(r["loose"] for r in rows) / len(rows), 3))


if __name__ == "__main__":
    main()
