"""Restore the KorQuAD confirmatory bank (bank_korquad.jsonl) from the public KorQuAD 1.0 validation set.
KorQuAD contexts are not redistributed (CC BY-ND 4.0). This script selects the released GUIDs, in their released order,
from any copy of the validation set and writes the bank in exactly the format the experiments used.

Input: a JSON list of validation rows with fields id, title, context, question and answers.text (the format returned by
the Hugging Face datasets-server or `datasets.load_dataset("KorQuAD/squad_kor_v1", split="validation")` converted to a
list). Usage (in the layout created by setup_layout.py, folder revision/rbo_s_v1):
    python restore_korquad_bank.py korquad_v1_validation.json
The script prints the bank's SHA-256; MATHQA_LOCK.json in revision/rbo_v2 holds the value used in the experiments."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUFFIX = "\n\n제공된 입력 문맥만 사용하여 정답 문자열만 출력하세요. 설명을 추가하지 마세요."   # as in build_korquad_bank.py


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "korquad_v1_validation.json"
    rows = {r["id"]: r for r in json.loads(src.read_text(encoding="utf-8"))}
    ids = [json.loads(l)["guid"] for l in (HERE / "bank_korquad_ids.jsonl").read_text(encoding="utf-8").splitlines()]
    missing = [g for g in ids if g not in rows]
    if missing:
        sys.exit(f"{len(missing)} GUIDs not found in {src.name}, e.g. {missing[:3]}")
    items = [{"guid": g, "title": rows[g]["title"], "question": rows[g]["question"], "instruction": rows[g]["question"] + SUFFIX,
              "context": rows[g]["context"], "answers": list(rows[g]["answers"]["text"])} for g in ids]
    text = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in items)
    (HERE / "bank_korquad.jsonl").write_text(text, encoding="utf-8", newline="\n")
    print(len(items), "items; bank_korquad.jsonl SHA-256", hashlib.sha256(text.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
