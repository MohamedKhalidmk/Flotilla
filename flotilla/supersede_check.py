"""Does the newer fact win in a chat history's GRAFT graph? Three steps, checked from a memory_route prepare cache.

    python -m flotilla.supersede_check --items tests/data/supersede_toy.jsonl --cache CACHE [--cache CACHE2 ...]
    python -m flotilla.supersede_check --items dev_0.jsonl --cache CACHE --check lme-72e3ee87=10,50,episode

Each checked item names an old value, a new value and optionally an anchor word (toy items carry them as
"supersede_check": {"old", "new", "anchor"}; --check gives them for real items). A fact "mentions" a value when the
value appears as a whole word (a number may carry an ordinal ending: 50th) in its subject, relation, object or source span, and the anchor (if any) appears too.

  1. extract   the graph holds a fact mentioning the old value and one mentioning the new value
  2. link      a SUPERSEDES edge (directly or through a chain) runs from a new-value fact to an old-value fact
  3. retrieve  among the facts retrieved for the question, the first that mentions either value mentions the new one
               and is not marked outdated

A later step is reported even when an earlier one fails, so the report shows every step that breaks.
"""
import argparse
import json
import re
from pathlib import Path


def mentions(fact: dict, value: str, anchor: str | None) -> bool:
    prov = fact.get("provenance") or {}
    text = " ".join(str(x) for x in (fact.get("subject"), fact.get("relation"), fact.get("object"),
                                     fact.get("span") or prov.get("span")))
    if not re.search(rf"(?<![\w.]){re.escape(value)}(?:st|nd|rd|th)?(?!\w)", text, re.I):
        return False
    return anchor is None or anchor.lower() in text.lower()


def newer_reaches(graph: dict, start: str, targets: set[str]) -> bool:
    out = {}
    for e in graph["edges"]:
        if e["type"] == "SUPERSEDES":
            out.setdefault(e["source"], []).append(e["target"])
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        for m in out.get(n, []):
            if m in targets:
                return True
            if m not in seen:
                seen.add(m)
                todo.append(m)
    return False


def check(graph: dict, retrieved: list[dict], old: str, new: str, anchor: str | None) -> dict:
    facts = [n for n in graph["nodes"] if n["type"] == "Fact"]
    olds = {f["id"] for f in facts if mentions(f, old, anchor) and not mentions(f, new, anchor)}
    news = {f["id"] for f in facts if mentions(f, new, anchor) and not mentions(f, old, anchor)}
    linked = [n for n in news if newer_reaches(graph, n, olds)]
    first = next(((i, f) for i, f in enumerate(retrieved) if mentions(f, old, anchor) or mentions(f, new, anchor)), None)
    ret_ok = bool(first) and mentions(first[1], new, anchor) and not mentions(first[1], old, anchor) and not first[1].get("outdated")
    show = lambda ids: [f"{f['id']}: {f['subject']} | {f['relation']} | {f['object']}" for f in facts if f["id"] in ids]
    return {"extract": bool(olds) and bool(news), "link": bool(linked), "retrieve": ret_ok,
            "old_facts": show(olds), "new_facts": show(news), "supersedes": linked,
            "retrieved_first": None if not first else {"rank": first[0] + 1, "fact": f"{first[1]['subject']} | "
                               f"{first[1]['relation']} | {first[1]['object']}", "outdated": first[1].get("outdated")},
            "retrieved_mentions": [{"rank": i + 1, "value": new if mentions(f, new, anchor) else old,
                                    "outdated": f.get("outdated")} for i, f in enumerate(retrieved)
                                   if mentions(f, old, anchor) or mentions(f, new, anchor)]}


def cache_files(cache: Path, item_id: str) -> tuple[Path | None, Path | None]:
    g = [p for p in (cache / "graphs").glob(f"{item_id}.*.json") if not p.name.endswith(".build.json")]
    r = list((cache / "retrieval").glob(f"{item_id}.*.json"))
    return (g[0] if g else None), (r[0] if r else None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--cache", action="append", required=True, help="a memory_route prepare cache (repeatable)")
    ap.add_argument("--check", nargs="*", default=[], help="ITEM_ID=OLD,NEW[,ANCHOR] for items without supersede_check")
    ap.add_argument("--out", help="write the full report as JSON")
    a = ap.parse_args()
    extra = {}
    for kv in a.check:
        iid, vals = kv.split("=", 1)
        v = vals.split(",")
        extra[iid] = {"old": v[0], "new": v[1], "anchor": v[2] if len(v) > 2 else None}
    report = []
    for line in open(a.items):
        it = json.loads(line)
        spec = it.get("supersede_check") or extra.get(it["item_id"])
        if not spec:
            continue
        for cache in map(Path, a.cache):
            g, r = cache_files(cache, it["item_id"])
            if g is None or r is None:
                report.append({"item_id": it["item_id"], "cache": str(cache), "missing": True})
                print(f"{it['item_id']} [{cache.name}]: no graph or retrieval in the cache yet")
                continue
            res = check(json.loads(g.read_text()), json.loads(r.read_text())["retrieval"]["facts"],
                        spec["old"], spec["new"], spec.get("anchor"))
            report.append({"item_id": it["item_id"], "cache": str(cache), **spec, **res})
            steps = " ".join(f"{s}={'pass' if res[s] else 'FAIL'}" for s in ("extract", "link", "retrieve"))
            print(f"{it['item_id']} [{cache.name}] {spec['old']} -> {spec['new']}: {steps}")
            for k in ("old_facts", "new_facts"):
                for f in res[k][:4]:
                    print(f"    {k[:3]}: {f}")
            print(f"    retrieved: {res['retrieved_mentions'][:6]}")
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
