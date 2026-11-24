"""test-04: grade every strategy on every labelled question, pick each question's label, split train/dev/held-out.

    python -m flotilla.routers.strategy_labels --pool pool.clean.jsonl --runs fast=DIR [DIR ...] tools=DIR deep=DIR vote=DIR \
        --out OUT_DIR [--split]
Per question and strategy: correct (router-label graders, code fences stripped), output tokens, calls, wall seconds.
Label = the cheapest strategy that is correct; "none" if none is. Cheapest is judged per row (2026-11-21): by the row's
own per-route gpu_seconds when it has them (the --pool-labels merge adds them), ties and rows without them in ORDER
(cheapest first, combos included). The ORDER-only label is kept as label_order.
Memory routes (memory, memory_deep, vote_memory, deep_tools_memory) exist only on items with a history (LongMemEval):
    --memory-items LME.jsonl --verdicts verdicts.jsonl   (verdicts: python -m flotilla.memory.memory_route judge)
A route is "available" on an item when it was run on the item's group (pool or memory); an item missing a route its
group ran is dropped and counted. Unavailable routes never count as wrong; the label is the first correct available
route. The GRAFT build cost is counted once per history (graft_build in per_question rows and summary).
--split writes split.json: 70% train, 15% dev, 15% held-out, stratified by (benchmark source, task type), seeded.
Outputs: per_question.jsonl, summary.json (accuracy, mean tokens and seconds per strategy, label counts, GPU-seconds).

Adding LongMemEval to finished pool labels (test 04, 2026-11-21), without regrading the pool:
    --pool-labels POOL_DIR --memory-items LME.jsonl --verdicts V.jsonl --memory-split LME_SPLIT.json \
        --runs fast=DIR ... memory=DIR ... [--build-runs PREP_DIR ...] --out NEW_DIR
POOL_DIR's rows are copied unchanged (the Memory routes marked unavailable); --runs then hold LongMemEval runs only.
split.json = POOL_DIR's split + LME_SPLIT.json's. Every row gets per-route "gpu_seconds", so a router costs each item
in its own group: the group's GPU-seconds per wall-second for that route (job GPU-s / questions / mean wall-s) times
the row's wall seconds, which is the number strategy_router used for the pool rows before. Memory routes add the
history's GRAFT build (prepare jobs' GPU-seconds shared out by each history's LLM seconds) to their gpu_seconds, as a
router that picks a Memory route must build the graph; gpu_seconds_answer and gpu_seconds_build keep the two apart.
summary.json: per route over all rows where it is available, plus by_group (pool as POOL_DIR's summary, longmemeval);
summary_longmemeval.json and per_question_longmemeval.jsonl hold the LongMemEval part alone.
"""
import argparse
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path

from flotilla.routers.label_loop import grade

# cheapest first; combos sit after their parts (pilot GPU-seconds decide the final order before training).
# Memory routes come after every base route, each in its base route's cost order: they add a GRAFT build per history
# (about a hundred Qwen calls) and run only on LongMemEval items; measured GPU-seconds, build included, decide the
# final order.
ORDER = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools",
         "memory", "memory_deep", "deep_tools_memory", "vote_memory"]
MEMORY_ROUTES = ("memory", "memory_deep", "deep_tools_memory", "vote_memory")
SEED = 20261120


def cheapest_label(row: dict) -> str:
    """Cheapest correct available route of one row: lowest gpu_seconds where every correct route has one, ties
    broken by ORDER; otherwise the first correct route in ORDER. "none" if no route is correct."""
    ok = [s for s in ORDER if isinstance(row.get(s), dict) and row[s].get("available") and row[s].get("correct")]
    if not ok:
        return "none"
    if all(row[s].get("gpu_seconds") is not None for s in ok):
        return min(ok, key=lambda s: (row[s]["gpu_seconds"], ORDER.index(s)))
    return ok[0]


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
    """Judge verdicts keyed by (item, route). Stops, naming them, if any (item, route) has more than one verdict:
    a second verdict would silently replace the first."""
    out, dup = {}, set()
    if path:
        for line in open(path):
            r = json.loads(line)
            k = (r["item_id"], r["route"])
            if k in out:
                dup.add(k)
            out[k] = bool(r["correct"])
    if dup:
        raise SystemExit(f"{len(dup)} (item, route) pairs have more than one judge verdict: " + name_pairs(sorted(dup)))
    return out


