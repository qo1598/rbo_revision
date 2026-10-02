"""Shared local-model client and journal helpers for the RBO v2 study (Ollama /api/chat, deterministic)."""
import hashlib, json, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
RUNS.mkdir(exist_ok=True)
HOST = "http://127.0.0.1:11434"
MODELS = {
    "ax7": "A.X-4.0-Light-Q5_K_M.gguf:latest",
    "qwen8": "qwen3:8b",
    "qwen4": "qwen3:4b-q4_K_M",  # original hybrid Qwen3-4B (not the 2507 thinking-only tag)
    "qwen1.7": "qwen3:1.7b",
    "exaone8": "exaone3.5:7.8b",
    "exaone2": "exaone3.5:2.4b",
    "midm2": "Midm-2.0-Mini-Instruct-Q5_K_M:latest",
    "hcx3": "hyperclova-3b-Q4_K_M:latest",
}
MAX_TOKENS = 1280  # IFEval-Ko official max_gen_toks


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def chat(mkey, messages, max_tokens=MAX_TOKENS, temperature=0.0, seed=0, fmt=None):
    model = MODELS[mkey]
    body = {"model": model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "seed": seed, "num_ctx": 8192, "num_predict": max_tokens}}
    if model.startswith("qwen3"):
        body["think"] = False
    if fmt:
        body["format"] = fmt  # Ollama constrained decoding (e.g. "json")
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.time()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                out = json.loads(r.read())
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    return {"text": out["message"]["content"], "prompt_tokens": out.get("prompt_eval_count"),
            "output_tokens": out.get("eval_count"), "done_reason": out.get("done_reason"), "seconds": round(time.time() - t, 2)}


def journal(path):
    """Returns (done-dict, append-fn) for an append-only JSONL journal keyed by rec['id']."""
    path = Path(path)
    done = {}
    if path.exists():
        for l in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            done[r["id"]] = r
    f = path.open("a", encoding="utf-8", newline="\n")

    def add(rec):
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        done[rec["id"]] = rec
    return done, add
