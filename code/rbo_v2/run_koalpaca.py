"""Original-submission KoAlpaca bank (350) with the IFEval-locked RBO-T2, transferred unchanged (no tuning on these items).

The user request given to every role is the instruction plus, when present, its input. The single-A.X comparator uses the
same request text and the same decoding (greedy, max 1280 tokens). Outputs are written in the judge runner's `ext:` format
(`rbo_s_v1/runs/orig350_ext_<name>.jsonl`, fields row/text). Usage: python run_koalpaca.py single|rbo
"""
import sys, json
from pathlib import Path
import rbo
from common import chat, journal

BANK = Path(__file__).resolve().parent.parent / "rbo_s_v1" / "bank_orig350.jsonl"
OUT = BANK.parent / "runs"


def request(x):
    return x["instruction"].strip() + (f"\n\n[입력]\n{x['input'].strip()}" if (x.get("input") or "").strip() else "")


def main():
    mode = sys.argv[1]
    name = {"single": "v2single_ax7", "rbo": "rbov2"}[mode]
    items = [json.loads(l) for l in BANK.read_text(encoding="utf-8").splitlines()]
    done, add = journal(OUT / f"orig350_ext_{name}.jsonl")
    for x in items:
        if x["row"] in done:
            continue
        p = request(x)
        if mode == "single":
            try:
                r = chat("ax7", [{"role": "user", "content": p}])
                add({"id": x["row"], "row": x["row"], "text": r["text"], "output_tokens": r["output_tokens"], "seconds": r["seconds"]})
            except Exception as e:
                add({"id": x["row"], "row": x["row"], "text": "", "error": str(e)[:200]})
        else:
            ans, trace, calls = rbo.run_item({"prompt": p, "key": x["row"]}, "T2", "qwen8", "ax7", "qwen8", "qwen8")
            add({"id": x["row"], "row": x["row"], "text": ans, "trace": trace, "calls": calls})
    print(name, len(done))


if __name__ == "__main__":
    main()
