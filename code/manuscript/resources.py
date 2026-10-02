"""Per-item resource accounting for RBO v2 confirm runs (calls, prompt/output tokens, local seconds) from stored traces.
Reads rbo_v2/runs/*.jsonl restricted to the confirm split IDs; writes RESOURCES_V2.json. No model calls.
Seconds are sequential local wall time on one GPU and include model swaps; they are descriptive, not deployment latency."""
import json, statistics
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "rbo_v2"
SPL = {"ifeval": ("SPLIT_IFEVAL.json", "confirm"), "korquad": ("SPLIT_KORQUAD.json", "confirm"), "hrm8k": ("SPLIT_HRM8K.json", "confirm")}
FILES = {
 "ifeval": {"RBO v2": "ifeval_rboT2_qwen8-ax7-qwen8-qwen8", "single A.X": "ifeval_single_ax7", "single Qwen3-8B": "ifeval_single_qwen8", "Self-Refine A.X": "ifeval_sr_ax7", "RBO v2 (submitted models)": "ifeval_rboT2_midm2-ax7-midm2-hcx3"},
 "korquad": {"RBO v2": "korquad_rbo_qwen8-ax7-qwen8-qwen8", "single A.X": "korquad_single_ax7", "single Qwen3-8B": "korquad_single_qwen8", "SC3 A.X": "korquad_sc3_ax7", "Self-Refine A.X": "korquad_sr_ax7", "RBO v2 (submitted models)": "korquad_rbo_midm2-ax7-midm2-hcx3"},
 "hrm8k": {"RBO v2": "hrm8k_rbo_qwen8-ax7-qwen8-qwen8", "single A.X": "hrm8k_single_ax7", "single Qwen3-8B": "hrm8k_single_qwen8", "SC3 A.X": "hrm8k_sc3_ax7", "Self-Refine A.X": "hrm8k_sr_ax7", "RBO v2 (submitted models)": "hrm8k_rbo_midm2-ax7-midm2-hcx3"},
}
def ids(task):
    f, k = SPL[task]; d = json.loads((R / f).read_text(encoding="utf-8"))
    v = d[k]; return {str(x) for x in v}
out = {}
for task, systems in FILES.items():
    keep = ids(task); out[task] = {}
    for name, stem in systems.items():
        rows = {}
        for l in (R / "runs" / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines():
            x = json.loads(l)
            if str(x["id"]) in keep: rows[str(x["id"])] = x   # last record per id
        for x in rows.values():   # single-call records store usage at top level
            if "calls" not in x:
                x["calls"] = [{"prompt_tokens": x.get("prompt_tokens"), "output_tokens": x.get("output_tokens"), "seconds": x.get("seconds")}]
        calls = [len(x["calls"]) for x in rows.values()]
        otok = [sum(c.get("output_tokens") or 0 for c in x["calls"]) for x in rows.values()]
        ptok = [sum(c.get("prompt_tokens") or 0 for c in x["calls"]) for x in rows.values()]
        has_p = all(all("prompt_tokens" in c for c in x["calls"]) for x in rows.values())
        sec = [sum(c.get("seconds") or 0 for c in x["calls"]) for x in rows.values()]
        out[task][name] = {"n": len(rows), "mean_calls": statistics.mean(calls), "mean_output_tokens": statistics.mean(otok),
                           "mean_prompt_tokens": statistics.mean(ptok) if has_p else None, "mean_local_seconds": statistics.mean(sec)}
(Path(__file__).parent / "RESOURCES_V2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
for t, v in out.items():
    for n, s in v.items(): print(t, n, s["n"], round(s["mean_calls"], 2), round(s["mean_output_tokens"]), s["mean_prompt_tokens"] and round(s["mean_prompt_tokens"]), round(s["mean_local_seconds"], 1))
