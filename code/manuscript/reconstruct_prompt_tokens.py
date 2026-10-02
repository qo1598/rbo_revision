"""Reconstruct per-call prompt (input) tokens for the KorQuAD and HRM8K confirm runs, which recorded only output tokens.
No model calls. Prompts are rebuilt from the frozen templates in rbo_v2/rbo_qa.py and rbo_math.py, the bank items and
the stored traces, and counted with the models' Hugging Face tokenizers and chat templates.

Validation (IFEval-Ko, where Ollama recorded prompt_eval_count): the same counting matches all 342 single A.X prompts
exactly, all 342 single Qwen3-8B prompts after a constant +4 template offset, and all 342 RBO Planner prompts exactly
with that offset.

Approximation: some prompts embed earlier model outputs whose text was not stored (HRM8K solutions and programs,
Self-Refine critiques, the Checker's free-text reason). For those spans we add the producing call's recorded output
tokens. When an A.X output is embedded in a Qwen3 prompt (HRM8K Reviser), its A.X token count is scaled by the Qwen/A.X
token ratio measured on the HRM8K confirm problems. Every count therefore carries the label 'exact' or 'approx'.
Writes PROMPT_TOKENS_V2.json."""
import json, statistics, sys
from pathlib import Path
import pandas as pd
from transformers import AutoTokenizer

R = Path(__file__).resolve().parent.parent / "rbo_v2"
sys.path.insert(0, str(R))
import rbo_qa as QA, rbo_math as MA  # noqa: E402  (templates only)

TOK = {"ax7": AutoTokenizer.from_pretrained("skt/A.X-4.0-Light"), "qwen8": AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")}
OFFSET = {"ax7": 0, "qwen8": 4}


def n(m, content):
    t = TOK[m]
    kw = {"enable_thinking": False} if m == "qwen8" else {}
    s = t.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True, **kw)
    return len(t(s, add_special_tokens=False)["input_ids"]) + OFFSET[m]


def raw(m, text):
    return len(TOK[m](text, add_special_tokens=False)["input_ids"])


