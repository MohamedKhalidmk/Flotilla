"""Router labels through the real Flotilla loop (same tools, prompts, verifier and retry as the small tests).

The first labels (flotilla/router_labels.py) made one plain generation call with a prompt that offers tools but ran no
tool loop, so answers that called a tool ended without a final answer. They are kept, marked v1, and not used.

    python -m flotilla.label_loop make-items --pool $SCRATCH/flotilla/router/pool.clean.jsonl \
        --out-dir $SCRATCH/flotilla/labelitems --shard-size 300
    # then serve each shard like a small-test group: python -m flotilla.serve ... --items-dir labelitems --benches label_03
    python -m flotilla.label_loop score --pool .../pool.clean.jsonl --runs RUN_DIR [RUN_DIR ...] --model qwen \
        --out $SCRATCH/flotilla/runs/router-labels-loop-qwen

Items carry only what the model sees (task, task type); grading reads the gold answers and code tests from the pool,
so traces stay small. Every answer is kept with its score, tokens, calls and time per question.
"""
import argparse
import json
from pathlib import Path

from flotilla import tools


def grade(item: dict, answer: str | None) -> bool:
    """The router-label graders (same as flotilla/router_labels.py, kept identical for continuity)."""
    if answer is None:
        return False
    t = item["task_type"]
    if t == "math":
        return tools.sympy_check(answer, item["gold"])["ok"]
    if t == "science_mc":
        return answer.strip().upper()[:1] == str(item["gold"]).strip().upper()[:1]
    if t == "code":  # strip markdown fences as the small-test scorer does (v1 labels did not: fenced code always failed)
        from flotilla.scoring import strip_fence
        return tools.run_public_tests(strip_fence(answer), item["tests"], timeout_s=6)["ok"]
    if t == "instruction":
        return tools.constraint_check(item["task"], answer)["ok"]
    return False


def make_items(pool: str, out_dir: str, shard_size: int) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(pool)]
    n_shards = (len(rows) + shard_size - 1) // shard_size
    # spread task types evenly over shards (round robin), so every shard takes about as long
    shards = [[] for _ in range(n_shards)]
    for i, r in enumerate(sorted(rows, key=lambda r: (r["task_type"], r["id"]))):
        shards[i % n_shards].append(r)
    for k, rs in enumerate(shards):
        with open(out / f"label_{k:02d}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps({"item_id": r["id"], "bench": f"label_{k:02d}", "scorer": "router_label",
                                    "task_type": r["task_type"], "task": r["task"], "source": r["source"],
                                    "gold": None}) + "\n")
    print(f"{len(rows)} questions -> {n_shards} shards of about {shard_size} in {out}")


def score(pool: str, runs: list[str], model: str, out_dir: str) -> None:
    items = {}
    for l in open(pool):
        r = json.loads(l)
        items[r["id"]] = r
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = ok = 0
    with open(out / "labels.jsonl", "w") as f:
        for run in runs:
            p = Path(run) / "trace.jsonl"
            if not p.exists():
                continue
            for line in open(p):
                t = json.loads(line)
                it = items[t["item_id"]]
                good = grade(it, t["final_answer"])
                samples = [s for m in t["models"] for s in m["samples"]]
                n += 1
                ok += good
                f.write(json.dumps({"id": it["id"], "source": it["source"], "task_type": it["task_type"], "model": model,
                                    "answer": (t["final_answer"] or "")[:4000], "correct": good,
                                    "tokens_out": sum(s.get("tokens_out", 0) for s in samples),
                                    "tokens_total": t.get("tokens_total"), "calls": t.get("calls"),
                                    "wall_seconds": t.get("wall_seconds"), "samples": len(samples),
                                    "tool_calls": len(t.get("tools", [])), "error_stage": t.get("error_stage"),
                                    "run": str(run)}) + "\n")
    (out / "summary.json").write_text(json.dumps({"model": model, "n": n, "correct": ok, "runs": runs}, indent=1))
    print(json.dumps({"model": model, "n": n, "correct": ok}))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make-items")
    m.add_argument("--pool", required=True)
    m.add_argument("--out-dir", required=True)
    m.add_argument("--shard-size", type=int, default=300)
    s = sub.add_parser("score")
    s.add_argument("--pool", required=True)
    s.add_argument("--runs", nargs="+", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "make-items":
        make_items(a.pool, a.out_dir, a.shard_size)
    else:
        score(a.pool, a.runs, a.model, a.out)


if __name__ == "__main__":
    main()
