"""RBO v2: role-based orchestration with explicit roles, fixed order and conditional branching.

Controller:  Planner -> Generator -> Checker -> [if any FAIL] Reviser -> Checker -> Gate -> (repeat <= ROUNDS)
- Planner   : reads ONLY the user prompt; lists each explicit requirement with a verbatim quote from the prompt and,
              when the requirement is measurable, a call to one of the generic text tools below. Requirements whose
              quote is not found in the prompt are discarded in code (guard against invented requirements).
- Generator : answers the prompt, given the validated requirement list.
- Checker   : variant T: tool requirements are measured in code, the rest judged by the Checker LLM.
              variant L: every requirement judged by the Checker LLM (ablation of the tools).
- Reviser   : rewrites the answer fixing ONLY the failed requirements (with the measured values), keeping the rest.
- Variant T2: the Reviser branches by failure type: only "at least" word/sentence shortfalls -> Extender (Generator
              model) appends a continuation; any other failure -> Reviser regenerates the answer with the failure feedback.
- Gate      : accepts a revision only if the pass count strictly increases and no passed requirement fails (do-no-harm).
No dataset labels (instruction_id_list/kwargs) and no official scorer are used inside the pipeline.
Usage: python rbo.py SPLIT VARIANT(L|T) PLANNER GENERATOR CHECKER REVISER
"""
import sys, json, re
import score_ifeval as S
from common import HERE, RUNS, chat, journal

ROUNDS = 2
TOOLS_DOC = """사용 가능한 측정 도구(해당될 때만 사용, 아니면 null):
- word_count {"op": ">=|<=|==|>|<", "n": 정수}   (띄어쓰기 기준 단어 수)
- sentence_count {"op", "n"}
- paragraph_count {"op", "n"}   (빈 줄 또는 *** 로 구분된 문단 수)
- bullet_count {"op", "n"}   (* 또는 - 로 시작하는 목록 줄 수)
- highlight_count {"op", "n"}   (*강조* 형태의 마크다운 강조 구간 수)
- placeholder_count {"op", "n"}   ([이름] 형태의 대괄호 자리표시자 수)
- keyword_count {"word": 단어, "op", "n"}   (단어 등장 횟수)
- forbidden_words {"words": [단어, ...]}
- no_char {"char": 문자}
- starts_with {"text": 문구}
- ends_with {"text": 문구}
- wrapped_in {"left": 문자, "right": 문자}
- contains_text {"text": 문구}
- json_valid {}
범위 조건(예: 10에서 20 단어)처럼 여러 측정이 모두 맞아야 하면 tool에 도구 호출의 목록을 적으세요: [{"name": ..., "args": ...}, {"name": ..., "args": ...}]"""
PLAN_EXAMPLE = {'reqs': [{'quote': '고양이에 대한 짧은 시를 써 주세요', 'desc': '고양이에 대한 짧은 시', 'tool': None}, {'quote': '제목은 없이', 'desc': '제목을 달지 않는다', 'tool': None}, {'quote': '정확히 4개의 문단으로', 'desc': '문단은 정확히 4개', 'tool': {'name': 'paragraph_count', 'args': {'op': '==', 'n': 4}}}, {'quote': "'행복'이라는 단어를 2번 이상", 'desc': '행복을 2번 이상 사용', 'tool': {'name': 'keyword_count', 'args': {'word': '행복', 'op': '>=', 'n': 2}}}]}
PLAN = ("""당신은 요구사항 분석가입니다. 아래 <요청>을 읽고, 답변이 지켜야 하는 명시적 요구사항을 빠짐없이 뽑으세요.
- 각 요구사항마다 <요청> 안에 실제로 있는 구절을 글자 그대로 quote에 인용하세요. <요청>에 없는 요구사항은 만들지 마세요.
- 무엇에 대해 쓰라는지(주제/과업)도 하나의 요구사항으로 넣으세요.
- 측정할 수 있는 요구사항이면 tool에 도구 호출을 적고, 아니면 null로 두세요.

""" + TOOLS_DOC + """

[예시]
<요청>
고양이에 대한 짧은 시를 써 주세요. 제목은 없이, 정확히 4개의 문단으로 쓰고 '행복'이라는 단어를 2번 이상 쓰세요.
</요청>
""" + json.dumps(PLAN_EXAMPLE, ensure_ascii=False) + """

[실제 과제]
<요청>
<<PROMPT>>
</요청>
다른 텍스트 없이 JSON 한 개만 출력하세요.""")
GEN = "{prompt}\n\n(참고: 답변은 아래 요구사항을 모두 지켜야 합니다. 요구사항 목록 자체는 출력하지 마세요.)\n{reqs}"
CHECK = ("[사용자 요청]\n{prompt}\n\n[답변]\n{answer}\n\n[판정할 요구사항]\n{reqs}\n\n"
         "각 요구사항을 답변이 지켰는지 엄격하게 판정하세요. 조금이라도 어기면 false입니다. 다른 텍스트 없이 JSON 한 개만 출력하세요:\n"
         '{{"items": [{{"n": 번호, "pass": true 또는 false}}, ...]}}')
