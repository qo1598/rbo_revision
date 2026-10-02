"""Judge API client for the RBO-S generative study. Keys are read into memory only; never printed or logged.

Judges: claude-opus-5 and gemini-3-1-pro via billing-ai (OpenAI-compatible), grok-4.6 via xAI direct.
"""
import json, time, urllib.request, urllib.error
from pathlib import Path

ENV = Path(r"C:/rbov2/논문2(역할기반 협업 오케스트레이션을 통한 한국어 과제 성능 평가 — SOTA 모델과의 비교 분석)/.env")
JUDGES = {
    "claude": {"url": "https://billing-ai.doubleze.ro/api/v1/chat/completions", "model": "claude-opus-5", "key": "BILLING_AI_KEY"},
    "gemini": {"url": "https://billing-ai.doubleze.ro/api/v1/chat/completions", "model": "gemini-3-1-pro", "key": "BILLING_AI_KEY"},
    "grok": {"url": "https://api.x.ai/v1/chat/completions", "model": "grok-4.6", "key": "Grok_AI_KEY"},
    "kimi": {"url": "https://billing-ai.doubleze.ro/api/v1/chat/completions", "model": "kimi-k3", "key": "BILLING_AI_KEY"},
    "glm": {"url": "https://billing-ai.doubleze.ro/api/v1/chat/completions", "model": "glm-5-2", "key": "BILLING_AI_KEY"},
    # comparator generators (not judges)
    "gpt4o": {"url": "https://api.openai.com/v1/chat/completions", "model": "gpt-4o-2024-11-20", "key": "Open_AI_KEY"},
    "deepseek": {"url": "https://billing-ai.doubleze.ro/api/v1/chat/completions", "model": "deepseek-v3-2", "key": "BILLING_AI_KEY"},
}


def _key(name):
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise KeyError(name + " missing")


def chat(judge, system, user, max_tokens=600, timeout=180):
    j = JUDGES[judge]
    body = {"model": j["model"], "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(j["url"], json.dumps(body).encode("utf-8"),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + _key(j["key"])})
    t = time.time()
    for attempt in range(4):  # 2026-09-27: transient network errors (e.g. WinError 10060) are retried, then fail closed
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "body": e.read()[:500].decode("utf-8", "ignore"), "seconds": time.time() - t}
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt == 3:
                raise SystemExit(f"network failure after retries ({judge}): {e}; run halted, rerun to resume from cache")
            time.sleep(15 * (attempt + 1))
    ch = (out.get("choices") or [{}])[0]
    msg = (ch.get("message") or {}).get("content") or ""
    if not ch.get("message"):
        return {"error": "no_message", "raw_shape": {k: (v if k != "choices" else [list(c.keys()) for c in v]) for k, v in out.items() if k in ("choices", "usage", "model", "error")}, "seconds": round(time.time() - t, 3)}
    return {"text": msg, "finish_reason": ch.get("finish_reason"), "model_returned": out.get("model"),
            "usage": out.get("usage"), "seconds": round(time.time() - t, 3)}


def parse_json(text):
    """Strict JSON; the only recovery allowed is a single whole-response ```json fence."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines[-1].strip() == "```":
            t = "\n".join(lines[1:-1])
    return json.loads(t)


if __name__ == "__main__":
    for j in JUDGES:
        r = chat(j, "You are a connectivity check.", 'Reply with exactly this JSON: {"ok": true}', max_tokens=2000)
        safe = {k: v for k, v in r.items() if k != "body"}
        if "body" in r:
            safe["body_head"] = r["body"][:200]
        print(j, json.dumps(safe, ensure_ascii=False))
