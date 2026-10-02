"""RBO-S generative roles: deterministic Validator, consensus (MBR) selector, local Arbiter.

Usage: python gen_select.py BANK   -> runs Arbiter calls (cached) and writes runs/{BANK}_policies.jsonl
"""
import json, re, sys, collections
from pathlib import Path
import propose as P
import propose_gen as PG

HERE = Path(__file__).resolve().parent
POOL = ["ax7", "qwen8", "exaone2", "midm2", "hcx3"]
LEAK = ("[지시문]", "[입력]", "[과업]", "[답변]", "[후보", "[번호]")
NONKO = re.compile(r"영어|english|영문|코드|code|sql|파이썬|python|자바|java|번역|html|css|정규식|수식", re.I)
COUNT = re.compile(r"(\d+)\s*(가지|개의|개를|개)")
LISTLINE = re.compile(r"^\s*(\d+[\.\)]|[-*•])\s+")


def load_props(bank):
    props = collections.defaultdict(dict)
    for m in POOL:
        p = HERE / "runs" / f"{bank}_{m}.jsonl"
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                r = json.loads(l)
                props[r["row"]][m] = r
    return props


def validate(rec, item):
    """Deterministic checks only. Returns (ok, reasons)."""
    reasons = []
    text = (rec or {}).get("response", "") or ""
    t = text.strip()
    if not rec or "error" in rec or len(t) < 10:
        return False, ["empty_or_error"]
    if rec.get("done_reason") == "length":
        reasons.append("truncated")
    if any(s in t for s in LEAK):
        reasons.append("prompt_leak")
    if not NONKO.search(item["instruction"] + item["input"]):
        letters = [c for c in t if c.isalpha()]
        hangul = sum("가" <= c <= "힣" for c in letters)
        if letters and hangul / len(letters) < 0.5:
            reasons.append("not_korean")
    m = COUNT.search(item["instruction"])
    if m:
        n = int(m.group(1))
        items = [l for l in t.split("\n") if LISTLINE.match(l)]
        if len(items) >= 2 and len(items) != n:
            reasons.append(f"count_{len(items)}_ne_{n}")
    return not reasons, reasons


def grams(t, n=3):
    t = re.sub(r"\s+", "", t)
    return collections.Counter(t[i:i + n] for i in range(max(0, len(t) - n + 1)))


def sim(a, b):
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    ov = sum((ga & gb).values())
    return 2 * ov / (sum(ga.values()) + sum(gb.values()))


def mbr(cands, primary):
    """Consensus selector: candidate with highest mean similarity to the other validated candidates."""
    if len(cands) <= 2:
        return primary if primary in cands else next(iter(cands), None)
    score = {m: sum(sim(cands[m], cands[o]) for o in cands if o != m) / (len(cands) - 1) for m in cands}
    best = max(score.values())
    top = [m for m in cands if score[m] == best]
    return primary if primary in top else top[0]


ARB = ("[지시문]\n{instruction}\n[입력]\n{input}\n[후보 답변]\n{options}\n[과업]\n위 지시문에 대해 가장 정확하고, 지시한 형식·개수·길이를 잘 지키며, "
       "입력에 충실하고, 사실 오류나 불필요한 내용이 적은 후보 하나를 고르세요. 번호 하나만 출력하세요.\n[번호]\n")


def arbiter(item, cands, cache):
    names = list(cands)
    picks = []
    for order in (names, list(reversed(names))):
        opts = "\n\n".join(f"<{i+1}>\n{cands[m][:1800]}\n</{i+1}>" for i, m in enumerate(order))
        prompt = ARB.format(instruction=item["instruction"], input=item["input"] or "(없음)", options=opts)
        key = P.sha(prompt)
        if key not in cache:
            out, dt = PG.call(P.MODELS["qwen8"], prompt, 1)
            cache[key] = {"response": out.get("response", ""), "prompt_eval_count": out.get("prompt_eval_count"),
                          "eval_count": out.get("eval_count"), "seconds": round(dt, 3)}
        txt = cache[key]["response"].strip()
        num = next((int(c) for c in txt if c.isdigit()), 0)
        picks.append(order[num - 1] if 1 <= num <= len(order) else None)
    return picks[0] if picks[0] is not None and picks[0] == picks[1] else None, picks


def main():
    bank = sys.argv[1]
    primary = sys.argv[2] if len(sys.argv) > 2 else "ax7"
    items = [json.loads(l) for l in (HERE / f"bank_{bank}.jsonl").read_text(encoding="utf-8").splitlines()]
    props = load_props(bank)
    cpath = HERE / "runs" / f"{bank}_arbiter_cache.json"
    cache = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
    out = []
    for it in items:
        pr = props[it["row"]]
        text = {m: (pr.get(m) or {}).get("response", "").strip() for m in POOL}
        val = {m: validate(pr.get(m), it) for m in POOL}
        cands = {m: text[m] for m in [primary] + [x for x in POOL if x != primary] if val[m][0]}
        fb = next(iter(cands), primary)
        sel_mbr = mbr(cands, primary) or primary
        if len(cands) >= 2:
            a, picks = arbiter(it, cands, cache)
            cpath.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        else:
            a, picks = None, None
        out.append({"row": it["row"], "validity": {m: val[m][1] for m in POOL},
                    "policies": {"single_ax7": "ax7", "single_qwen8": "qwen8", "V_fallback": fb,
                                 "V_mbr": sel_mbr, "V_arbiter": a or sel_mbr},
                    "arbiter_picks": picks})
    (HERE / "runs" / f"{bank}_policies_{primary}.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    c = collections.Counter()
    for x in out:
        for k, v in x["policies"].items():
            c[(k, v)] += 1
    print(sorted(c.items()))


if __name__ == "__main__":
    main()
