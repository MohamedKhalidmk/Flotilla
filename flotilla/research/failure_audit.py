"""test-04: overlap between routes and the causes of failures, from the same traces strategy_labels.py grades.

    python -m flotilla.research.failure_audit --pool pool.clean.jsonl --runs fast=DIR [DIR ...] tools=DIR ... --out OUT_DIR
Writes overlap.json (per route: questions only it got right; questions it got wrong that another route got right) and
failures.jsonl (every question every route got wrong, one row per route, with the automatic cause and the evidence a
person needs to check it by hand: gold, final answer, every verifier attempt, every sample, finish reasons, text tails).

Automatic causes, checked in this order (first match wins):
  cap            a model call stopped at the token cap (finish_reason "length")
  no_answer      the loop ended without a final answer (format failure, empty reply)
  verifier       a verifier attempt held an answer the grader accepts, but the final answer differs (retry hurt)
  vote           a sample held an answer the grader accepts, but the vote picked another
  grader_suspect the gold answer appears in the final answer or the answer text, yet the grader said wrong
  wrong          none of the above: the model's answer is wrong
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from flotilla.routers.label_loop import grade
from flotilla.routers.strategy_labels import ORDER, load_traces


def _norm(s: str) -> str:
    return re.sub(r"[\s$\\{}]|\\text|\\boxed|\\left|\\right", "", str(s)).lower()


def cause(item: dict, t: dict) -> str:
    calls = t.get("call_log") or []
    if any(c.get("finish_reason") == "length" for c in calls):
        return "cap"
    if not t.get("final_answer"):
        return "no_answer"
    attempts = (t.get("verifier") or {}).get("attempts", [])
    if any(a.get("final_answer") and a["final_answer"] != t["final_answer"] and grade(item, a["final_answer"]) for a in attempts):
        return "verifier"
    samples = [s for m in t["models"] for s in m["samples"]]
    if any(s.get("final_answer") and s["final_answer"] != t["final_answer"] and grade(item, s["final_answer"]) for s in samples):
        return "vote"
    gold = item.get("gold")
    if gold is not None and item["task_type"] in ("math", "science_mc"):
        g = _norm(gold)
        if g and (g == _norm(t["final_answer"]) or (item["task_type"] == "math" and len(g) >= 2 and g in _norm(t["final_answer"]))):
            return "grader_suspect"
    return "wrong"


def evidence(item: dict, t: dict) -> dict:
    samples = [s for m in t["models"] for s in m["samples"]]
    return {"final_answer": (t.get("final_answer") or "")[:400],
            "attempts": [{"answer": (a.get("final_answer") or "")[:200], "verdict": a.get("verdict"), "reason": (a.get("reason") or "")[:300],
                          "checks": [(c.get("name"), c.get("passed"), str(c.get("detail"))[:150]) for c in a.get("checks", [])]}
                         for a in (t.get("verifier") or {}).get("attempts", [])],
            "samples": [{"answer": (s.get("final_answer") or "")[:200], "tokens_out": s.get("tokens_out"), "text_tail": (s.get("text") or "")[-300:]}
                        for s in samples],
            "calls": [{"finish": c.get("finish_reason"), "tokens_out": c.get("tokens_out"), "tool_calls": c.get("tool_calls"),
                       "content_tail": (c.get("content_tail") or "")[-200:], "reasoning_tail": (c.get("reasoning_tail") or "")[-300:]}
                      for c in t.get("call_log") or []],
            "vote": t.get("vote"), "tools": [(x.get("name"), x.get("ok")) for x in t.get("tools", [])][:10]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--graded", default=None, help="per_question.jsonl from strategy_labels: reuse its verdicts")
    a = ap.parse_args()
    runs = defaultdict(list)
    for kv in a.runs:
        k, v = kv.split("=", 1)
        runs[k].append(v)
    pool = {r["id"]: r for r in map(json.loads, open(a.pool))}
    routes = [s for s in ORDER if s in runs]
    traces = {s: load_traces(runs[s]) for s in routes}
    ids = sorted(set.intersection(*(set(t) for t in traces.values())))
    if a.graded:
        g = {r["id"]: r for r in map(json.loads, open(a.graded))}
        ok = {i: {s: g[i][s]["correct"] for s in routes} for i in ids}
    else:
        ok = {i: {s: grade(pool[i], traces[s][i]["final_answer"]) for s in routes} for i in ids}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    overlap = {}
    for s in routes:
        only = [i for i in ids if ok[i][s] and not any(ok[i][o] for o in routes if o != s)]
        missed = [i for i in ids if not ok[i][s] and any(ok[i][o] for o in routes if o != s)]
        overlap[s] = {"correct": sum(ok[i][s] for i in ids), "only_this_route_right": len(only),
                      "wrong_but_another_route_right": len(missed),
                      "only_ids": only, "missed_ids": missed,
                      "missed_by_task": dict(Counter(pool[i]["task_type"] for i in missed)),
                      "missed_causes": dict(Counter(cause(pool[i], traces[s][i]) for i in missed))}
    all_wrong = [i for i in ids if not any(ok[i].values())]
    causes = Counter()
    with open(out / "failures.jsonl", "w") as f:
        for i in all_wrong:
            it = pool[i]
            for s in routes:
                c = cause(it, traces[s][i])
                causes[(s, c)] += 1
                f.write(json.dumps({"id": i, "route": s, "task_type": it["task_type"], "source": it["source"],
                                    "task": it["task"][:1500], "gold": str(it.get("gold"))[:300], "auto_cause": c,
                                    **evidence(it, traces[s][i])}, ensure_ascii=False) + "\n")
    summary = {"questions": len(ids), "routes": routes, "all_wrong": len(all_wrong),
               "all_wrong_by_task": dict(Counter(pool[i]["task_type"] for i in all_wrong)),
               "all_wrong_causes_per_route": {s: {c: n for (r, c), n in causes.items() if r == s} for s in routes},
               "overlap": {s: {k: v for k, v in o.items() if not k.endswith("_ids")} for s, o in overlap.items()}}
    (out / "overlap.json").write_text(json.dumps({"summary": summary, "per_route": overlap}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
