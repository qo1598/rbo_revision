"""Summarize judge-cache usage for calls added after a timestamp-free baseline (line count). Usage: python judge_usage.py START_LINE"""
import sys, json, collections
C = r"C:/rbov2/revision/rbo_s_v1/runs/judge_cache.jsonl"
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
n = collections.Counter(); err = collections.Counter(); tin = collections.Counter(); tout = collections.Counter()
for i, l in enumerate(open(C, encoding="utf-8")):
    if i < start:
        continue
    try:
        r = json.loads(l)
    except json.JSONDecodeError:
        continue
    j = r["judge"]; n[j] += 1
    if r.get("error"):
        err[j] += 1
    u = r.get("usage") or {}
    tin[j] += u.get("prompt_tokens", 0); tout[j] += u.get("completion_tokens", 0)
PER_CALL = {"claude": 2300, "gemini": 900, "kimi": 2700}  # credits/call, estimated from 2026-09-25/26 billing totals
est = sum(n[j] * PER_CALL.get(j, 0) for j in n)
print({j: {"calls": n[j], "errors": err[j], "in": tin[j], "out": tout[j]} for j in n}, "est_credits", est)