REVISE = ("[사용자 요청]\n{prompt}\n\n[현재 답변]\n{answer}\n\n[지키지 못한 요구사항]\n{fails}\n\n"
          "위 답변을 고쳐서 지키지 못한 요구사항을 모두 만족시키세요. 이미 지킨 요구사항과 내용은 유지하세요.\n"
          "수정된 최종 답변만 출력하세요. 설명이나 머리말을 붙이지 마세요.")
# Variant T2 (dev revision 2026-09-26): the Reviser branches by failure type.
REGEN = ("{prompt}\n\n(주의: 이전 답변은 다음 요구사항을 지키지 못했습니다. 이번에는 반드시 지키세요.)\n{fails}\n"
         "(다른 요구사항도 모두 지키세요.)\n{reqs}")
EXTEND = ("[사용자 요청]\n{prompt}\n\n[지금까지 쓴 답변]\n{answer}\n\n위 답변은 {what}이(가) 부족합니다(현재 {cur}, 필요 {need} 이상). "
          "같은 형식과 어조로 내용을 자연스럽게 이어서 최소 {add} 이상 더 쓰세요. 이미 쓴 부분은 다시 쓰지 말고, 이어질 새 부분만 출력하세요.\n"
          "다른 요구사항도 지키세요:\n{reqs}")
EXTENDABLE = {"word_count": "단어 수", "sentence_count": "문장 수"}
OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "==": lambda a, b: a == b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def _norm(s):
    return re.sub(r"\s+", "", s)


def measure(name, a, text):
    """Generic text tools. Returns (value_description, passed) or None if the call is malformed."""
    t = text.strip()
    try:
        if name in ("word_count", "sentence_count", "paragraph_count", "bullet_count", "highlight_count", "placeholder_count"):
            v = {"word_count": lambda: len(t.split()),
                 "sentence_count": lambda: len([s for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]),
                 "paragraph_count": lambda: len([p for p in re.split(r"\n\s*\n|\n\s*\*\*\*\s*\n", t) if p.strip() and p.strip() != "***"]),
                 "bullet_count": lambda: len([l for l in t.split("\n") if re.match(r"^\s*[*-]\s+", l)]),
                 "highlight_count": lambda: len(re.findall(r"\*[^\n*]+\*", t)),
                 "placeholder_count": lambda: len(re.findall(r"\[[^\]\n]+\]", t))}[name]()
            return f"{v}", OPS[a["op"]](v, int(a["n"]))
        if name == "keyword_count":
            v = t.count(a["word"])
            return f"{v}회", OPS[a["op"]](v, int(a["n"]))
        if name == "forbidden_words":
            hit = [w for w in a["words"] if w and w in t]
            return f"포함된 금지어: {hit}", not hit
        if name == "no_char":
            v = t.count(a["char"])
            return f"{v}개", v == 0
        if name == "starts_with":
            return f"시작: {t[:30]!r}", t.startswith(a["text"])
        if name == "ends_with":
            return f"끝: {t[-30:]!r}", t.endswith(a["text"])
        if name == "wrapped_in":
            return f"처음/끝 문자: {t[:1]!r}/{t[-1:]!r}", t.startswith(a["left"]) and t.endswith(a["right"])
        if name == "contains_text":
            return "포함" if a["text"] in t else "없음", a["text"] in t
        if name == "json_valid":
            u = re.sub(r"^```(json)?\s*|\s*```$", "", t)
            try:
                json.loads(u)
                return "파싱 성공", True
            except Exception:
                return "파싱 실패", False
    except Exception:
        return None
    return None


def plan_reqs(raw, prompt):
    """Validate Planner output: keep requirements whose quote occurs in the prompt; keep well-formed tool calls."""
    try:
        reqs = (_json(raw) or {}).get("reqs") or []
    except Exception:
        return [], "unparsable"
    keep = []
    if not isinstance(reqs, list):
        reqs = []
    for r in reqs:
        if not isinstance(r, dict):  # robustness fix 2026-09-26 (Midm emitted plain strings); such entries are dropped
            continue
        q = str(r.get("quote") or "")
        if not q or _norm(q) not in _norm(prompt):
            continue
        tool = r.get("tool")
        tool = [tool] if isinstance(tool, dict) else (tool if isinstance(tool, list) else [])
        tool = [t for t in tool if isinstance(t, dict)]
        if not tool or any(measure(t.get("name"), t.get("args") or {}, "테스트") is None for t in tool):
            tool = None  # absent or malformed call -> judged by the Checker LLM
        keep.append({"desc": str(r.get("desc") or q), "quote": q, "tool": tool})
    return keep, f"{len(keep)}/{len(reqs)} kept"


