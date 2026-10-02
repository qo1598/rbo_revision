"""RBO v2 for Korean extractive QA (KorQuAD 1.0 validation bank). Same role order as rbo.py:
Planner -> Generator -> Checker -> [if FAIL] Reviser (branch by failure type) -> Checker -> Gate, <= ROUNDS.
- Planner   : from the question only, states the asked answer type (person/date/number/place/name/...) and clue words.
- Generator : copies the answer span from the passage (answer-only prompt, as in the RBO-S study).
- Checker   : tools (code): grounded = normalized answer occurs in the passage; short = <= 40 characters;
              non_refusal. LLM (Checker model): the answer is of the asked type and answers the question (JSON).
- Reviser   : tool failure (not grounded / too long / refusal) -> Extractor re-copies an exact span;
              type/answer failure -> Reviser re-answers with the Checker's feedback and the plan.
- Gate      : accepts a revision only if the pass count rises and no passed check fails.
Gold answers are used only for scoring (pinned KLUE/KorQuAD EM scorer). Usage:
  python rbo_qa.py SPLIT POLICY [models...]   POLICY: single M | sc M K | sr M | rbo P G C R
"""
import sys, json, re, collections
from pathlib import Path
from common import HERE, RUNS, chat, journal

sys.path.insert(0, str(HERE.parent / "experiments/klue_objective/prelaunch"))
from scorer import normalize, official_scores  # pinned whole-answer EM (same as RBO-S study)

BANK = HERE.parent / "rbo_s_v1" / "bank_korquad.jsonl"
ROUNDS = 2
ANSWER = "[I: 지시문]\n{instruction}\n[입력(있으면)]\n{context}\n[과업]\n위 질문에 대한 정답 문자열만 출력하세요. 설명이나 근거를 덧붙이지 마세요.\n[정답 출력]\n"
PLAN = ("다음 질문이 묻는 답의 종류(예: 인물, 날짜, 수량, 장소, 기관, 작품명, 용어 등)와 본문에서 찾을 때 단서가 될 단어를 "
        "두세 줄로 정리하세요. 답을 추측하지 마세요.\n\n[질문]\n{question}")
GEN = ANSWER + "(참고: 질문 분석) {plan}\n"
CHECK = ("[본문]\n{context}\n\n[질문]\n{question}\n\n[질문 분석]\n{plan}\n\n[답]\n{answer}\n\n"
         "이 답이 질문이 묻는 종류의 답이며 본문에 근거해 질문에 정확히 답하는지 엄격하게 판정하세요. "
         '다른 텍스트 없이 JSON 한 개만 출력하세요: {{"pass": true 또는 false, "why": "짧은 이유"}}')
EXTRACT = ("[본문]\n{context}\n\n[질문]\n{question}\n\n이전 답 '{answer}'은(는) {why}. 본문에 있는 표현을 글자 그대로 짧게 복사해서 "
           "정답 문자열만 출력하세요.")
REANSWER = ("[본문]\n{context}\n\n[질문]\n{question}\n\n[질문 분석]\n{plan}\n\n이전 답 '{answer}'은(는) 다음 이유로 부적절했습니다: {why}\n"
            "본문에서 질문이 묻는 종류의 답을 찾아 본문 표현 그대로 정답 문자열만 출력하세요.")
SR_CRIT = ("[본문]\n{context}\n\n[질문]\n{question}\n\n[답]\n{answer}\n\n이 답이 맞는지 검토하세요. 틀렸다면 이유를 쓰고, 맞으면 '수정 불필요'라고만 쓰세요.")
SR_REV = ("[본문]\n{context}\n\n[질문]\n{question}\n\n[이전 답]\n{answer}\n\n[검토 의견]\n{crit}\n\n검토 의견을 반영해 정답 문자열만 출력하세요.")
REFUSAL = ("확인할 수 없", "제공된 정보", "알 수 없", "없습니다")


def items():
    return [{"key": i, **json.loads(l)} for i, l in enumerate(BANK.read_text(encoding="utf-8").splitlines())]


def clean(text):
    t = (text or "").strip().split("\n")[0].strip()
    for p in ("정답:", "정답 :", "답:", "[정답 출력]"):
        if t.startswith(p):
            t = t[len(p):].strip()
    return t.strip(" \"'“”‘’.")


def tools(ans, x):
    return {"grounded": bool(ans) and normalize(ans).replace(" ", "") in normalize(x["context"]).replace(" ", ""),
            "short": 0 < len(ans) <= 40, "non_refusal": not any(r in ans for r in REFUSAL)}


