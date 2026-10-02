"""RBO v2 for Korean math word problems (HRM8K GSM8K subset). Same role order as rbo.py:
Planner -> Generator -> Checker -> [if FAIL] Reviser (branch by failure type) -> Checker -> Gate, <= ROUNDS.
- Planner   : lists the given quantities and the asked quantity (with unit), from the problem text only.
- Generator : step-by-step solution ending with '정답: <number>'.
- Checker   : tool 1 (format) = a number can be parsed after '정답:'; tool 2 (verification) = the Checker model writes an
              independent Python program for the problem, executed in a sandboxed subprocess; PASS if the program's
              value equals the Generator's answer.
- Reviser   : format failure -> Extractor asks the Generator model for the final number only;
              disagreement -> Reviser re-solves given both candidate values.
- Gate      : accepts a revision only if it now agrees with the program value; otherwise keeps the previous answer.
Gold answers are used only for scoring after the final answer. Usage:
  python rbo_math.py SPLIT POLICY [models...]
  POLICY: single M | sc M K | sr M | rbo P G C R
"""
import sys, json, re, subprocess, tempfile, os, hashlib, collections
from pathlib import Path
import pandas as pd
from common import HERE, RUNS, chat, journal

DATA = HERE / "data" / "hrm8k" / "gsm8k_test.csv"
ROUNDS = 2
SOLVE = "다음 수학 문제를 단계별로 풀고, 마지막 줄에 '정답: 숫자' 형식으로 최종 답을 숫자만 쓰세요.\n\n[문제]\n{q}"
PLAN = ("다음 수학 문제를 읽고, 문제에 주어진 값들과 구해야 하는 값(단위 포함)을 짧은 목록으로 정리하세요. 문제를 풀지는 마세요.\n\n[문제]\n{q}")
GEN = SOLVE + "\n\n[문제 분석(참고)]\n{plan}"
CODE = ("다음 수학 문제를 푸는 파이썬 코드를 작성하세요. 표준 라이브러리 math, fractions만 사용할 수 있습니다. "
        "최종 답을 변수 answer에 숫자로 저장하세요. 코드만 ```python 블록 하나로 출력하세요.\n\n[문제]\n{q}")
EXTRACT = "[문제]\n{q}\n\n[풀이]\n{sol}\n\n위 풀이의 최종 답을 '정답: 숫자' 형식으로 한 줄만 출력하세요."
RESOLVE = ("[문제]\n{q}\n\n[풀이 A]\n{sol}\n(풀이 A의 답: {a})\n\n[검산 코드 B]\n{code}\n(코드 B의 실행 결과: {b})\n\n"
           "두 답이 다릅니다. 문제 조건을 하나씩 확인하면서 풀이 A와 코드 B 중 어느 쪽이 문제를 올바르게 해석했는지 판단하고, "
           "필요하면 처음부터 다시 풀어 마지막 줄에 '정답: 숫자'를 쓰세요.")  # dev revision 2026-09-27: code shown, 2048 tokens
SR_CRIT = "[문제]\n{q}\n\n[풀이]\n{sol}\n\n위 풀이에 오류가 있는지 검토하고 구체적으로 지적하세요. 오류가 없으면 '수정 불필요'라고만 쓰세요."
SR_REV = "[문제]\n{q}\n\n[이전 풀이]\n{sol}\n\n[검토 의견]\n{crit}\n\n검토 의견을 반영해 다시 단계별로 풀고, 마지막 줄에 '정답: 숫자'를 쓰세요."
ALLOWED_IMPORT = re.compile(r"^\s*(import|from)\s+(math|fractions)\b")


def items():
    d = pd.read_csv(DATA)
    return [{"key": i, "question": r["question"], "gold": float(r["answer"])} for i, r in d.iterrows()]


def split_keys(name):
    return json.loads((HERE / "SPLIT_HRM8K.json").read_text())[name]


def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_answer(text):
    m = re.findall(r"정답\s*[:：]\s*\$?\s*(-?[\d,]*\.?\d+)", text or "")
    return num(m[-1]) if m else None


def same(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b))


