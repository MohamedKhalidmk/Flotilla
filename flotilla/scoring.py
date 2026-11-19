"""Score small-test (or full) traces against gold, one scorer per benchmark (protocol 1.3 metrics).

    python -m flotilla.scoring --run RUN_DIR --items-dir DIR [--out RUN_DIR/scores.jsonl]
Reads RUN_DIR/trace.jsonl and the item files, writes one line per item {item_id, bench, task_type, correct, ...}
and RUN_DIR/scores_summary.json (per-benchmark metric as CQL reports it, plus mean over benchmarks).
Runs where lm_eval (IFEval) and lmms_eval 0.7.3 (MMMU) are installed: the Trillium env.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from flotilla import tools

QA_RULER = ("qa",)          # RULER QA tasks use string_match_part (any reference); the others string_match_all


def strip_fence(code: str) -> str:
    m = re.findall(r"```(?:python|py)?\s*\n(.*?)```", code, re.S)
    return max(m, key=len) if m else code


def math_verify(pred, item):
    return {"correct": bool(pred) and tools.sympy_check(pred, item["gold"])["ok"]}


def mc_letter(pred, item):
    p = (pred or "").strip().strip("()[].").upper()
    return {"correct": p[:1] == item["gold"] and (len(p) == 1 or not p[1].isalpha())}


def ifeval(pred, item):
    from lm_eval.tasks.ifeval.utils import process_results
    doc = {"key": item["item_id"], "prompt": item["task"], "instruction_id_list": item["instruction_id_list"], "kwargs": item["kwargs"]}
    r = process_results(doc, [pred or ""])
    return {"correct": bool(r["prompt_level_strict_acc"]), "prompt_strict": bool(r["prompt_level_strict_acc"]),
            "inst_strict": r["inst_level_strict_acc"], "prompt_loose": bool(r["prompt_level_loose_acc"]),
            "inst_loose": r["inst_level_loose_acc"]}


def mmmu(pred, item):
    from lmms_eval.tasks.mmmu import utils as mu
    pred = pred or ""
    if item["question_type"] == "multiple-choice" and item.get("options"):
        choices = [chr(65 + k) for k in range(len(item["options"]))]
        idx2ans = dict(zip(choices, item["options"]))
        parsed = mu.parse_multi_choice_response(pred, choices, idx2ans)
        ok = mu.eval_multi_choice(item["gold"], parsed)
    else:
        parsed = mu.parse_open_response(pred)
        gold = item["gold"]
        try:
            gold = json.loads(gold) if gold.strip().startswith("[") else gold
        except ValueError:
            pass
        ok = mu.eval_open(gold, parsed)
    return {"correct": bool(ok), "parsed": str(parsed)[:200]}


def ocrbench(pred, item):
    """lmms-eval OCRBench rule: a gold answer counts if it appears in the prediction (HME100k: spaces removed)."""
    p = (pred or "")
    if item.get("ocr_dataset") == "HME100k":
        p = p.strip().replace("\n", " ").replace(" ", "")
        ok = any(g.strip().replace("\n", " ").replace(" ", "") in p for g in item["gold"])
    else:
        p = p.lower().strip().replace("\n", " ")
        ok = any(g.lower().strip().replace("\n", " ") in p for g in item["gold"])
    return {"correct": ok}


def ruler(pred, item):
    p = (pred or "").lower()
    refs = [str(g).lower() for g in item["gold"]]
    if item.get("ruler_task", "").startswith(QA_RULER):
        s = float(any(r in p for r in refs))
    else:
        s = sum(r in p for r in refs) / len(refs)
    return {"correct": s == 1.0, "score": s}


def lcb(pred, item, timeout_s: float = 6.0):
    """pass@1 on all tests (public + private), stopping at the first failure."""
    if not pred:
        return {"correct": False, "passed": 0, "n_tests": len(item["all_tests"])}
    code = strip_fence(pred)
    fn = item.get("fn_name")
    n_ok = 0
    for t in item["all_tests"]:
        if t.get("testtype") == "functional" and fn:
            harness = code + ("\n\nimport json as _j, sys as _s\n_a = [_j.loads(l) for l in _s.stdin.read().split('\\n') if l.strip()]\n"
                              f"print(_j.dumps(Solution().{fn}(*_a)))\n")
            r = tools.python_exec(harness, t["input"], timeout_s)
            try:
                ok = r["ok"] and json.loads((r["output"] or "").strip().splitlines()[-1]) == json.loads(t["output"])
            except (ValueError, IndexError):
                ok = False
        else:
            r = tools.python_exec(code, t["input"], timeout_s)
            ok = r["ok"] and (r["output"] or "").strip().split() == str(t["output"]).strip().split()
        if not ok:
            break
        n_ok += 1
    return {"correct": n_ok == len(item["all_tests"]), "passed": n_ok, "n_tests": len(item["all_tests"])}


SCORERS = {"math_verify": math_verify, "mc_letter": mc_letter, "ifeval": ifeval, "mmmu": mmmu, "ocrbench": ocrbench,
           "ruler_substring": ruler, "lcb": lcb}


def summary(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[r["bench"]].append(r)
    out = {}
    for b, rs in sorted(by.items()):
        n = len(rs)
        d = {"n": n, "accuracy": round(sum(r["correct"] for r in rs) / n, 4)}
        if b == "ifeval":
            insts = [x for r in rs for x in r["inst_strict"]]
            d.update(prompt_strict=d["accuracy"], inst_strict=round(sum(insts) / len(insts), 4))
        if b == "ocrbench":
            d["score_per_1000"] = round(1000 * d["accuracy"], 1)
        if b.startswith("ruler"):
            d["mean_score"] = round(sum(r["score"] for r in rs) / n, 4)
        d["tokens_total"] = sum(r.get("tokens_total", 0) for r in rs)
        d["calls"] = sum(r.get("calls", 0) for r in rs)
        out[b] = d
    main = {b: (d["mean_score"] if b.startswith("ruler") else d["accuracy"]) for b, d in out.items()}
    return {"per_bench": out, "mean_over_benches": round(sum(main.values()) / len(main), 4) if main else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--items-dir", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    items = {}
    for f in Path(a.items_dir).glob("*.jsonl"):
        for line in open(f):
            it = json.loads(line)
            items[it["item_id"]] = it
    rows = []
    for line in open(run / "trace.jsonl"):
        t = json.loads(line)
        it = items[t["item_id"]]
        r = SCORERS[it["scorer"]](t["final_answer"], it)
        calls = t.get("calls", sum(len(m["samples"]) for m in t["models"]))
        rows.append({"item_id": it["item_id"], "id": it["item_id"], "bench": it["bench"], "task_type": it["task_type"],
                     "tokens_total": t["tokens_total"], "calls": calls, **r})
    with open(run / "scores.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    s = summary(rows)
    (run / "scores_summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