class Caller:
    def __init__(self):
        self.calls = []

    def __call__(self, role, mkey, content, max_tokens=128, temperature=0.0, seed=0, fmt=None):
        try:
            r = chat(mkey, [{"role": "user", "content": content}], max_tokens=max_tokens, temperature=temperature, seed=seed, fmt=fmt)
        except Exception as e:
            self.calls.append({"role": role, "model": mkey, "error": str(e)[:200], "output_tokens": 0, "seconds": 0})
            return ""
        self.calls.append({"role": role, "model": mkey, "output_tokens": r["output_tokens"], "seconds": r["seconds"]})
        return r["text"]


def rbo(x, P, G, C, R):
    call, trace = Caller(), []
    plan = call("planner", P, PLAN.format(question=x["question"]), 200).strip()
    ans = clean(call("generator", G, GEN.format(instruction=x["instruction"], context=x["context"], plan=plan.replace("\n", " "))))

    def check(a):
        t = tools(a, x)
        why = None
        if all(t.values()):
            raw = call("checker", C, CHECK.format(context=x["context"], question=x["question"], plan=plan, answer=a), 200, fmt="json")
            try:
                j = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
                t["llm"], why = bool(j["pass"]), str(j.get("why", ""))[:200]
            except Exception:
                t["llm"] = None  # unparsable -> no revision is triggered by the LLM check
        else:
            t["llm"] = False
            why = "본문에 그대로 있지 않거나 너무 길거나 답을 거부함"
        return t, why

    res, why = check(ans)
    trace.append({"step": "draft", "answer": ans, "check": res, "plan": plan})
    for rnd in range(ROUNDS):
        fails = [k for k, v in res.items() if v is False]
        if not fails:
            trace.append({"step": "stop", "reason": "all_pass" if res.get("llm") is not None else "checker_unparsable"})
            break
        if not all(res[k] for k in ("grounded", "short", "non_refusal")):
            mode, cand = "extract", clean(call("extractor", G, EXTRACT.format(context=x["context"], question=x["question"], answer=ans, why=why)))
        else:
            mode, cand = "reanswer", clean(call("reviser", R, REANSWER.format(context=x["context"], question=x["question"], plan=plan, answer=ans, why=why)))
        cres, cwhy = check(cand)
        score = lambda r: sum(v is True for v in r.values())
        accept = score(cres) > score(res) and all(cres[k] is True for k, v in res.items() if v is True)
        trace.append({"step": f"revise{rnd+1}", "mode": mode, "answer": cand, "check": cres, "accepted": accept})
        if not accept:
            break
        ans, res, why = cand, cres, cwhy
    return ans, trace, call.calls


def single(x, M):
    call = Caller()
    return clean(call("generator", M, ANSWER.format(instruction=x["instruction"], context=x["context"]))), [], call.calls


def sc(x, M, K):
    call = Caller()
    answers = [clean(call("sample", M, ANSWER.format(instruction=x["instruction"], context=x["context"]), temperature=0.7 if k else 0.0, seed=k)) for k in range(K)]
    c = collections.Counter(normalize(a).replace(" ", "") for a in answers if a)
    if not c:
        return "", [{"step": "votes", "answers": answers}], call.calls
    top = max(c.values())
    win = next(a for a in answers if a and c[normalize(a).replace(" ", "")] == top)  # ties -> earliest (greedy first)
    return win, [{"step": "votes", "answers": answers}], call.calls


def sr(x, M):
    call = Caller()
    ans = clean(call("generator", M, ANSWER.format(instruction=x["instruction"], context=x["context"])))
    for _ in range(ROUNDS):
        crit = call("critic", M, SR_CRIT.format(context=x["context"], question=x["question"], answer=ans), 300)
        if "수정 불필요" in crit[:40]:
            break
        ans = clean(call("reviser", M, SR_REV.format(context=x["context"], question=x["question"], answer=ans, crit=crit)))
    return ans, [], call.calls


def main():
    split, policy, *m = sys.argv[1:]
    name = {"single": lambda: f"single_{m[0]}", "sc": lambda: f"sc{m[1]}_{m[0]}", "sr": lambda: f"sr_{m[0]}",
            "rbo": lambda: f"rbo_{'-'.join(m)}"}[policy]()
    keys = set(json.loads((HERE / "SPLIT_KORQUAD.json").read_text())[split])
    done, add = journal(RUNS / f"korquad_{name}.jsonl")
    for x in items():
        if x["key"] not in keys or x["key"] in done:
            continue
        fn = {"single": lambda: single(x, m[0]), "sc": lambda: sc(x, m[0], int(m[1])), "sr": lambda: sr(x, m[0]),
              "rbo": lambda: rbo(x, *m)}[policy]
        ans, trace, calls = fn()
        s = official_scores(ans, x["answers"])
        add({"id": x["key"], "policy": name, "answer": ans, "em": s["em"], "rouge_w": s.get("rouge_w"), "trace": trace, "calls": calls})
    rows = [done[k] for k in keys if k in done]
    print(f"korquad {name}", len(rows), "EM", round(sum(r["em"] for r in rows) / len(rows), 3))


if __name__ == "__main__":
    main()