def run_item(x, variant, P, G, C, R):
    calls = []

    def call(role, mkey, content, max_tokens=None, fmt=None):
        try:
            r = chat(mkey, [{"role": "user", "content": content}], fmt=fmt, **({"max_tokens": max_tokens} if max_tokens else {}))
        except Exception as e:  # robustness fix 2026-09-26: a failed call yields "" (planner: no reqs; generator: empty
            # answer, scored as failure; checker: unparsable -> stop; reviser/extender: candidate rejected by the gate)
            calls.append({"role": role, "model": mkey, "error": str(e)[:200], "prompt_tokens": 0, "output_tokens": 0, "seconds": 0})
            return ""
        calls.append({"role": role, "model": mkey, "prompt_tokens": r["prompt_tokens"], "output_tokens": r["output_tokens"], "seconds": r["seconds"]})
        return r["text"]

    def check(ans):
        res, notes, llm_idx = {}, {}, []
        for i, r in enumerate(reqs, 1):
            if variant.startswith("T") and r["tool"]:
                ms = [measure(t["name"], t.get("args") or {}, ans) for t in r["tool"]]
                notes[i], res[i] = "; ".join(m[0] for m in ms), all(m[1] for m in ms)
            else:
                llm_idx.append(i)
        if llm_idx:
            txt = call("checker", C, CHECK.format(prompt=x["prompt"], answer=ans,
                                                 reqs="\n".join(f"{i}. {reqs[i-1]['desc']}" for i in llm_idx)), 600)
            try:
                got = {int(it["n"]): bool(it["pass"]) for it in _json(txt)["items"]}
            except Exception:
                return None, notes
            for i in llm_idx:
                if i not in got:
                    return None, notes
                res[i] = got[i]
        return res, notes

    raw = call("planner", P, PLAN.replace("<<PROMPT>>", x["prompt"]), 1000, "json")
    reqs, pstat = plan_reqs(raw, x["prompt"])
    rtxt = "\n".join(f"- {r['desc']}" for r in reqs)
    answer = call("generator", G, GEN.format(prompt=x["prompt"], reqs=rtxt) if reqs else x["prompt"])
    trace = [{"step": "plan", "raw": raw, "reqs": reqs, "stat": pstat}, {"step": "draft", "answer": answer}]
    if not reqs:
        trace.append({"step": "stop", "reason": "no_valid_reqs"})
        return answer, trace, calls
    res, notes = check(answer)
    trace[-1].update(check=res, notes=notes)
    for rnd in range(ROUNDS):
        if res is None:
            trace.append({"step": "stop", "reason": "checker_unparsable"})
            break
        fails = [i for i, ok in res.items() if not ok]
        if not fails:
            trace.append({"step": "stop", "reason": "all_pass"})
            break
        ftxt = "\n".join(f"- {reqs[i-1]['desc']}" + (f" (현재 측정값: {notes[i]})" if i in notes else "") for i in fails)
        mode = "revise"
        if variant in ("T2", "L2"):  # L2 (ablation, added after the T2 lock): no tools, so no extend branch
            short = [] if variant == "L2" else [(i, t) for i in fails if reqs[i-1]["tool"] for t in reqs[i-1]["tool"]
                     if t["name"] in EXTENDABLE and t["args"].get("op") in (">=", ">")
                     and not measure(t["name"], t["args"], answer)[1]]
            others = [i for i in fails if i not in {i for i, _ in short}]
            rall = "\n".join(f"- {q['desc']}" for q in reqs)
            if short and not others:
                mode = "extend"
                i, t = short[0]
                cur, need = int(measure(t["name"], t["args"], answer)[0]), int(t["args"]["n"]) + (t["args"]["op"] == ">")
                add = call("extender", G, EXTEND.format(prompt=x["prompt"], answer=answer, what=EXTENDABLE[t["name"]],
                                                       cur=cur, need=need, add=int((need - cur) * 1.2) + 1, reqs=rall))
                cand = answer.rstrip() + "\n\n" + add.strip()
            else:
                mode = "regenerate"
                cand = call("reviser", R, REGEN.format(prompt=x["prompt"], fails=ftxt, reqs=rall))
        else:
            cand = call("reviser", R, REVISE.format(prompt=x["prompt"], answer=answer, fails=ftxt))
        cres, cnotes = check(cand)
        accept = (cres is not None and sum(cres.values()) > sum(res.values())
                  and all(cres.get(i, False) for i, ok in res.items() if ok))
        trace.append({"step": f"revise{rnd+1}", "mode": mode, "answer": cand, "check": cres, "notes": cnotes, "accepted": accept})
        if not accept:
            break
        answer, res, notes = cand, cres, cnotes
    return answer, trace, calls


def main():
    split, variant, P, G, C, R = sys.argv[1:7]
    keys = set(json.loads((HERE / "SPLIT_IFEVAL.json").read_text())[split])
    name = f"rbo{variant}_{P}-{G}-{C}-{R}"
    done, add = journal(RUNS / f"ifeval_{name}.jsonl")
    for x in S.items():
        if x["key"] not in keys or x["key"] in done:
            continue
        answer, trace, calls = run_item(x, variant, P, G, C, R)
        add({"id": x["key"], "policy": name, "text": answer, "trace": trace, "calls": calls, **S.score(x, answer)})
    rows = [done[k] for k in keys if k in done]
    print(name, len(rows), "strict", round(sum(r["strict"] for r in rows) / len(rows), 3),
          "loose", round(sum(r["loose"] for r in rows) / len(rows), 3))


if __name__ == "__main__":
    main()
