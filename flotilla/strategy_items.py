"""Label items for test-04 (strategy router): pool questions only, never router B's held-out 10% or any test item.

    python -m flotilla.strategy_items --pool pool.clean.jsonl --n 1500 --pilot 50 --shards 6 --out-dir labelitems_strategy
Draws n questions from the clean pool minus router B's held-out split (router_b.split, by question id), stratified by
task type in proportion to the pool, seeded. Writes pilot.jsonl (the first `pilot`, same mix) and strat_KK.jsonl shards
of the rest, plus ids.json recording what was drawn and what was excluded.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from flotilla.router_b import split

SEED = 20261120


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--pilot", type=int, default=50)
    ap.add_argument("--shards", type=int, default=6)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.pool)]
    held_out, _ = split([{"id": r["id"]} for r in rows])
    held = {r["id"] for r in held_out}
    by_type = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["id"]):
        if r["id"] not in held:
            by_type[r["task_type"]].append(r)
    rng = random.Random(SEED)
    total = sum(len(v) for v in by_type.values())
    picked = {t: rng.sample(v, round(a.n * len(v) / total)) for t, v in by_type.items()}
    order = []  # interleave types so the pilot and every shard keep the same mix
    while any(picked.values()):
        for t in sorted(picked):
            if picked[t]:
                order.append(picked[t].pop())
    item = lambda r, bench: {"item_id": r["id"], "bench": bench, "scorer": "router_label", "task_type": r["task_type"],
                             "task": r["task"], "source": r["source"], "gold": None}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "pilot.jsonl", "w") as f:
        f.writelines(json.dumps(item(r, "pilot")) + "\n" for r in order[: a.pilot])
    rest = order[a.pilot:]
    for k in range(a.shards):
        with open(out / f"strat_{k:02d}.jsonl", "w") as f:
            f.writelines(json.dumps(item(r, f"strat_{k:02d}")) + "\n" for r in rest[k::a.shards])
    mix = defaultdict(int)
    for r in order:
        mix[r["task_type"]] += 1
    (out / "ids.json").write_text(json.dumps({"seed": SEED, "drawn": len(order), "pilot": [r["id"] for r in order[: a.pilot]],
                                               "full": [r["id"] for r in rest], "mix": mix, "excluded_router_b_held_out": len(held),
                                               "pool": len(rows)}, indent=1))
    print(json.dumps({"drawn": len(order), "pilot": a.pilot, "shards": a.shards, "mix": mix, "excluded_held_out": len(held)}))


if __name__ == "__main__":
    main()
