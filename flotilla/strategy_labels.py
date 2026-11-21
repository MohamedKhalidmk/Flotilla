"""test-04: grade every strategy on every labelled question, pick each question's label, split train/dev/held-out.

    python -m flotilla.strategy_labels --pool pool.clean.jsonl --runs fast=DIR [DIR ...] tools=DIR deep=DIR vote=DIR \
        --out OUT_DIR [--split]
Per question and strategy: correct (router-label graders, code fences stripped), output tokens, calls, wall seconds.
Label = the cheapest strategy that is correct, in ORDER (cheapest first, combos included); "none" if none is.
Memory routes (memory, memory_deep, vote_memory, deep_tools_memory) exist only on items with a history (LongMemEval):
    --memory-items LME.jsonl --verdicts verdicts.jsonl   (verdicts: python -m flotilla.memory_route judge)
A route is "available" on an item when it was run on the item's group (pool or memory); an item missing a route its
group ran is dropped and counted. Unavailable routes never count as wrong; the label is the first correct available
route. The GRAFT build cost is counted once per history (graft_build in per_question rows and summary).
--split writes split.json: 70% train, 15% dev, 15% held-out, stratified by (benchmark source, task type), seeded.
Outputs: per_question.jsonl, summary.json (accuracy, mean tokens and seconds per strategy, label counts, GPU-seconds).
"""
import argparse
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path

from flotilla.label_loop import grade

# cheapest first; combos sit after their parts (pilot GPU-seconds decide the final order before training).
# Memory routes come after every base route, each in its base route's cost order: they add a GRAFT build per history
# (about a hundred Qwen calls) and run only on LongMemEval items; measured GPU-seconds, build included, decide the
# final order.
ORDER = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools",
         "memory", "memory_deep", "deep_tools_memory", "vote_memory"]
MEMORY_ROUTES = ("memory", "memory_deep", "deep_tools_memory", "vote_memory")
SEED = 20261120


def load_traces(dirs: list[str]) -> dict[str, dict]:
    out = {}
    for d in dirs:
        p = Path(d) / "trace.jsonl"
        if p.exists():
            for line in open(p):
                t = json.loads(line)
                out[t["item_id"]] = t
    return out


def _grade(args: tuple) -> bool:
    return grade(*args)


def gpu_seconds(dirs: list[str]) -> float:
    tot = 0.0
    for d in dirs:
        c = Path(d) / "compute.json"
        if c.exists():
            tot += sum(s["gpu_seconds_run"] for s in json.loads(c.read_text())["servers"].values())
    return round(tot, 1)


def load_verdicts(path: str | None) -> dict[tuple[str, str], bool]:
    out = {}
    if path:
        for line in open(path):
            r = json.loads(line)
            out[(r["item_id"], r["route"])] = bool(r["correct"])
    return out