def name_pairs(pairs: list[tuple[str, str]]) -> str:
    """Every (item, route) pair, grouped by route: 'memory: lme-1, lme-2; deep: lme-3'."""
    by = {}
    for i, s in pairs:
        by.setdefault(s, []).append(i)
    return "; ".join(f"{s}: {', '.join(ids)}" for s, ids in by.items())


def verdict_problems(memory_ids: list[str], answered: set[str], routes: list[str],
                     verdicts: dict[tuple[str, str], bool]) -> list[str]:
    """Every LongMemEval question must have exactly one judge verdict per route (duplicates stop load_verdicts).
    Returns one message per problem, naming every item: questions with no answer in some route, then answers with
    no verdict."""
    out = []
    unanswered = [i for i in memory_ids if i not in answered]
    if unanswered:
        out.append(f"{len(unanswered)} LongMemEval questions have no answer in every route: {', '.join(unanswered)}")
    missing = [(i, s) for i in memory_ids if i in answered for s in routes if (i, s) not in verdicts]
    if missing:
        out.append(f"{len(missing)} LongMemEval answers have no judge verdict: {name_pairs(missing)}")
    return out


def prepare_seconds(dirs: list[str]) -> float:
    """Wall seconds a Memory-route run spent building or loading GRAFT graphs (graft_prepare.json), inside its GPU time."""
    return round(sum(json.loads((Path(d) / "graft_prepare.json").read_text())["wall_seconds"]
                     for d in dirs if (Path(d) / "graft_prepare.json").exists()), 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", help="pool questions (JSONL with id); not needed with --pool-labels")
    ap.add_argument("--pool-labels", help="finished pool labels folder (per_question.jsonl, split.json, summary.json) to merge")
    ap.add_argument("--memory-split", help="split.json of the --memory-items (LongMemEval's own)")
    ap.add_argument("--build-runs", nargs="*", default=[], help="memory_route prepare run folders (compute.json)")
    ap.add_argument("--graft-cache", help="GRAFT cache with prepare-*.json (per-history build cost)")
    ap.add_argument("--runs", nargs="+", required=True, help="strategy=DIR [DIR ...] groups, e.g. fast=a fast=b deep=c")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--memory-items", help="LongMemEval items (JSONL with item_id); graded by --verdicts")
    ap.add_argument("--verdicts", help="judge verdicts for LongMemEval answers (flotilla.memory.memory_route judge)")
    ap.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1), help="parallel graders (code tests run in subprocesses)")
    a = ap.parse_args()
    runs = defaultdict(list)
    for kv in a.runs:
        k, v = kv.split("=", 1)
        runs[k].append(v)
    if not a.pool and not a.pool_labels:
        ap.error("--pool or --pool-labels is required")
    pool = {}
    for line in (open(a.pool) if a.pool else []):
        r = json.loads(line)
        pool[r["id"]] = r
    if a.memory_items:
        from flotilla.memory.memory_route import question_text
        for line in open(a.memory_items):
            r = json.loads(line)
            pool[r["item_id"]] = {"id": r["item_id"], "source": r.get("source", "longmemeval"), "task_type": "memory",
                                  "question_type": r.get("question_type"), "task": question_text(r)}
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
    memory_ids = sorted(i for i in pool if group(i) == "memory") if required["memory"] else []
    problems = verdict_problems(memory_ids, set(ids), required["memory"], verdicts_in)
    if problems:
        raise SystemExit("merge stopped:\n" + "\n".join(problems) + "\n(run python -m flotilla.memory.memory_route judge, "
                         "or rerun the missing answers, first)")
    verdicts.update({(i, s): verdicts_in[(i, s)] for i in ids if group(i) == "memory" for s in required["memory"]})
    rows, labels = [], Counter()
    with open(out / "per_question.jsonl", "w") as f:
        for i in ids:
            it = pool[i]
            row = {"id": i, "source": it["source"], "task_type": it["task_type"]}
            if it["task_type"] == "memory":  # what a router reads for a LongMemEval item: the question, not the history
                row.update({"question_type": it.get("question_type"), "task": it.get("task")})
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
    if a.pool_labels:
        summary = merge_pool_labels(a, out, rows, summary, runs)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def _rates(rows: list[dict], per: dict) -> dict:
    """Route -> GPU-seconds per wall-second in this group (job GPU-s / questions / mean wall-s), as strategy_router."""
    out = {}
    for s, st in per.items():
        n = st.get("questions_available") or len(rows)
        wall = st.get("mean_wall_seconds") or 0
        out[s] = (st["gpu_seconds_job"] / n) / wall if wall > 0 and n else None
    return out


