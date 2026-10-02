"""Bind the submitted 350-item KoAlpaca bank to archived comparator outputs (hash-verified), no model calls."""
import csv, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REV = HERE.parent
P2 = REV.parent / "논문2(역할기반 협업 오케스트레이션을 통한 한국어 과제 성능 평가 — SOTA 모델과의 비교 분석)"
FILES = {  # label: (path, expected sha256 recorded in revision/human_eval/VALIDATION_REPORT.md)
    "rbo_v1_main": (P2 / "부록/RBC_outputs.jsonl", "32704fc3d99d22115b0ee4ea13fc16c79c6d5ad28460fa6f9b68991349ab20ca"),
    "gpt4o_archived": (P2 / "rbo/runs_gpt4o/SOTA_gpt4o_outputs.jsonl", "e26937528d53ea2f1b6bdbbdc77bbda50c149fb37dbae748cfa54e5e6d81c989"),
    "deepseek_archived": (P2 / "rbo/runs_ds/SOTA_deepseek_outputs.jsonl", "4ac2b74d38eb0bea27178d561b1f72e73fb5fe467dc599eb7229c79db30a19c5"),
    "rbo_v1_ds_run": (P2 / "rbo/runs_ds/RBO_audit.jsonl", "6670f7e8aa65ee406a77335022ed60c65a51ddd7c738c39ac294204337889048"),
}


def main():
    src = json.loads((P2 / "ko_alpaca_data.json").read_text(encoding="utf-8"))
    rowmap = {r["item_id"]: int(r["source_row_zero_based"]) for r in
              csv.DictReader(open(REV / "reproducibility/KOALPACA_350_SOURCE_ROW_MAP_2026-09-24.csv", encoding="utf-8-sig"))}
    outs = {}
    for label, (p, sha) in FILES.items():
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        assert got == sha, (label, got)
        outs[label] = {}
        for l in p.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
            r = json.loads(l)
            outs[label][str(r["id"])] = r["answer"].encode("utf-8", "surrogateescape").decode("utf-8", "replace")
    bank = []
    for iid, row in sorted(rowmap.items(), key=lambda x: int(x[0])):
        r = src[row]
        bank.append({"row": row, "item_id": iid, "instruction": r["instruction"], "input": r.get("input", ""),
                     "archived": {k: v.get(iid) for k, v in outs.items()}})
    assert len(bank) == 350 and all(all(x["archived"].values()) for x in bank)
    text = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in bank)
    (HERE / "bank_orig350.jsonl").write_text(text, encoding="utf-8", newline="\n")
    print("orig350", len(bank), hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
