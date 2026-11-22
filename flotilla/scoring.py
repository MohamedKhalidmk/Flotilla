# Sources: ifeval, lm-eval, lmms-eval, mmmu, ocrbench, ruler, livecodebench, math-verify (docs/reference/REFERENCES.md)
"""Score small-test (or full) traces against gold, one scorer per benchmark (protocol 1.3 metrics).

    python -m flotilla.scoring --run RUN_DIR --items-dir DIR [--out RUN_DIR/scores.jsonl]
    python -m flotilla.scoring stages --labels per_question.jsonl --runs route=DIR ... --out DIR   # see stages_main
Reads RUN_DIR/trace.jsonl and the item files, writes one line per item {item_id, bench, task_type, correct,
error_stage, error_flags, ...} (error stages by PROTOCOL.md section 7, error_stage() below)
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
    from flotilla.label_loop import math_format_match  # 2026-11-20: dollar, \\text{} and option-letter answers
    return {"correct": bool(pred) and (tools.sympy_check(pred, item["gold"])["ok"]
                                       or math_format_match(item.get("task", ""), pred, str(item["gold"])))}


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
            ok = r["ok"] and tools.same_tokens((r["output"] or "").strip().split(), str(t["output"]).strip().split())
        if not ok:
            break
        n_ok += 1
    return {"correct": n_ok == len(item["all_tests"]), "passed": n_ok, "n_tests": len(item["all_tests"])}


SCORERS = {"math_verify": math_verify, "mc_letter": mc_letter, "ifeval": ifeval, "mmmu": mmmu, "ocrbench": ocrbench,
           "ruler_substring": ruler, "lcb": lcb}


# ------------------------------------------------------------------ error stages (PROTOCOL.md section 7)

# One primary stage per trace: the first rule that applies, in this order (pipeline order, earliest failure first).
STAGE_RULES = ("none", "timeout_or_oom", "token_cap", "format_parse_failure", "verifier_false_reject", "vote_wrong",
               "router_wrong_model", "retrieval_miss", "verifier_false_accept", "reasoning_error")
# Stages a deployed system can tag without gold (flotilla-deploy); the others need the gold answer or evidence.
LIVE_STAGES = ("timeout_or_oom", "token_cap", "format_parse_failure")
# Verifier checks that test whether the answer is right, not only its form (math_parses and the option-letter check
# only test form, so an accepted wrong maths or letter answer is not the verifier's miss).
CORRECTNESS_CHECKS = ("public_tests", "constraints", "llm_check")
_CRASH = re.compile(r"timeout|timed out|out of memory|outofmemory|cuda error|enginedead", re.I)


def solver_samples(trace: dict) -> list[dict]:
    """Samples of the solver call(s); the retry, the LLM check and the USC tie call are logged as name:role."""
    return [s for m in trace.get("models", []) if ":" not in m["name"] for s in m["samples"]]


def _model_of(trace: dict) -> list[str]:
    return [m["name"] for m in trace.get("models", []) if ":" not in m["name"] for _ in m["samples"]]


def error_stage(trace: dict, correct: bool | None, grade=None, evidence_shown: bool | None = None,
                abstention: bool = False) -> dict:
    """The trace's error stage by PROTOCOL.md section 7's rules, plus secondary flags.

    correct: the final answer's grade. grade(answer) -> True / False / None (None = cannot grade that answer, e.g. a
    LongMemEval sample no judge has seen). evidence_shown: for a Memory route, whether the facts shown include gold
    evidence (None = unknown). abstention: an unanswerable question (no evidence to retrieve).
    Returns {"stage", "flags", "live"}: live = the stage can be tagged without gold."""
    samples = solver_samples(trace)
    final = trace.get("final_answer")
    ver = trace.get("verifier") or {}
    attempts = ver.get("attempts") or []
    vote = trace.get("vote") or {}
    counts = vote.get("counts") or {}
    flags = []
    if attempts and attempts[0].get("verdict") == "reject":
        flags.append("verifier_rejected")
    if len(attempts) > 1:
        flags.append("retry_used")
    if len(samples) > 1 and vote.get("rule") in ("majority of normalized answers", "USC tie rule (no two answers match)") \
            and counts and max(counts.values()) == 1:
        flags.append("vote_tie")
    if any(t.get("ok") is False and t.get("name") in ("python_exec", "sympy") for t in trace.get("tools") or []):
        flags.append("tool_error")
    if (trace.get("retrieval") or {}).get("fallback") in (True, "True"):
        flags.append("retrieval_fallback")
    if trace.get("retrieval", {}).get("truncated"):
        flags.append("context_truncated")

    def out(stage):
        return {"stage": stage, "flags": flags, "live": stage in LIVE_STAGES}

    if correct:
        return out("none")
    if final in (None, "None", ""):
        crashed = trace.get("error_stage") == "timeout_or_oom" or (
            samples and all((s.get("final_answer") is None and str(s.get("text", "")).startswith("ERROR")
                             and _CRASH.search(str(s.get("text", "")))) for s in samples))
        if crashed:
            return out("timeout_or_oom")
        if any(c.get("finish_reason") == "length" for c in trace.get("call_log") or []):
            return out("token_cap")
        return out("format_parse_failure")
    graded = [grade(s.get("final_answer")) if grade and s.get("final_answer") is not None else None for s in samples]
    if len(attempts) > 1 and attempts[0].get("verdict") == "reject" and grade and grade(attempts[0].get("final_answer")):
        return out("verifier_false_reject")
    if len(samples) > 1 and any(g is True for g in graded):
        models = _model_of(trace)
        right_models = {m for m, g in zip(models, graded) if g is True}
        winner_model = next((m for m, s in zip(models, samples) if s.get("final_answer") == vote.get("winner")), None)
        if len(set(models)) > 1 and winner_model and winner_model not in right_models:
            return out("router_wrong_model")
        return out("vote_wrong")
    if len(samples) > 1 and any(g is None for g in graded):
        flags.append("samples_ungraded")
    if (trace.get("retrieval") or {}).get("source") == "graft" and not abstention and evidence_shown is False:
        return out("retrieval_miss")
    last = attempts[-1] if attempts else {}
    if last.get("verdict") == "accept" and any(c.get("name") in CORRECTNESS_CHECKS and c.get("passed")
                                               for c in last.get("checks") or []):
        return out("verifier_false_accept")
    return out("reasoning_error")


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


def _norm_answer(a) -> str:
    return re.sub(r"\s+", " ", str(a or "").strip().lower()).strip(" .")


def _grade_pair(arg):
    from flotilla.label_loop import grade as label_grade
    item, ans = arg
    try:
        return bool(label_grade(item, ans))
    except Exception:  # noqa: BLE001 - a grader crash leaves the sample ungraded, never right
        return None


def stages_main(argv: list[str]) -> None:
    """Error stages for a finished label set (test 04), without regrading the labels:
        python -m flotilla.scoring stages --labels per_question.jsonl --runs route=DIR [route=DIR ...] \
            [--items GLOB ...] [--memory-items LME.jsonl --verdicts V.jsonl --graft-cache DIR] --out OUT_DIR
    A route's later folders replace earlier ones per item (run-03's fix reruns after the first answers). The final
    answer's grade is the label's; a trace whose final answer does not match the label's is skipped and counted.
    Pool samples are graded with the router-label graders (label_loop.grade); a LongMemEval sample is right or wrong
    when the judge gave a verdict on the same answer text for that item (any route), else ungraded. Memory routes get
    evidence_shown from the GRAFT cache's graph (fact provenance against the answer sessions)."""
    import glob
    ap = argparse.ArgumentParser(prog="scoring stages")
    ap.add_argument("--labels", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--items", nargs="*", default=[])
    ap.add_argument("--memory-items")
    ap.add_argument("--verdicts")
    ap.add_argument("--graft-cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.labels)}
    items = {}
    for g in a.items:
        for f in glob.glob(g):
            for line in open(f):
                it = json.loads(line)
                items[it.get("item_id") or it.get("id")] = it
    mem = {}
    if a.memory_items:
        for line in open(a.memory_items):
            it = json.loads(line)
            if it["item_id"] in rows:
                mem[it["item_id"]] = it
    judged = {}
    if a.verdicts:
        for line in open(a.verdicts):
            v = json.loads(line)
            if v.get("answer") is not None:
                judged[(v["item_id"], _norm_answer(v["answer"]))] = bool(v["correct"])
    traces: dict[str, dict] = defaultdict(dict)
    for kv in a.runs:
        route, d = kv.split("=", 1)
        for line in open(Path(d) / "trace.jsonl"):
            t = json.loads(line)
            traces[route][t["item_id"]] = t
    graphs = {}

    def graph_for(iid, key):
        if (iid, key) not in graphs:
            p = Path(a.graft_cache) / "graphs" / f"{iid}.{key}.json"
            graphs[(iid, key)] = json.load(open(p)) if p.exists() else None
        return graphs[(iid, key)]

    from flotilla.memory_route import evidence_shown, gold_in_facts, is_abstention, shown_facts_text
    # grade every distinct (pool item, answer) once, in parallel (code tests and sympy run in subprocesses)
    todo = set()
    for route, tr in traces.items():
        for iid, t in tr.items():
            if iid in items and iid not in mem and iid in rows:
                atts = (t.get("verifier") or {}).get("attempts") or []
                for ans in [s.get("final_answer") for s in solver_samples(t)] + [x.get("final_answer") for x in atts[:1]]:
                    if ans is not None:
                        todo.add((iid, ans))
    todo = sorted(todo)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(a.workers) as ex:
        pool_grades = dict(zip(todo, ex.map(_grade_pair, [(items[i], ans) for i, ans in todo], chunksize=16)))
    out_rows, skipped = [], defaultdict(int)
    for route, tr in traces.items():
        for iid, r in rows.items():
            lab = r.get(route) or {}
            if not lab.get("available") or iid not in tr:
                continue
            t = tr[iid]
            fa, la = _norm_answer(t.get("final_answer") if t.get("final_answer") is not None else ""), _norm_answer(lab.get("answer"))
            if la and not fa.startswith(la[:200]):
                skipped[route] += 1
                continue
            if iid in mem:
                g = lambda ans, iid=iid: judged.get((iid, _norm_answer(ans)))
            elif iid in items:
                g = lambda ans, iid=iid: pool_grades.get((iid, ans))
            else:
                g = None
            ev = ev_session = None
            ret = t.get("retrieval") or {}
            if ret.get("source") == "graft" and iid in mem and a.graft_cache:
                gr = graph_for(iid, ret.get("graph_key"))
                if gr:   # fact-level (the gold inside the facts shown); the session-level check kept for reference
                    ev = gold_in_facts(mem[iid], shown_facts_text(ret.get("fact_ids") or [], gr))
                    ev_session = evidence_shown(mem[iid], ret.get("fact_ids") or [], gr)
            st = error_stage(t, bool(lab.get("correct")), grade=g, evidence_shown=ev,
                             abstention=bool(iid in mem and is_abstention(mem[iid])))
            out_rows.append({"id": iid, "route": route, "task_type": r["task_type"], "correct": bool(lab.get("correct")),
                             "error_stage": st["stage"], "error_flags": st["flags"], "evidence_shown": ev,
                             "evidence_session": ev_session})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "stages.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in out_rows)
    (out / "stages_summary.json").write_text(json.dumps({"rows": len(out_rows), "skipped_answer_mismatch": dict(skipped)}, indent=1))
    print(json.dumps({"rows": len(out_rows), "skipped_answer_mismatch": dict(skipped)}))


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stages":
        return stages_main(sys.argv[2:])
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
        st = error_stage(t, r["correct"], grade=lambda a, it=it: SCORERS[it["scorer"]](a, it)["correct"])
        rows.append({"item_id": it["item_id"], "id": it["item_id"], "bench": it["bench"], "task_type": it["task_type"],
                     "tokens_total": t["tokens_total"], "calls": calls, **r, "error_stage": st["stage"],
                     "error_flags": st["flags"]})
    with open(run / "scores.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    s = summary(rows)
    (run / "scores_summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
