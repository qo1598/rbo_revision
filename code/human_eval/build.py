"""Build the 2026-10 human-evaluation packets (PROTOCOL.md): five comparisons x 35 disjoint items, three raters,
identity-hidden, side-balanced, per-rater random order, 10 swapped repeats and 3 practice pairs. No model calls."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REV = HERE.parent
S = REV / "rbo_s_v1"
P2 = REV.parent / "논문2(역할기반 협업 오케스트레이션을 통한 한국어 과제 성능 평가 — SOTA 모델과의 비교 분석)"
CATS = P2 / "부록" / "pilot_7_seq_categories.csv"
OUT = HERE / "packets"
PRIVATE = HERE / "private"
SAMPLE_SEED, PRES_SEED = "he-2026-10-sample", "he-2026-10-present"
PER_CAT, N_REPEAT_PER_COMP, N_PRACTICE = 5, 2, 3
RATERS = ("R01", "R02", "R03")
# code: (system A = RBO side, system B = comparator); sampling order R1, R2, R3, O1, O2
COMPARISONS = {"R1": ("rbov2", "v2single_ax7"), "R2": ("rbov2", "gpt4o_matched"), "R3": ("rbov2", "rbo_v1_main"),
               "O1": ("rbo_v1_main", "gpt4o_archived"), "O2": ("rbo_v1_ds_run", "deepseek_archived")}


def sha(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def fsha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load():
    bank = [json.loads(l) for l in (S / "bank_orig350.jsonl").read_text(encoding="utf-8").splitlines()]
    cat = {int(r["id"]): r["category"] for r in csv.DictReader(open(CATS, encoding="utf-8-sig"))}
    texts = {k: {b["row"]: b["archived"][k] for b in bank} for k in ("rbo_v1_main", "rbo_v1_ds_run", "gpt4o_archived", "deepseek_archived")}
    sources = {"bank_orig350.jsonl": fsha(S / "bank_orig350.jsonl"), "categories": fsha(CATS)}
    for n in ("rbov2", "v2single_ax7", "gpt4o_matched"):
        p = S / "runs" / f"orig350_ext_{n}.jsonl"
        texts[n] = {json.loads(l)["row"]: json.loads(l)["text"] for l in p.read_text(encoding="utf-8").splitlines()}
        sources[p.name] = fsha(p)
    items = {b["row"]: {"row": b["row"], "item_id": b["item_id"], "category": cat[int(b["item_id"])],
                        "instruction": b["instruction"], "input": b.get("input", "")} for b in bank}
    assert len(items) == 350 and all(len(t) == 350 for t in texts.values())
    return items, texts, sources


def main() -> None:
    if OUT.exists() or PRIVATE.exists():
        raise FileExistsError("packets already built; do not rebuild after distribution")
    items, texts, sources = load()
    cats = sorted({x["category"] for x in items.values()})
    used, excluded, pairs = set(), {}, []
    for comp, (a, b) in COMPARISONS.items():
        same = {r for r in items if texts[a][r].strip() == texts[b][r].strip()}
        excluded[comp] = len(same)
        for c in cats:
            pool = [r for r in items if items[r]["category"] == c and r not in used and r not in same]
            pool.sort(key=lambda r: sha(f"{SAMPLE_SEED}:{comp}:{r}"))
            for r in pool[:PER_CAT]:
                used.add(r)
                pairs.append({"comp": comp, "row": r, "a": texts[a][r], "b": texts[b][r]})
    assert len(pairs) == len(COMPARISONS) * len(cats) * PER_CAT and len(used) == len(pairs)
    rest = sorted((r for r in items if r not in used), key=lambda r: sha(f"{SAMPLE_SEED}:practice:{r}"))
    practice = [{"comp": "PRACTICE", "row": r, "a": texts["rbov2"][r], "b": texts["gpt4o_matched"][r]} for r in rest[:N_PRACTICE]]

    OUT.mkdir()
    PRIVATE.mkdir()
    mapping, counts = {}, {}
    for ri, rater in enumerate(RATERS):
        core, sides = [], {}
        for comp in COMPARISONS:
            group = sorted((p for p in pairs if p["comp"] == comp), key=lambda p: sha(f"{PRES_SEED}:{rater}:{comp}:{p['row']}:side"))
            sides[comp] = 0
            for rank, p in enumerate(group):
                a_left = (rank + ri) % 2 == 0
                sides[comp] += a_left
                core.append((p, a_left, "core"))
        core.sort(key=lambda x: sha(f"{PRES_SEED}:{rater}:{x[0]['comp']}:{x[0]['row']}:order"))
        reps = []
        for comp in COMPARISONS:
            cand = sorted((x for x in core if x[0]["comp"] == comp), key=lambda x: sha(f"{PRES_SEED}:{rater}:{x[0]['row']}:repeat"))
            reps += [(p, not a_left, "repeat") for p, a_left, _ in cand[:N_REPEAT_PER_COMP]]
        reps.sort(key=lambda x: sha(f"{PRES_SEED}:{rater}:{x[0]['row']}:reporder"))
        # repeats are interleaved into the second half, never adjacent to their first showing by construction of order
        half = len(core) // 2
        seq = core[:half]
        tail = core[half:]
        step = max(1, len(tail) // (len(reps) + 1))
        for i, r in enumerate(reps):
            tail.insert(min(len(tail), (i + 1) * step + i), r)
        seq += tail
        seq = [(p, (ri + k) % 2 == 0, "practice") for k, p in enumerate(practice)] + seq
        rows = []
        for p, a_left, kind in seq:
            code = sha(f"{PRES_SEED}:{rater}:{kind}:{p['comp']}:{p['row']}")[:12].upper()
            it = items[p["row"]]
            left, right = (p["a"], p["b"]) if a_left else (p["b"], p["a"])
            mapping[f"{rater}:{code}"] = {"rater": rater, "code": code, "kind": kind, "comp": p["comp"], "row": p["row"],
                                          "item_id": it["item_id"], "category": it["category"],
                                          "a_side": "left" if a_left else "right",
                                          "left_sha256": sha(left), "right_sha256": sha(right)}
            rows.append({"code": code, "kind": "practice" if kind == "practice" else "main",
                         "instruction": it["instruction"], "input": it["input"], "left": left, "right": right})
        payload = json.dumps({"rater": rater, "rows": rows}, ensure_ascii=False, sort_keys=True)
        psha = sha(payload)
        (OUT / f"{rater}_packet.json").write_text(payload, encoding="utf-8")
        (OUT / f"{rater}_평가.html").write_text(render(rater, rows, psha), encoding="utf-8")
        counts[rater] = {"practice": N_PRACTICE, "core": len(core), "repeat": len(reps), "total": len(rows),
                         "a_left_by_comp": sides, "packet_sha256": psha}
    (PRIVATE / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    sample = [{"comp": p["comp"], "row": p["row"], "item_id": items[p["row"]]["item_id"], "category": items[p["row"]]["category"],
               "a_sha256": sha(p["a"]), "b_sha256": sha(p["b"])} for p in pairs]
    (HERE / "SAMPLE.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest = {"protocol_sha256": fsha(HERE / "PROTOCOL.md"), "build_sha256": fsha(Path(__file__)), "sources": sources,
                "comparisons": COMPARISONS, "identical_excluded": excluded, "per_category": PER_CAT,
                "core_pairs": len(pairs), "raters": counts, "sample_sha256": fsha(HERE / "SAMPLE.json"),
                "mapping_sha256": fsha(PRIVATE / "mapping.json"),
                "html_sha256": {r: fsha(OUT / f"{r}_평가.html") for r in RATERS}}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"core_pairs": len(pairs), "identical_excluded": excluded, "raters": counts}, ensure_ascii=False))


def render(rater: str, rows: list[dict], psha: str) -> str:
    data = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    return (TEMPLATE.replace("__RATER__", rater).replace("__PSHA__", psha).replace("__ROWS__", data))


TEMPLATE = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>응답 비교 평가 __RATER__</title>
<style>
:root{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--line:#d0d4da;--soft:#f4f6f8;--accent:#1a5fb4;--warn:#b3261e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:16px}h1{font-size:1.4rem}h2{font-size:1.1rem;margin:.2rem 0}
#bar{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
#bar .grow{flex:1;color:var(--muted)}pre{white-space:pre-wrap;word-break:break-word;background:var(--soft);padding:12px;border-radius:8px;margin:.3rem 0;font:inherit}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){.pair{grid-template-columns:1fr}}
.box{border:1px solid var(--line);border-radius:10px;padding:10px}.tag{font-size:.8rem;color:var(--muted)}
button{font:inherit;padding:7px 14px;border-radius:8px;border:1px solid var(--line);background:var(--soft);cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}.choice label{display:inline-block;margin:4px 14px 4px 0}
textarea,input[type=text]{width:100%;font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px}textarea{min-height:64px}label{display:block}
.warn{color:var(--warn)}.card{border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}
</style></head><body>
<div id="bar"><span class="grow" id="prog"></span><button onclick="go(-1)">◀ 이전</button><button onclick="go(1)">다음 ▶</button><button onclick="nextEmpty()">미응답으로</button><button class="primary" onclick="saveFile()">결과 파일 저장</button></div>
<main id="app"></main>
<script>
const RATER="__RATER__", PSHA="__PSHA__", ROWS=__ROWS__, KEY="he2026-10-"+RATER+"-"+PSHA.slice(0,8);
let S={meta:{},ans:{},pos:-1};
try{const s=localStorage.getItem(KEY); if(s) S=JSON.parse(s);}catch(e){}
function persist(){try{localStorage.setItem(KEY,JSON.stringify(S));}catch(e){}}
const now=()=>new Date().toISOString();
function esc(s){return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
let shownAt=null;
function tick(){if(S.pos>=0&&shownAt!==null){const c=ROWS[S.pos].code,a=S.ans[c]||(S.ans[c]={});a.visibleMs=(a.visibleMs||0)+(Date.now()-shownAt);shownAt=Date.now();persist();}}
document.addEventListener("visibilitychange",()=>{if(document.hidden){tick();shownAt=null;}else if(S.pos>=0){shownAt=Date.now();}});
function done(c){const a=S.ans[c];if(!a||!a.label)return false;if((a.label==="left"||a.label==="right")&&!(a.reasonTags||[]).length)return false;return true;}
const TAGS=[["accuracy","내용 정확성"],["instruction","지시·형식 준수"],["completeness","내용 충실도·도움 정도"],["korean","한국어 표현"],["other","기타"]];
function intro(){
 const m=S.meta;document.getElementById("prog").textContent="평가자 "+RATER+" · 시작 전 안내";
 document.getElementById("app").innerHTML=`<h1>한국어 응답 비교 평가 (${RATER})</h1>
 <div class="card"><b>무엇을 하나요?</b><br>각 화면에는 하나의 지시(필요하면 입력 자료 포함)와 두 개의 응답이 나옵니다. 어느 응답이 지시를 더 잘 수행했는지 골라 주세요.
 <ul><li>판단 기준: 내용의 정확성, 지시·형식 준수, 실제 도움 정도, 자연스러운 한국어. <b>길이 자체는 기준이 아닙니다.</b> 길어도 군더더기거나 틀리면 감점, 짧아도 정확하고 충분하면 좋은 응답입니다.</li>
 <li>선택지: 왼쪽이 더 좋음 / 오른쪽이 더 좋음 / 비슷함 / 판단 불가(지식이 부족하거나 지시 자체가 성립하지 않는 경우).</li>
 <li>왼쪽·오른쪽을 고르면 더 좋다고 본 <b>이유를 하나 이상 체크</b>해 주세요(여러 개 가능). 짧은 메모는 선택이지만, 적어 주시면 분석에 큰 도움이 됩니다.</li>
 <li>응답을 만든 시스템은 공개되지 않으며, 같은 시스템이 늘 같은 쪽에 나오지도 않습니다.</li>
 <li>처음 3개는 연습 문항입니다(분석하지 않음). 전체 ${ROWS.length}개이며 2~3회로 나누어 해도 됩니다. 응답은 이 브라우저에 자동 저장됩니다. <b>같은 컴퓨터·같은 브라우저</b>로 이어서 하세요.</li></ul></div>
 <div class="card"><b>지켜 주세요</b><ul><li>ChatGPT 등 <b>생성형 AI를 사용하지 마세요.</b> 외부 검색이나 다른 평가자와의 상의도 하지 마세요.</li><li>본인의 판단만 기록해 주세요.</li></ul></div>
 <div class="card"><b>동의 및 기본 정보</b> (이름·연락처는 받지 않습니다)<br>
 <label><input type="checkbox" id="c1" ${m.consent?"checked":""}> 연구 목적의 평가 참여와 평가 결과(익명) 활용에 동의합니다.</label><br>
 <label><input type="checkbox" id="c2" ${m.pledge?"checked":""}> 생성형 AI·외부 검색·타인과의 상의 없이 혼자 평가하겠습니다.</label><br>
 교직 경력(년) <input type="text" id="yrs" value="${esc(m.years||"")}" style="max-width:120px"> &nbsp; 최종 학위 <input type="text" id="deg" value="${esc(m.degree||"")}" style="max-width:200px"></div>
 <button class="primary" onclick="start()">평가 시작 / 이어하기</button> <span class="warn" id="msg"></span>`;}
function start(){const c1=document.getElementById("c1").checked,c2=document.getElementById("c2").checked;
 if(!c1||!c2){document.getElementById("msg").textContent="두 항목에 모두 체크해야 시작할 수 있습니다.";return;}
 Object.assign(S.meta,{consent:true,pledge:true,years:document.getElementById("yrs").value,degree:document.getElementById("deg").value});
 if(!S.meta.consentAt)S.meta.consentAt=now();S.pos=Math.max(0,S.pos);persist();render();}
function render(){
 if(S.pos<0){intro();return;}
 const x=ROWS[S.pos],a=S.ans[x.code]||(S.ans[x.code]={});if(!a.firstShownAt)a.firstShownAt=now();shownAt=Date.now();persist();
 const n=ROWS.filter(r=>done(r.code)).length;
 document.getElementById("prog").textContent=`평가자 ${RATER} · ${S.pos+1} / ${ROWS.length} · 완료 ${n}개`;
 const lab=[["left","왼쪽이 더 좋음"],["right","오른쪽이 더 좋음"],["tie","비슷함"],["cannot","판단 불가"]];
 document.getElementById("app").innerHTML=`<h2>${x.kind==="practice"?"연습 문항 ":"문항 "}${S.pos+1}</h2><div class="tag">코드 ${x.code}</div>
 <h3>지시</h3><pre>${esc(x.instruction)}</pre>${x.input?`<h3>입력 자료</h3><pre>${esc(x.input)}</pre>`:""}
 <div class="pair"><div class="box"><b>왼쪽 응답</b><pre>${esc(x.left)}</pre></div><div class="box"><b>오른쪽 응답</b><pre>${esc(x.right)}</pre></div></div>
 <div class="card choice">${lab.map(([v,t])=>`<label><input type="radio" name="lab" value="${v}" ${a.label===v?"checked":""} onchange="setLab('${v}')"> ${t}</label>`).join("")}
 ${a.label==="left"||a.label==="right"?`<div style="margin-top:8px">더 좋다고 본 이유 <span class="warn">(하나 이상 체크)</span><br>${TAGS.map(([v,t])=>`<label style="display:inline-block;margin-right:14px"><input type="checkbox" ${(a.reasonTags||[]).includes(v)?"checked":""} onchange="setTag('${v}',this.checked)"> ${t}</label>`).join("")}</div>`:""}
 <label style="display:block;margin-top:8px">메모 (선택)<textarea id="why" oninput="setWhy()">${esc(a.reason||"")}</textarea></label></div>
 <button onclick="go(-1)">◀ 이전</button> <button class="primary" onclick="go(1)">다음 ▶</button> <span class="warn" id="msg"></span>`;}
function setLab(v){tick();const a=S.ans[ROWS[S.pos].code];a.label=v;a.lastChangedAt=now();persist();render();}
function setTag(v,on){const a=S.ans[ROWS[S.pos].code];const t=new Set(a.reasonTags||[]);on?t.add(v):t.delete(v);a.reasonTags=[...t];a.lastChangedAt=now();persist();render();}
function setWhy(){const a=S.ans[ROWS[S.pos].code];a.reason=document.getElementById("why").value;a.lastChangedAt=now();persist();}
function go(d){if(S.pos<0)return;tick();S.pos=Math.min(ROWS.length-1,Math.max(0,S.pos+d));persist();render();window.scrollTo(0,0);}
function nextEmpty(){if(S.pos<0)return;tick();const i=ROWS.findIndex(r=>!done(r.code));if(i>=0){S.pos=i;persist();render();window.scrollTo(0,0);}else alert("모든 문항을 완료했습니다. '결과 파일 저장'을 눌러 주세요.");}
function saveFile(){tick();const left=ROWS.filter(r=>!done(r.code)).length;
 if(left&&!confirm(`아직 ${left}개 문항이 완료되지 않았습니다. 중간 저장할까요?`))return;
 const out={rater:RATER,packet_sha256:PSHA,saved_at:now(),complete:left===0,meta:S.meta,
  ratings:ROWS.map(r=>({code:r.code,kind:r.kind,...(S.ans[r.code]||{})}))};
 const b=new Blob([JSON.stringify(out,null,1)],{type:"application/json"}),u=URL.createObjectURL(b),e=document.createElement("a");
 e.href=u;e.download=`${RATER}_결과_${out.saved_at.slice(0,10)}${left?"_중간":""}.json`;document.body.appendChild(e);e.click();e.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);}
render();
</script></body></html>'''

if __name__ == "__main__":
    main()
