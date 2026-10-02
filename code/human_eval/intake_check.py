"""Intake QC for returned rating files (9-rater design). Checks integrity and completeness only; it never decodes
which system was preferred, so running it on partial returns does not reveal outcomes. Appends receipts.
Usage: python intake_check.py [returns_dir]"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
rdir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "returns"
man = json.loads((HERE / "MANIFEST9.json").read_text(encoding="utf-8"))
packets = {r: json.loads((HERE / "packets9" / f"{r}_packet.json").read_text(encoding="utf-8")) for r in man["raters"]}
receipts = rdir / "RECEIPTS.md"
logged = receipts.read_text(encoding="utf-8") if receipts.exists() else "| 확인 시각 | 파일 | SHA-256 |\n|---|---|---|\n"
print("평가자 | 묶음 | 완료/전체 | 이유 없는 우열 | 판단불가 | 왼쪽 선택률 | 체류 중앙값(초) | 10초 미만 | 동의·서약 | 문제")
for r in man["raters"]:
    files = sorted(p for p in rdir.glob(f"{r}_*.json"))
    if not files:
        print(f"{r} | {man['raters'][r]['block']} | 미반환")
        continue
    for f in files:
        raw = f.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        if h not in logged:
            logged += f"| {datetime.now().isoformat(timespec='seconds')} | {f.name} | {h} |\n"
        problems = []
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            print(f"{r} | {f.name} | JSON 읽기 실패")
            continue
        if d.get("rater") != r:
            problems.append(f"평가자 코드 불일치({d.get('rater')})")
        if d.get("packet_sha256") != man["raters"][r]["packet_sha256"]:
            problems.append("패킷 해시 불일치")
        codes = [x["code"] for x in packets[r]["rows"]]
        got = {x.get("code"): x for x in d.get("ratings", [])}
        if set(got) != set(codes):
            problems.append("문항 코드 집합 불일치")
        main = [got[c] for c in codes if c in got and got[c].get("kind") == "main"]
        lab = [x for x in main if x.get("label")]
        dec = [x for x in lab if x["label"] in ("left", "right")]
        notag = sum(not x.get("reasonTags") for x in dec)
        ms = [x["visibleMs"] for x in main if isinstance(x.get("visibleMs"), (int, float))]
        meta = d.get("meta", {})
        if len(lab) < len(main):
            problems.append(f"미응답 {len(main) - len(lab)}")
        if notag:
            problems.append("이유 체크 누락")
        if not (meta.get("consent") and meta.get("pledge")):
            problems.append("동의/서약 없음")
        if "중간" in f.name:
            problems.append("중간 저장본")
        print(f"{r} | {man['raters'][r]['block']} | {len(lab)}/{len(main)} | {notag} | {sum(x['label'] == 'cannot' for x in lab)} | "
              f"{(sum(x['label'] == 'left' for x in dec) / len(dec)) if dec else float('nan'):.2f} | "
              f"{(statistics.median(ms) / 1000) if ms else float('nan'):.0f} | {(sum(m < 10000 for m in ms) / len(ms)) if ms else float('nan'):.0%} | "
              f"{'예' if meta.get('consent') and meta.get('pledge') else '아니오'} | {', '.join(problems) or '없음'}")
receipts.write_text(logged, encoding="utf-8")
