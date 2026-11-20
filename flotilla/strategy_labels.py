"""test-04: grade every strategy on every labelled question, pick each question's label, split train/dev/held-out.

    python -m flotilla.strategy_labels --pool pool.clean.jsonl --runs fast=DIR [DIR ...] tools=DIR deep=DIR vote=DIR \
        --out OUT_DIR [--split]
Per question and strategy: correct (router-label graders, code fences stripped), output tokens, calls, wall seconds.
Label = the cheapest strategy that is correct, in ORDER (cheapest first, combos included); "none" if none is.
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

# cheapest first; combos sit after their parts (pilot GPU-seconds decide the final order before training)
ORDER = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools"]
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="strategy=DIR [DIR ...] groups, e.g. fast=a fast=b deep=c")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", action="store_true")
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
    traces = {s: load_traces(runs[s]) for s in ORDER if s in runs}
    ids = sorted(set.intersection(*(set(t) for t in traces.values())))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(i, s) for i in ids for s in traces]
    with ProcessPoolExecutor(a.workers) as ex:
        verdicts = dict(zip(jobs, ex.map(_grade, [(pool[i], traces[s][i]["final_answer"]) for i, s in jobs], chunksize=8)))
    rows, labels = [], Counter()
    with open(out / "per_question.jsonl", "w") as f:
        for i in ids:
            it = pool[i]
            row = {"id": i, "source": it["source"], "task_type": it["task_type"]}
            for s, tr in traces.items():
                t = tr[i]
                samples = [x for m in t["models"] for x in m["samples"]]
                row[s] = {"correct": verdicts[(i, s)], "tokens_out": sum(x.get("tokens_out", 0) for x in samples),
                          "calls": t.get("calls"), "wall_seconds": t.get("wall_seconds"), "answer": (t["final_answer"] or "")[:500]}
            row["label"] = next((s for s in ORDER if s in traces and row[s]["correct"]), "none")
            labels[row["label"]] += 1
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n = len(rows)
    summary = {"questions": n, "labels": dict(labels),
               "per_strategy": {s: {"accuracy": round(sum(r[s]["correct"] for r in rows) / n, 4),
                                    "mean_output_tokens": round(sum(r[s]["tokens_out"] for r in rows) / n, 1),
                                    "mean_wall_seconds": round(sum(r[s]["wall_seconds"] or 0 for r in rows) / n, 1),
                                    "max_wall_seconds": round(max(r[s]["wall_seconds"] or 0 for r in rows), 1),
                                    "gpu_seconds_job": gpu_seconds(runs[s])} for s in traces},
               "best_any_strategy": round(sum(r["label"] != "none" for r in rows) / n, 4)}
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
