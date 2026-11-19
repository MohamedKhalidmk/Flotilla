"""Routing accuracy on items whose true task type is known (router pool sources).

    python -m flotilla.eval_router --router a --pool $SCRATCH/flotilla/router/pool.clean.jsonl --n 500
"""
import argparse
import json
import random
from collections import Counter, defaultdict

from huggingface_hub import try_to_load_from_cache


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", choices=["a"], default="a")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default=None, help="cpu on login nodes (their GPU is shared)")
    a = ap.parse_args()
    items = [json.loads(l) for l in open(a.pool)]
    random.Random(20261119).shuffle(items)
    items = items[: a.n]
    from flotilla.router_a import RouterA
    path = str(__import__("pathlib").Path(try_to_load_from_cache("vllm-sr/vela3-fast", "config.json")).parent)
    r = RouterA(path, device=a.device)
    per = defaultdict(Counter)
    lat = []
    rows = []
    for it in items:
        d = r.route(it["task"])
        per[it["task_type"]][d["task_type"]] += 1
        lat.append(d["latency_s"])
        rows.append({"id": it["id"], "true": it["task_type"], "pred": d["task_type"], "probabilities": d["probabilities"]})
    correct = sum(c[t] for t, c in per.items())
    out = {"router": "A:vela3-fast", "n": len(items), "accuracy": round(correct / len(items), 4),
           "per_type": {t: {"n": sum(c.values()), "correct": c[t], "confused_with": dict(c.most_common(3))} for t, c in per.items()},
           "latency_s_mean": round(sum(lat) / len(lat), 4)}
    print(json.dumps(out, indent=2))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({**out, "rows": rows}, f)


if __name__ == "__main__":
    main()