def load(stem, keep):
    rows = {}
    for l in (R / "runs" / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(l)
        if x["id"] in keep:
            rows[x["id"]] = x
    return rows


def korquad():
    bank = {i: json.loads(l) for i, l in enumerate((R.parent / "rbo_s_v1" / "bank_korquad.jsonl").read_text(encoding="utf-8").splitlines())}
    keep = set(json.loads((R / "SPLIT_KORQUAD.json").read_text())["confirm"])
    TOOLWHY = "본문에 그대로 있지 않거나 너무 길거나 답을 거부함"
    out = {}
    # single / SC3: the ANSWER prompt, exact
    for name, stem in (("single A.X", "korquad_single_ax7"), ("single Qwen3-8B", "korquad_single_qwen8"), ("SC3 A.X", "korquad_sc3_ax7")):
        m = "qwen8" if "qwen8" in stem else "ax7"
        rows = load(stem, keep)
        per = [n(m, QA.ANSWER.format(instruction=bank[i]["instruction"], context=bank[i]["context"])) * len(r["calls"]) for i, r in rows.items()]
        out[name] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": 0}
    # Self-Refine A.X: answer and critique texts not stored -> recorded output tokens of the producing call
    rows, per, approx = load("korquad_sr_ax7", keep), [], 0
    for i, r in rows.items():
        x, tot, ans_t, crit_t = bank[i], 0, 0, 0
        for c in r["calls"]:
            if c["role"] == "generator":
                tot += n("ax7", QA.ANSWER.format(instruction=x["instruction"], context=x["context"]))
                ans_t = c["output_tokens"]
            elif c["role"] == "critic":
                tot += n("ax7", QA.SR_CRIT.format(context=x["context"], question=x["question"], answer="")) + ans_t; approx += 1
                crit_t = c["output_tokens"]
            else:
                tot += n("ax7", QA.SR_REV.format(context=x["context"], question=x["question"], answer="", crit="")) + ans_t + crit_t; approx += 1
                ans_t = c["output_tokens"]
        per.append(tot)
    out["Self-Refine A.X"] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": approx}
    # RBO v2: replay the stored trace
    rows, per, approx = load("korquad_rbo_qwen8-ax7-qwen8-qwen8", keep), [], 0
    for i, r in rows.items():
        x, tr, calls = bank[i], r["trace"], list(r["calls"])
        draft = tr[0]
        plan = draft["plan"]
        checked = [(draft["answer"], draft["check"])] + [(s["answer"], s["check"]) for s in tr if s["step"].startswith("revise")]
        revs = [s for s in tr if s["step"].startswith("revise")]
        tot, k_check, rev_i = 0, 0, 0
        cur_ans, cur_why_fixed, cur_why_tok = draft["answer"], None, 0
        last_checker_out = 0

        def why_state(chk):
            return TOOLWHY if not all(chk.get(t) for t in ("grounded", "short", "non_refusal")) else None
        cur_why_fixed = why_state(draft["check"])
        for c in calls:
            role, m = c["role"], c["model"]
            if role == "planner":
                tot += n(m, QA.PLAN.format(question=x["question"]))
            elif role == "generator":
                tot += n(m, QA.GEN.format(instruction=x["instruction"], context=x["context"], plan=plan.replace("\n", " ")))
            elif role == "checker":
                while k_check < len(checked) and not all(checked[k_check][1].get(t) for t in ("grounded", "short", "non_refusal")):
                    k_check += 1
                a = checked[k_check][0] if k_check < len(checked) else ""
                tot += n(m, QA.CHECK.format(context=x["context"], question=x["question"], plan=plan, answer=a))
                last_checker_out = c["output_tokens"]
                if k_check == 0:
                    cur_why_tok = last_checker_out
                k_check += 1
            else:  # extractor / reviser
                why = cur_why_fixed if cur_why_fixed else ""
                extra = 0 if cur_why_fixed else cur_why_tok
                tpl = QA.EXTRACT.format(context=x["context"], question=x["question"], answer=cur_ans, why=why) if role == "extractor" else \
                    QA.REANSWER.format(context=x["context"], question=x["question"], plan=plan, answer=cur_ans, why=why)
                tot += n(m, tpl) + extra
                approx += bool(extra)
                s = revs[rev_i] if rev_i < len(revs) else None
                rev_i += 1
                if s and s.get("accepted"):
                    cur_ans, cur_why_fixed = s["answer"], why_state(s["check"])
                    cur_why_tok = last_checker_out
        per.append(tot)
    out["RBO v2"] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": approx}
    return out


def hrm8k():
    d = pd.read_csv(R / "data" / "hrm8k" / "gsm8k_test.csv")
    Q = {i: row["question"] for i, row in d.iterrows()}
    keep = set(json.loads((R / "SPLIT_HRM8K.json").read_text())["confirm"])
    ratio = sum(raw("qwen8", Q[i]) for i in keep) / sum(raw("ax7", Q[i]) for i in keep)
    out = {"_qwen_per_ax_token_ratio": ratio}
    for name, stem in (("single A.X", "hrm8k_single_ax7"), ("single Qwen3-8B", "hrm8k_single_qwen8"), ("SC3 A.X", "hrm8k_sc3_ax7")):
        m = "qwen8" if "qwen8" in stem else "ax7"
        rows = load(stem, keep)
        per = [n(m, MA.SOLVE.format(q=Q[i])) * len(r["calls"]) for i, r in rows.items()]
        out[name] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": 0}
    rows, per, approx = load("hrm8k_sr_ax7", keep), [], 0
    for i, r in rows.items():
        q, tot, sol_t, crit_t = Q[i], 0, 0, 0
        for c in r["calls"]:
            if c["role"] == "generator":
                tot += n("ax7", MA.SOLVE.format(q=q)); sol_t = c["output_tokens"]
            elif c["role"] == "critic":
                tot += n("ax7", MA.SR_CRIT.format(q=q, sol="")) + sol_t; crit_t = c["output_tokens"]; approx += 1
            else:
                tot += n("ax7", MA.SR_REV.format(q=q, sol="", crit="")) + sol_t + crit_t; sol_t = c["output_tokens"]; approx += 1
        per.append(tot)
    out["Self-Refine A.X"] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": approx}
    rows, per, approx = load("hrm8k_rbo_qwen8-ax7-qwen8-qwen8", keep), [], 0
    for i, r in rows.items():
        q, tr = Q[i], r["trace"]
        plan = next(s["text"] for s in tr if s["step"] == "plan")
        a0 = next(s["answer"] for s in tr if s["step"] == "draft")
        pv = next(s["value"] for s in tr if s["step"] == "program")
        revs = [s for s in tr if s["step"].startswith("revise")]
        tot, sol_tok_ax, sol_tok_q, code_tok, rev_i, cur_a = 0, 0, 0, 0, 0, a0
        for c in r["calls"]:
            role, m = c["role"], c["model"]
            if role == "planner":
                tot += n(m, MA.PLAN.format(q=q))
            elif role == "generator":
                tot += n(m, MA.GEN.format(q=q, plan=plan)); sol_tok_ax, sol_tok_q = c["output_tokens"], c["output_tokens"] * ratio
            elif role == "checker":
                tot += n(m, MA.CODE.format(q=q)); code_tok = c["output_tokens"]
            elif role == "extractor":
                tot += n(m, MA.EXTRACT.format(q=q, sol="")) + sol_tok_ax; approx += 1
                s = revs[rev_i] if rev_i < len(revs) else None; rev_i += 1
                if s and s.get("accepted"):
                    sol_tok_ax, sol_tok_q, cur_a = c["output_tokens"], c["output_tokens"] * ratio, s["answer"]
            else:  # reviser (Qwen3) sees solution A, its answer, program B and its value
                a = f"{cur_a:g}" if cur_a is not None else ""
                b = f"{pv:g}" if pv is not None else ""
                tot += n(m, MA.RESOLVE.format(q=q, sol="", a=a, code="", b=b)) + sol_tok_q + code_tok; approx += 1
                s = revs[rev_i] if rev_i < len(revs) else None; rev_i += 1
                if s and s.get("accepted"):
                    sol_tok_q, sol_tok_ax, cur_a = c["output_tokens"], c["output_tokens"] / ratio, s["answer"]
        per.append(tot)
    out["RBO v2"] = {"n": len(per), "mean_prompt_tokens": statistics.mean(per), "approx_calls": approx}
    return out


if __name__ == "__main__":
    res = {"korquad": korquad(), "hrm8k": hrm8k(),
           "method": "templates + traces + HF tokenizers (skt/A.X-4.0-Light; Qwen/Qwen3-8B, +4 Ollama template offset); see docstring"}
    (Path(__file__).parent / "PROMPT_TOKENS_V2.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for t in ("korquad", "hrm8k"):
        for k, v in res[t].items():
            print(t, k, v if not isinstance(v, dict) else (v["n"], round(v["mean_prompt_tokens"]), v["approx_calls"]))