def build_gpu_seconds(a, ids: list[str]) -> tuple[dict, dict]:
    """History -> GPU-seconds of its GRAFT build: the prepare jobs' GPU-seconds shared out by LLM seconds."""
    total = sum(json.loads((Path(d) / "compute.json").read_text())["servers"][k]["gpu_seconds_run"]
                for d in a.build_runs if (Path(d) / "compute.json").exists()
                for k in json.loads((Path(d) / "compute.json").read_text())["servers"])
    llm = {}
    for p in sorted(Path(a.graft_cache).glob("prepare-*.json")) if a.graft_cache else []:
        for k, v in json.loads(p.read_text()).get("per_history", {}).items():
            if not v.get("cache_hit") and v.get("llm_seconds"):
                llm[k] = v["llm_seconds"]
    tot_llm = sum(llm[i] for i in ids if i in llm)
    share = {i: total * llm[i] / tot_llm for i in ids if i in llm} if tot_llm else {}
    return share, {"prepare_gpu_seconds": round(total, 1), "histories_with_build_cost": len(share),
                   "mean_gpu_seconds_per_history": round(total / max(len(share), 1), 1)}


def merge_pool_labels(a, out: Path, lme_rows: list[dict], lme_summary: dict, runs: dict) -> dict:
    """The LongMemEval rows (graded here) plus the finished pool labels (copied): see the module docstring."""
    pdir = Path(a.pool_labels)
    if out.resolve() == pdir.resolve():
        raise SystemExit("--out must be a new folder: the pool labels are never overwritten")
    psum = json.loads((pdir / "summary.json").read_text())
    psplit = json.loads((pdir / "split.json").read_text())
    prows = [json.loads(l) for l in open(pdir / "per_question.jsonl")]
    mem_routes = [s for s in lme_summary["per_strategy"] if s in MEMORY_ROUTES]
    prate = _rates(prows, psum["per_strategy"])
    lrate = _rates(lme_rows, lme_summary["per_strategy"])
    ids = [r["id"] for r in lme_rows]
    build, build_info = build_gpu_seconds(a, ids)
    for r in prows:
        for s, v in list(r.items()):
            # pool labels written before routes carried "available" (run-03): a route with a verdict was run on the row
            if isinstance(v, dict) and "correct" in v and "available" not in v:
                v["available"] = True
            if isinstance(v, dict) and v.get("available") and prate.get(s) is not None:
                v["gpu_seconds"] = round(prate[s] * (v.get("wall_seconds") or 0), 3)
        for s in mem_routes:
            r[s] = {"available": False}
    for r in lme_rows:
        for s, v in list(r.items()):
            if isinstance(v, dict) and v.get("available"):
                ans = round((lrate.get(s) or 0) * (v.get("wall_seconds") or 0), 3)
                if s in MEMORY_ROUTES:
                    b = round(build.get(r["id"], build_info["mean_gpu_seconds_per_history"]), 3)
                    v.update({"gpu_seconds_answer": ans, "gpu_seconds_build": b, "gpu_seconds": round(ans + b, 3)})
                else:
                    v["gpu_seconds"] = ans
    for r in lme_rows:
        r["label_order"], r["label"] = r["label"], cheapest_label(r)
    lme_summary = {**lme_summary, "labels_order": lme_summary["labels"],
                   "labels": dict(Counter(r["label"] for r in lme_rows))}
    (out / "per_question_longmemeval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lme_rows))
    (out / "summary_longmemeval.json").write_text(json.dumps({**lme_summary, "graft_build_gpu": build_info}, indent=1))
    rows = prows + lme_rows
    changed = Counter()
    for r in rows:  # per-row cost order now that every row has its gpu_seconds
        r["label_order"] = r.get("label_order", r["label"])
        r["label"] = cheapest_label(r)
        if r["label"] != r["label_order"]:
            changed["pool" if r.get("task_type") != "memory" else "longmemeval"] += 1
    with open(out / "per_question.jsonl", "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    msplit = json.loads(Path(a.memory_split).read_text()) if a.memory_split else {}
    sp = {k: list(psplit[k]) + list(msplit.get(k, [])) for k in ("train", "dev", "held_out")}
    missing = [i for i in ids if not any(i in msplit.get(k, []) for k in sp)]
    if missing:
        raise SystemExit(f"{len(missing)} LongMemEval items are in no split of --memory-split, e.g. {missing[:3]}")
    (out / "split.json").write_text(json.dumps({"seed": psplit.get("seed"), "pool": {k: v for k, v in psplit.items()
                                                                                     if k not in sp},
                                                "longmemeval": {"source": a.memory_split, **{k: v for k, v in msplit.items()
                                                                                             if k not in sp}},
                                                **sp}, indent=1))
    order = [s for s in ORDER if s in psum["per_strategy"] or s in lme_summary["per_strategy"]]
    per = {}
    for s in order:
        rs = [r for r in rows if r.get(s, {}).get("available")]
        k = len(rs) or 1
        gp = (psum["per_strategy"].get(s) or {}).get("gpu_seconds_job", 0)
        gl = (lme_summary["per_strategy"].get(s) or {}).get("gpu_seconds_job", 0)
        per[s] = {"questions": len(rs), "questions_available": len(rs),
                  "accuracy": round(sum(bool(r[s]["correct"]) for r in rs) / k, 4),
                  "mean_output_tokens": round(sum(r[s].get("tokens_out") or 0 for r in rs) / k, 1),
                  "mean_wall_seconds": round(sum(r[s].get("wall_seconds") or 0 for r in rs) / k, 1),
                  "gpu_seconds_job": round(gp + gl, 1),
                  "gpu_seconds_per_question": round(sum(r[s].get("gpu_seconds") or 0 for r in rs) / k, 3)}
    labels = Counter(r["label"] for r in rows)
    return {"questions": len(rows), "groups": {"pool": len(prows), "longmemeval": len(lme_rows)},
            "labels": dict(labels), "labels_order": dict(Counter(r["label_order"] for r in rows)),
            "labels_changed_by_row_cost": dict(changed), "per_strategy": per,
            "by_group": {"pool": {"from": str(pdir), "questions": psum["questions"], "labels": psum["labels"],
                                  "per_strategy": psum["per_strategy"], "best_any_strategy": psum.get("best_any_strategy"),
                                  "labels_by_row_cost": dict(Counter(r["label"] for r in prows))},
                         "longmemeval": {k: lme_summary[k] for k in ("questions", "labels", "labels_order", "per_strategy", "graft_build",
                                                                     "best_any_strategy") if k in lme_summary}},
            "graft_build_gpu": build_info, "split": {k: len(v) for k, v in sp.items()},
            "best_any_strategy": round(sum(r["label"] != "none" for r in rows) / max(len(rows), 1), 4),
            "dropped_incomplete": lme_summary.get("dropped_incomplete")}


if __name__ == "__main__":
    main()
