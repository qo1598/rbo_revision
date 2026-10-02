"""Official IFEval-Ko scoring (allganize/IFEval-Ko evaluator files, unmodified) run outside lm-eval via import aliases."""
import sys, types, importlib.util, json, unicodedata
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "ifeval_ko"


def _load_official():
    pkg = "lm_eval.tasks.ifeval_ko"
    for name in ("lm_eval", "lm_eval.tasks", pkg):
        sys.modules.setdefault(name, types.ModuleType(name))
    mods = {}
    for m in ("instructions_util", "instructions", "instructions_registry", "utils"):
        spec = importlib.util.spec_from_file_location(f"{pkg}.{m}", SRC / f"{m}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"{pkg}.{m}"] = mod
        setattr(sys.modules[pkg], m, mod)
        spec.loader.exec_module(mod)
        mods[m] = mod
    return mods["utils"]


U = _load_official()


def _plain(v):
    """Parquet stores nullable int64 kwargs as float; restore ints as HF datasets would yield them."""
    if hasattr(v, "tolist"):
        v = v.tolist()
    if isinstance(v, float) and v == v and v.is_integer():
        return int(v)
    return v


def items():
    d = pd.read_parquet(HERE / "data" / "ifeval_ko.parquet")
    out = []
    for r in d.to_dict("records"):
        kw = [{k: _plain(v) for k, v in (x or {}).items()} for x in r["kwargs"]]
        out.append({"key": int(r["key"]), "prompt": r["prompt"], "instruction_id_list": list(r["instruction_id_list"]), "kwargs": kw})
    return out


def score(item, response):
    """Returns official strict and loose results for one response."""
    inp = U.InputExample(key=item["key"], instruction_id_list=item["instruction_id_list"], prompt=item["prompt"], kwargs=item["kwargs"])
    s = U.test_instruction_following_strict(inp, response)
    l = U.test_instruction_following_loose(inp, response)
    return {"strict": s.follow_all_instructions, "strict_list": s.follow_instruction_list,
            "loose": l.follow_all_instructions, "loose_list": l.follow_instruction_list}


if __name__ == "__main__":
    it = items()
    print(len(it), it[0]["instruction_id_list"], it[0]["kwargs"])
    print(score(it[0], "테스트 응답"))
