"""Who gets what right: per group (task type or benchmark), how many questions only one model got right, all
got right, or none did, plus the perfect-router ("oracle") score next to each model alone.

    python -m flotilla.oracle --labels qwen=a.jsonl phi=b.jsonl [--group task_type|bench] [--pool pool.clean.jsonl] [--out x.json]
Each labels file has one JSON line per question with "id" (or "item_id"), the group field, and "correct".
Only questions every model answered are counted; --pool restricts to ids in that file (e.g. the clean pool).
"""
import argparse
import json
from collections import defaultdict
from itertools import combinations


def load(path: str) -> dict[str, dict]:
    out = {}
    for line in open(path):
        r = json.loads(line)
        out[r.get("id") or r["item_id"]] = r
    return out


def table(labels: dict[str, dict[str, dict]], group: str, keep: set[str] | None = None) -> dict:
    models = list(labels)
    ids = set.intersection(*(set(v) for v in labels.values()))
    if keep is not None:
        ids &= keep
    groups: dict[str, list[str]] = defaultdict(list)
    for i in ids:
        groups[labels[models[0]][i].get(group, "?")].append(i)
    groups["ALL"] = list(ids)
    res = {}
    for g, gids in sorted(groups.items(), key=lambda kv: (kv[0] == "ALL", kv[0])):
        n = len(gids)
        ok = {m: {i for i in gids if labels[m][i]["correct"]} for m in models}
        anyok = set().union(*ok.values())
        row = {"n": n, "none": n - len(anyok), "all": len(set.intersection(*ok.values()))}
        for m in models:
            row[f"only_{m}"] = len(ok[m] - set().union(*(ok[o] for o in models if o != m)))
            row[f"{m}_alone"] = round(len(ok[m]) / n, 4) if n else None
        if len(models) > 2:
            for a, b in combinations(models, 2):
                row[f"{a}+{b}_only"] = len((ok[a] & ok[b]) - set().union(*(ok[o] for o in models if o not in (a, b))))
        row["oracle"] = round(len(anyok) / n, 4) if n else None
        best = max(models, key=lambda m: len(ok[m]))
        row["oracle_gain_over_best_single"] = round((len(anyok) - len(ok[best])) / n, 4) if n else None
        res[g] = row
    return {"models": models, "group": group, "groups": res}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="+", required=True, help="model=path")
    ap.add_argument("--group", default="task_type")
    ap.add_argument("--pool", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    labels = {}
    for kv in a.labels:
        m, path = kv.split("=", 1)
        merged = {}
        for p in path.split(","):            # shards: comma-separated
            merged.update(load(p))
        labels[m] = merged
    keep = {json.loads(l)["id"] for l in open(a.pool)} if a.pool else None
    t = table(labels, a.group, keep)
    print(json.dumps(t, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(t, f, indent=1)


if __name__ == "__main__":
    main()
