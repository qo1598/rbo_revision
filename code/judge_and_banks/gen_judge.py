"""Blind pairwise 3-judge panel (Claude Opus 5, Gemini 3.1 Pro via billing-ai; Grok 4.6 via xAI).

Each judge sees both orders; a judge's label counts only if both orders agree. Panel label = label with
>=2 judge votes; otherwise unresolved. Invalid/missing are never ties. Results cached append-only.
Usage (library): judge_pair(row_item, text_x, text_y) -> dict
"""
import json, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import judge_client as JC

HERE = Path(__file__).resolve().parent
CACHE = HERE / "runs" / "judge_cache.jsonl"
SYSTEM = "당신은 한국어 지시 수행 답변을 공정하게 비교 평가하는 전문 평가자입니다. 모델 이름이나 답변 길이, 제시 순서에 영향을 받지 마세요."
USER = ("[지시문]\n{instruction}\n[입력]\n{input}\n\n[답변 A]\n{a}\n\n[답변 B]\n{b}\n\n"
        "지시문 충족도, 정확성·사실성, 입력 충실도, 형식·개수·길이 준수, 한국어 품질을 종합하여 더 나은 답변을 고르세요. "
        "실질적으로 차이가 없으면 tie를 고르세요. 다른 텍스트 없이 JSON 한 개만 출력하세요: "
        '{{"winner": "A" 또는 "B" 또는 "tie", "reason": "한 문장"}}')
JUDGES = ["claude", "gemini", "kimi"]  # amendment 1 (JUDGE_PANEL_AMENDMENT.md)
_cache = None
import threading
_TLOCK = threading.Lock()


def _h(*xs):
    return hashlib.sha256("␞".join(xs).encode("utf-8")).hexdigest()


def _load():
    global _cache
    if _cache is None:
        _cache = {}
        if CACHE.exists():
            bad = 0
            for l in CACHE.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(l)
                except json.JSONDecodeError:  # interleaved concurrent append (2026-09-25 incident); call is re-asked
                    bad += 1
                    continue
                _cache[r["key"]] = r
            if bad:
                print(f"judge_cache: skipped {bad} malformed line(s)")
    return _cache


def _append(rec):
    """Append one record under an exclusive OS lock so concurrent processes cannot interleave lines."""
    import msvcrt
    line = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
    with _TLOCK, open(CACHE, "ab") as f:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # lock byte 0 (inter-process); append mode writes at end
        try:
            f.write(line)
            f.flush()
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def _ask(judge, item, a, b):
    user = USER.format(instruction=item["instruction"], input=item["input"] or "(없음)", a=a, b=b)
    key = _h(judge, JC.JUDGES[judge]["model"], SYSTEM, user)
    c = _load()
    if key in c and not c[key].get("error"):
        return c[key]  # errored records (e.g., Grok HTTP 403 on exhausted credit, 2026-09-25) are re-asked
    r = JC.chat(judge, SYSTEM, user, max_tokens=4000)
    if str(r.get("error", "")).startswith(("HTTP 401", "HTTP 402", "HTTP 403", "HTTP 429")):
        # fail closed: an account/quota failure must stop the run instead of silently shrinking the panel
        raise SystemExit(f"judge {judge} unavailable: {r['error']}; run halted, rerun after fixing credit/quota")
    label = None
    if "text" in r:
        try:
            w = str(JC.parse_json(r["text"]).get("winner", "")).strip().upper()
            label = {"A": "A", "B": "B", "TIE": "tie"}.get(w)
        except Exception:
            label = None
    rec = {"key": key, "judge": judge, "model": JC.JUDGES[judge]["model"], "label": label,
           "text": r.get("text"), "error": r.get("error"), "usage": r.get("usage"), "seconds": r.get("seconds")}
    _append(rec)
    c[key] = rec
    return rec


def judge_pair(item, x, y):
    """Returns panel label in {'x','y','tie','unresolved'} plus per-judge detail."""
    if x.strip() == y.strip():
        return {"panel": "identical", "judges": {}}
    per = {}

    def run(j):
        r1 = _ask(j, item, x, y)   # A=x
        r2 = _ask(j, item, y, x)   # A=y
        m1 = {"A": "x", "B": "y", "tie": "tie"}.get(r1["label"])
        m2 = {"A": "y", "B": "x", "tie": "tie"}.get(r2["label"])
        return j, (m1 if m1 is not None and m1 == m2 else None), (m1, m2)

    with ThreadPoolExecutor(3) as ex:
        for j, lab, raw in ex.map(run, JUDGES):
            per[j] = {"label": lab, "raw": raw}
    votes = [v["label"] for v in per.values() if v["label"]]
    cnt = {l: votes.count(l) for l in set(votes)}
    panel = next((l for l, n in cnt.items() if n >= 2), "unresolved")
    return {"panel": panel, "judges": per}
