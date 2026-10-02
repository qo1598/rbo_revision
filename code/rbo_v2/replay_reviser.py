"""Dev-only diagnostic: replay the Reviser on saved RBO-T drafts whose tool-checked requirements failed.
Compares reviser prompt/model variants using the pipeline's own tools (not the official scorer) for acceptance,
and reports the official strict score only as a diagnostic."""
import json, sys
import rbo, score_ifeval as S
from common import HERE, RUNS, chat

GAP = ("[사용자 요청]\n{prompt}\n\n[현재 답변]\n{answer}\n\n[지키지 못한 요구사항과 현재 측정값]\n{fails}\n\n"
       "지키지 못한 요구사항을 반드시 만족하도록 답변을 고치세요. 측정값과 목표의 차이를 확인하고 필요한 만큼 충분히 늘리거나 줄이세요. "
       "이미 지킨 요구사항은 유지하세요. 수정된 최종 답변만 출력하세요.")
REGEN = ("{prompt}\n\n(주의: 이전 답변은 다음 요구사항을 지키지 못했습니다. 이번에는 반드시 지키세요.)\n{fails}\n"
         "(다른 요구사항도 모두 지키세요.)\n{reqs}")


def gap_text(r, note):
    return f"- {r['desc']} (현재 측정값: {note}; 목표: " + ", ".join(f"{t['name']} {t['args'].get('op','')} {t['args'].get('n', t['args'].get('word',''))}" for t in r["tool"]) + ")"


def main(variant, mkey):
    dev = set(json.loads((HERE / "SPLIT_IFEVAL.json").read_text())["dev"])
    it = {x["key"]: x for x in S.items()}
    rows = [json.loads(l) for l in open(RUNS / "ifeval_rboT_qwen8-ax7-qwen8-ax7.jsonl", encoding="utf-8")]
    n = fixed = strict = 0
    for r in rows:
        if r["id"] not in dev:
            continue
        tr = r["trace"]; d = next(t for t in tr if t["step"] == "draft")
        chk, notes = d.get("check"), d.get("notes") or {}
        if not chk:
            continue
        reqs = tr[0]["reqs"]
        fails = [int(i) for i, ok in chk.items() if not ok and reqs[int(i) - 1]["tool"]]
        if not fails:
            continue
        x = it[r["id"]]
        ftxt = "\n".join(gap_text(reqs[i - 1], notes[str(i)]) for i in fails)
        if variant == "gap":
            p = GAP.format(prompt=x["prompt"], answer=d["answer"], fails=ftxt)
        else:
            p = REGEN.format(prompt=x["prompt"], fails=ftxt, reqs="\n".join(f"- {q['desc']}" for q in reqs))
        out = chat(mkey, [{"role": "user", "content": p}])["text"]
        ok = all(all(rbo.measure(t["name"], t["args"], out)[1] for t in reqs[i - 1]["tool"]) for i in fails)
        tools_all = all(all(rbo.measure(t["name"], t["args"], out)[1] for t in q["tool"]) for q in reqs if q["tool"])
        n += 1; fixed += ok and tools_all; strict += S.score(x, out)["strict"]
        print(r["id"], "fixed" if ok else "not", [rbo.measure(t["name"], t["args"], out)[0] for i in fails for t in reqs[i - 1]["tool"]])
    print(variant, mkey, "n", n, "tool-fixed", fixed, "official-strict", strict)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