def run_code(text):
    """Execute model-written code in an isolated subprocess (python -I, 10 s, temp dir); only math/fractions imports."""
    m = re.search(r"```(?:python)?\s*(.*?)```", text or "", re.S)
    code = m.group(1) if m else (text or "")
    for line in code.splitlines():
        if re.match(r"^\s*(import|from)\s+", line) and not ALLOWED_IMPORT.match(line):
            return None, "disallowed_import"
    if re.search(r"\b(open|exec|eval|__import__|input|os\.|sys\.|subprocess)\b", code):
        return None, "disallowed_call"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.py"
        p.write_text(code + "\n\ntry:\n    print(repr(float(answer)))\nexcept Exception as _e:\n    print('NOANSWER')\n", encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", str(p)], cwd=td, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            return None, "timeout"
    out = (r.stdout or "").strip().splitlines()
    return (num(out[-1]) if out and out[-1] != "NOANSWER" else None), ("ok" if r.returncode == 0 else "error")


class Caller:
    def __init__(self):
        self.calls = []

    def __call__(self, role, mkey, content, max_tokens=1024, temperature=0.0, seed=0):
        try:
            r = chat(mkey, [{"role": "user", "content": content}], max_tokens=max_tokens, temperature=temperature, seed=seed)
        except Exception as e:
            self.calls.append({"role": role, "model": mkey, "error": str(e)[:200], "output_tokens": 0, "seconds": 0})
            return ""
        self.calls.append({"role": role, "model": mkey, "output_tokens": r["output_tokens"], "seconds": r["seconds"]})
        return r["text"]


def rbo(x, P, G, C, R):
    call, q, trace = Caller(), x["question"], []
    plan = call("planner", P, PLAN.format(q=q), 400)
    sol = call("generator", G, GEN.format(q=q, plan=plan))
    ans = parse_answer(sol)
    code = call("checker", C, CODE.format(q=q), 800)
    pv, pstat = run_code(code)
    trace += [{"step": "plan", "text": plan}, {"step": "draft", "answer": ans}, {"step": "program", "value": pv, "status": pstat}]
    for rnd in range(ROUNDS):
        if ans is not None and (pv is None or same(ans, pv)):
            trace.append({"step": "stop", "reason": "agree" if pv is not None else "no_program_value"})
            break
        if ans is None:
            mode, cand_sol = "extract", call("extractor", G, EXTRACT.format(q=q, sol=sol), 60)
            cand = parse_answer(cand_sol)
            accept = cand is not None and (pv is None or same(cand, pv))
        else:
            mode, cand_sol = "resolve", call("reviser", R, RESOLVE.format(q=q, sol=sol, a=f"{ans:g}", code=code, b=f"{pv:g}"), 2048)
            cand = parse_answer(cand_sol)
            accept = same(cand, pv)
        trace.append({"step": f"revise{rnd+1}", "mode": mode, "answer": cand, "accepted": accept})
        if not accept:
            break
        ans, sol = cand, cand_sol
    return ans, trace, call.calls


def single(x, M):
    call = Caller()
    sol = call("generator", M, SOLVE.format(q=x["question"]))
    return parse_answer(sol), [{"step": "solution", "text": sol[-300:]}], call.calls


def sc(x, M, K):
    call = Caller()
    answers = [parse_answer(call("sample", M, SOLVE.format(q=x["question"]), temperature=0.7 if k else 0.0, seed=k)) for k in range(K)]
    valid = [a for a in answers if a is not None]
    if not valid:
        return None, [{"step": "votes", "answers": answers}], call.calls
    cnt = collections.Counter(round(a, 6) for a in valid)
    top = max(cnt.values())
    winner = next(round(a, 6) for a in answers if a is not None and cnt[round(a, 6)] == top)  # ties -> earliest sample (greedy first)
    return winner, [{"step": "votes", "answers": answers}], call.calls


def sr(x, M):
    call, q = Caller(), x["question"]
    sol = call("generator", M, SOLVE.format(q=q))
    for _ in range(ROUNDS):
        crit = call("critic", M, SR_CRIT.format(q=q, sol=sol), 600)
        if "수정 불필요" in crit[:40]:
            break
        new = call("reviser", M, SR_REV.format(q=q, sol=sol, crit=crit))
        sol = new
    return parse_answer(sol), [], call.calls


def main():
    split, policy, *m = sys.argv[1:]
    name = {"single": lambda: f"single_{m[0]}", "sc": lambda: f"sc{m[1]}_{m[0]}", "sr": lambda: f"sr_{m[0]}",
            "rbo": lambda: f"rbo_{'-'.join(m)}"}[policy]()
    keys = set(split_keys(split))
    done, add = journal(RUNS / f"hrm8k_{name}.jsonl")
    for x in items():
        if x["key"] not in keys or x["key"] in done:
            continue
        if policy == "single":
            ans, trace, calls = single(x, m[0])
        elif policy == "sc":
            ans, trace, calls = sc(x, m[0], int(m[1]))
        elif policy == "sr":
            ans, trace, calls = sr(x, m[0])
        else:
            ans, trace, calls = rbo(x, *m)
        add({"id": x["key"], "policy": name, "answer": ans, "correct": same(ans, x["gold"]), "trace": trace, "calls": calls})
    rows = [done[k] for k in keys if k in done]
    print(f"hrm8k {name}", len(rows), "acc", round(sum(r["correct"] for r in rows) / len(rows), 3))


if __name__ == "__main__":
    main()