def prepare_seconds(dirs: list[str]) -> float:
    """Wall seconds a Memory-route run spent building or loading GRAFT graphs (graft_prepare.json), inside its GPU time."""
    return round(sum(json.loads((Path(d) / "graft_prepare.json").read_text())["wall_seconds"]
                     for d in dirs if (Path(d) / "graft_prepare.json").exists()), 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="strategy=DIR [DIR ...] groups, e.g. fast=a fast=b deep=c")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--memory-items", help="LongMemEval items (JSONL with item_id); graded by --verdicts")
    ap.add_argument("--verdicts", help="judge verdicts for LongMemEval answers (flotilla.memory_route judge)")
    ap.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1), help="parallel graders (code tests run in subprocesses)")
    a = ap.parse_args()
    runs = defaultdict(list)
    for kv in a.runs:
        k, v = kv.split("=", 1)
        runs[k].append(v)
    pool = {}
    for line in open(a.pool):
        r = json.loads(line)
        pool[r["id"]] = r
    if a.memory_items:
        for line in open(a.memory_items):
            r = json.loads(line)
            pool[r["item_id"]] = {"id": r["item_id"], "source": r.get("source", "longmemeval"), "task_type": "memory",
                                  "question_type": r.get("question_type")}
    verdicts_in = load_verdicts(a.verdicts)
    traces = {s: load_traces(runs[s]) for s in ORDER if s in runs}
    # groups: pool questions and memory (history) questions; each group requires every route run on any of its items
    group = lambda i: "memory" if pool[i]["task_type"] == "memory" else "pool"  # noqa: E731
    seen = {i for t in traces.values() for i in t if i in pool}
    required = {g: [s for s in traces if any(group(i) == g for i in traces[s] if i in pool)] for g in ("pool", "memory")}
    ids = sorted(i for i in seen if all(i in traces[s] for s in required[group(i)]))
    dropped = len(seen) - len(ids)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(i, s) for i in ids for s in required[group(i)] if group(i) == "pool"]
    with ProcessPoolExecutor(a.workers) as ex:
        verdicts = dict(zip(jobs, ex.map(_grade, [(pool[i], traces[s][i]["final_answer"]) for i, s in jobs], chunksize=8)))
    missing = [(i, s) for i in ids if group(i) == "memory" for s in required["memory"] if (i, s) not in verdicts_in]
    if missing:
        raise SystemExit(f"{len(missing)} LongMemEval answers have no judge verdict (e.g. {missing[:3]}); "
                         "run python -m flotilla.memory_route judge first")
    verdicts.update({(i, s): verdicts_in[(i, s)] for i in ids if group(i) == "memory" for s in required["memory"]})
    rows, labels = [], Counter()
    with open(out / "per_question.jsonl", "w") as f:
        for i in ids:
            it = pool[i]
            row = {"id": i, "source": it["source"], "task_type": it["task_type"]}
            for s, tr in traces.items():
                if s not in required[group(i)]:
                    row[s] = {"available": False}
                    continue
                t = tr[i]
                samples = [x for m in t["models"] for x in m["samples"]]
                row[s] = {"available": True, "correct": verdicts[(i, s)],
                          "tokens_out": sum(x.get("tokens_out", 0) for x in samples),
                          "calls": t.get("calls"), "wall_seconds": t.get("wall_seconds"), "answer": (t["final_answer"] or "")[:500]}
                build = (t.get("retrieval") or {}).get("graft_build")
                if build and "graft_build" not in row:  # once per history, whichever Memory route carries it
                    row["graft_build"] = {k: build.get(k) for k in ("llm_calls", "input_tokens", "output_tokens",
                                                                    "llm_seconds", "wall_seconds")}
            row["label"] = next((s for s in ORDER if s in traces and row[s].get("available") and row[s]["correct"]), "none")
            labels[row["label"]] += 1
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n = len(rows)

    def stats(s):
        rs = [r for r in rows if r[s].get("available")]
        k = len(rs) or 1
        return {"questions_available": len(rs), "accuracy": round(sum(r[s]["correct"] for r in rs) / k, 4),
                "mean_output_tokens": round(sum(r[s]["tokens_out"] for r in rs) / k, 1),
                "mean_wall_seconds": round(sum(r[s]["wall_seconds"] or 0 for r in rs) / k, 1),
                "max_wall_seconds": round(max([r[s]["wall_seconds"] or 0 for r in rs] or [0]), 1),
                "gpu_seconds_job": gpu_seconds(runs[s]), "graft_prepare_seconds": prepare_seconds(runs[s])}
    builds = [r["graft_build"] for r in rows if "graft_build" in r]
    summary = {"questions": n, "dropped_incomplete": dropped, "labels": dict(labels),
               "per_strategy": {s: stats(s) for s in traces},
               "graft_build": {"histories": len(builds),
                               **{k: sum(b.get(k) or 0 for b in builds) for k in ("llm_calls", "input_tokens", "output_tokens",
                                                                                  "wall_seconds")}},
               "best_any_strategy": round(sum(r["label"] != "none" for r in rows) / max(n, 1), 4)}
    if a.split:
        groups = defaultdict(list)
        for r in rows:
            groups[(r["source"], r["task_type"])].append(r["id"])
        rng = random.Random(SEED)
        sp = {"train": [], "dev": [], "held_out": []}
        for key in sorted(groups):
            g = sorted(groups[key])
            rng.shuffle(g)
            k1, k2 = round(0.70 * len(g)), round(0.85 * len(g))
            sp["train"] += g[:k1]
            sp["dev"] += g[k1:k2]
            sp["held_out"] += g[k2:]
        (out / "split.json").write_text(json.dumps({"seed": SEED, "stratified_by": ["source", "task_type"], **sp}, indent=1))
        summary["split"] = {k: len(v) for k, v in sp.items()}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
