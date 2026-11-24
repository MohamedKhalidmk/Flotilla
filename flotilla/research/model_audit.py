"""Every question a model got wrong in a scored run, with a cause: grader bug, verifier bug, wrong gold, or model wrong.

    python -m flotilla.research.model_audit smalltest --model gptoss --runs DIR [DIR ...] --items-dir $SCRATCH/flotilla/smalltest \
        --ref-runs QWEN_DIR [...] --out OUT
    python -m flotilla.research.model_audit labels --model gptoss --runs DIR [...] --pool pool.clean.jsonl --orig labels.jsonl \
        --ref-runs QWEN_DIR [...] --out OUT
Wrong = wrong in the original scoring (small test: scores.jsonl; labels: the router-label labels.jsonl). Cause, first
match wins:
  grader bug     the fixed graders (2026-11-20: instruction checker, float tolerance on code, math formats) accept it
  verifier bug   a verifier attempt held an answer the fixed graders accept, the verifier rejected it, and the final
                 answer moved off it (the check that rejected it is named)
  wrong gold     a gold answer found wrong by hand (--known-gold-errors), or an interactive problem that fixed
                 stdin/stdout tests cannot judge
  model wrong    otherwise (detail: no answer, token cap, lost the vote)
wrong_gold_candidate marks a model-wrong answer identical to the reference model's (Qwen's) wrong answer: both agree
against the gold, so the gold is checked by hand. Writes OUT/failures.jsonl and OUT/summary.json.
"""
import argparse
import gzip
import json
import re
from collections import Counter
from pathlib import Path

from flotilla.routers.label_loop import grade as label_grade
from flotilla.core.scoring import SCORERS


def _open(p: Path):
    return gzip.open(p, "rt") if p.suffix == ".gz" else open(p)


def traces(dirs: list[str]) -> dict:
    out = {}
    for d in dirs:
        for p in sorted(Path(d).rglob("trace.jsonl*")):
            if "smoke" in p.parts:
                continue
            for line in _open(p):
                t = json.loads(line)
                out[t["item_id"]] = t
    return out


def scores(dirs: list[str]) -> dict:
    out = {}
    for d in dirs:
        for p in sorted(Path(d).rglob("scores.jsonl*")):
            if "smoke" in p.parts:
                continue
            for line in _open(p):
                s = json.loads(line)
                out[s["item_id"]] = s
    return out


def norm(a) -> str:
    return re.sub(r"\s+", " ", str(a or "")).strip().lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["smalltest", "labels"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--ref-runs", nargs="*", default=[])
    ap.add_argument("--items-dir")
    ap.add_argument("--pool")
    ap.add_argument("--orig", help="labels: the original labels.jsonl with a correct field per id")
    ap.add_argument("--known-gold-errors", default=None, help="JSON {id: reason} of golds found wrong by hand")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    tr, ref = traces(a.runs), traces(a.ref_runs)
    if a.source == "smalltest":
        items = {}
        for p in Path(a.items_dir).glob("*.jsonl"):
            for line in open(p):
                r = json.loads(line)
                items[r["item_id"]] = r
        orig = {i: s for i, s in scores(a.runs).items()}

        def wrong0(i):
            s = orig.get(i, {})
            return not s.get("correct") if s.get("correct") is not None else (s.get("score", 0) or 0) < 1

        def fixed(it, ans):
            r = SCORERS[it["scorer"]](ans, it)
            return bool(r.get("correct")) if r.get("correct") is not None else (r.get("score", 0) or 0) >= 1
    else:
        items = {r["id"]: r for r in map(json.loads, open(a.pool))}
        orig = {r["id"]: r for r in map(json.loads, _open(Path(a.orig)))}

        def wrong0(i):
            return not orig[i]["correct"]

        def fixed(it, ans):
            return label_grade(it, ans)
    known = json.loads(Path(a.known_gold_errors).read_text()) if a.known_gold_errors else {}

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    counts, rows = Counter(), []
    for i, t in tr.items():
        if i not in items or i not in orig or not wrong0(i):
            continue
        it, final = items[i], t.get("final_answer")
        attempts = (t.get("verifier") or {}).get("attempts", [])
        samples = [s for m in t["models"] for s in m["samples"]]
        calls = t.get("call_log") or []
        cause, detail = None, ""
        if final and fixed(it, final):
            cause, detail = "grader bug", "the fixed graders accept the final answer"
        if not cause:
            for at in attempts:
                ans = at.get("final_answer")
                if ans and ans != final and at.get("verdict") == "reject" and fixed(it, ans):
                    failed = [c.get("name") + ": " + str(c.get("detail"))[:60] for c in at.get("checks", []) if c.get("passed") is False]
                    cause, detail = "verifier bug", f"rejected a correct answer ({'; '.join(failed) or at.get('reason')})"
                    break
        if not cause and (i in known or "interactive problem" in it.get("task", "")[:300].lower()):
            cause, detail = "wrong gold", known.get(i, "interactive problem: fixed stdin/stdout tests cannot judge it")
        if not cause:
            cause = "model wrong"
            if not final:
                detail = "no final answer" + (" (hit the token cap)" if any(c.get("finish_reason") == "length" for c in calls) else "")
            elif any(c.get("finish_reason") == "length" for c in calls):
                detail = "hit the token cap on a call"
            elif any(s.get("final_answer") and fixed(it, s["final_answer"]) for s in samples):
                detail = "a sample was right but lost the vote"
        r = ref.get(i)
        cand = (cause == "model wrong" and final and r is not None and norm(r.get("final_answer")) == norm(final)
                and it.get("task_type") in ("math", "science_mc"))
        counts[cause] += 1
        gold = it.get("gold")
        if gold is None:
            gold = {"code": "the task's tests", "instruction": "no gold: graded by the instruction rules"}.get(
                it.get("task_type"), "rubric / reference in the benchmark")
        rows.append({"id": i, "model": a.model, "source": a.source, "bench": it.get("bench") or it.get("source"),
                     "task_type": it.get("task_type"), "task": (it.get("task") or "")[:2500], "gold": str(gold)[:400],
                     "answer": (final or "")[:700], "cause": cause, "detail": detail, "wrong_gold_candidate": bool(cand),
                     "ref_answer": (r.get("final_answer") or "")[:200] if r else None,
                     "attempts": [{"answer": (x.get("final_answer") or "")[:120], "verdict": x.get("verdict")} for x in attempts]})
    with open(out / "failures.jsonl", "w") as f:
        for row in sorted(rows, key=lambda r: (r["bench"] or "", r["id"])):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summ = {"model": a.model, "source": a.source, "wrong": len(rows), "causes": dict(counts),
            "wrong_gold_candidates": sum(r["wrong_gold_candidate"] for r in rows),
            "by_bench": {b: dict(Counter(r["cause"] for r in rows if r["bench"] == b)) for b in sorted({r["bench"] or "" for r in rows})}}
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
