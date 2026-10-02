"""RBO-S KorQuAD 1.0 transfer bank: one question per distinct context (salted hash), frozen before any output.

Source: HF datasets-server KorQuAD/squad_kor_v1 validation rows 0-5699 (rows 5700-5773 not downloaded: HTTP 429,
outcome-blind). No development split: the KLUE-frozen RBO-S configuration is applied unchanged (pure transfer test).
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "korquad_v1_validation.json"
SALT = "rbo-s-korquad-v1-2026-09-25"
SUFFIX = "\n\n제공된 입력 문맥만 사용하여 정답 문자열만 출력하세요. 설명을 추가하지 마세요."


def h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    best = {}
    for r in sorted(rows, key=lambda r: h(SALT + r["id"])):
        if len(r["context"]) > 3000:
            continue
        best.setdefault(h(r["context"]), r)
    bank = sorted(best.values(), key=lambda r: h(SALT + "ctx" + r["id"]))
    items = [{"guid": r["id"], "title": r["title"], "question": r["question"], "instruction": r["question"] + SUFFIX,
              "context": r["context"], "answers": list(r["answers"]["text"])} for r in bank]
    text = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in items)
    (HERE / "bank_korquad.jsonl").write_text(text, encoding="utf-8", newline="\n")
    man = {"source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(), "source_rows": len(rows),
           "n": len(items), "bank_sha256": h(text), "salt": SALT,
           "note": "validation rows 5700-5773 not downloaded (HTTP 429), decided before any output"}
    (HERE / "KORQUAD_BANK_MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
