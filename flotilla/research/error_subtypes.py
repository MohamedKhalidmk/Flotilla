# Sources: original, claude-haiku, anthropic-sdk (docs/reference/REFERENCES.md)
"""Sub-types of reasoning_error (PROTOCOL.md 7.1): one Claude Haiku 5.5 call per trace (PAID) with the fixed prompt
prompts/error_subtype.v1.md, which sees the question, the gold, the wrong answer and the facts shown.

    python -m flotilla.research.error_subtypes --stages STAGES.jsonl [...] --runs route=DIR [...] --pool POOL.jsonl \
        --memory-items LME.jsonl --graft-cache DIR --out DIR [--limit N]
Rows of stages.jsonl (`python -m flotilla.core.scoring stages`) with error_stage reasoning_error are classified. A route's
later folders replace earlier ones per item (run-03's fix reruns). Every call is logged with its cost in
OUT/usage.jsonl (memory_route.HaikuJudge); results go to OUT/subtypes.jsonl, resumable (rows already written are
skipped).
"""
import argparse
import asyncio
import json
import re
from pathlib import Path

SUBTYPES = ("partial_answer", "calculation_error", "outdated_fact", "abstention_error", "misread_question", "other")
CUT = 4000   # characters kept of a long question or answer (code answers); the cut is marked


def _cut(text, n=CUT) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= n else text[:n] + f"\n[... {len(text) - n} more characters cut]"


def subtype_prompt(question: str, gold: str, answer: str, facts: str, version: str = "v1") -> str:
    from flotilla.core.system import PROMPTS, _section
    md = (PROMPTS / f"error_subtype.{version}.md").read_text()
    t = _section(md, "User")
    for k, v in (("question", _cut(question)), ("gold", _cut(gold, 2000)), ("answer", _cut(answer)),
                 ("facts", _cut(facts, 12000))):
        t = t.replace("{" + k + "}", v)
    return t


def parse_subtype(text: str) -> dict:
    """The reply's JSON object; an unknown or missing sub-type becomes "unparsed" (never guessed)."""
    m = re.findall(r"\{[^{}]*\"subtype\"[^{}]*\}", text or "", re.S)
    for blob in reversed(m):
        try:
            d = json.loads(blob)
        except ValueError:
            continue
        st = str(d.get("subtype", "")).strip().lower()
        if st in SUBTYPES:
            return {"subtype": st, "reason": str(d.get("reason", ""))[:300]}
    return {"subtype": "unparsed", "reason": (text or "")[:300]}


def gold_text(item: dict) -> str:
    """What the classifier is told the right answer is."""
    if item.get("task_type") == "instruction":
        return f"(an instruction task) the answer must follow this rule: {item.get('constraint') or 'see the task'}"
    if item.get("task_type") == "code":
        return "(a programming task) the program must pass the task's hidden tests"
    return str(item.get("gold") if item.get("gold") is not None else item.get("answer"))


def facts_text(route: str, trace: dict, item: dict, graph: dict | None) -> str:
    from flotilla.memory.memory_route import shown_facts_text
    if (trace.get("retrieval") or {}).get("source") == "graft" and graph:
        return shown_facts_text((trace["retrieval"].get("fact_ids") or []), graph)
    if "sessions" in item:
        return "(this route read the whole chat history; it is not repeated here)"
    return "(no memory: the question is self-contained)"


async def run(a) -> None:
    from flotilla.memory.memory_route import HAIKU, HaikuJudge
    rows = [json.loads(l) for p in a.stages for l in open(p)]
    rows = [r for r in rows if r["error_stage"] == "reasoning_error"]
    if a.limit:
        rows = rows[:a.limit]
    traces: dict[str, dict] = {}
    for kv in a.runs:
        route, d = kv.split("=", 1)
        for line in open(Path(d) / "trace.jsonl"):
            t = json.loads(line)
            traces.setdefault(route, {})[t["item_id"]] = t
    items = {}
    for line in open(a.pool):
        x = json.loads(line)
        items[x.get("id") or x.get("item_id")] = x
    for line in open(a.memory_items):
        x = json.loads(line)
        if any(r["id"] == x["item_id"] for r in rows):
            items[x["item_id"]] = x
    graphs = {}

    def graph(iid, key):
        if (iid, key) not in graphs:
            p = Path(a.graft_cache) / "graphs" / f"{iid}.{key}.json"
            graphs[(iid, key)] = json.load(open(p)) if p.exists() else None
        return graphs[(iid, key)]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    done = set()
    if (out / "subtypes.jsonl").exists():
        done = {(r["id"], r["route"]) for r in map(json.loads, open(out / "subtypes.jsonl"))}
    if a.dry_run:   # free: build every prompt, report sizes (about 4 characters a token), call nothing
        n_chars = 0
        for r in rows:
            t, it = traces[r["route"]][r["id"]], items[r["id"]]
            g = graph(r["id"], t["retrieval"]["graph_key"]) if (t.get("retrieval") or {}).get("source") == "graft" else None
            q = it.get("question") or it.get("task")
            n_chars += len(subtype_prompt(q, gold_text(it), t.get("final_answer"), facts_text(r["route"], t, it, g)))
        tok = n_chars / 4
        print(f"dry run: {len(rows)} prompts, about {tok / 1e6:.2f}M input tokens, Haiku input cost about "
              f"${tok * 0.10 / 1e6:.3f} plus about ${len(rows) * 60 * 0.50 / 1e6:.3f} output")
        return
    judge = HaikuJudge(out / "usage.jsonl", model=HAIKU, max_tokens=200, phase="error_subtype")
    sem = asyncio.Semaphore(8)

    with open(out / "subtypes.jsonl", "a") as f:
        async def one(r):
            t, it = traces[r["route"]][r["id"]], items[r["id"]]
            g = graph(r["id"], t["retrieval"]["graph_key"]) if (t.get("retrieval") or {}).get("source") == "graft" else None
            q = it.get("question") or it.get("task")
            prompt = subtype_prompt(q, gold_text(it), t.get("final_answer"), facts_text(r["route"], t, it, g))
            async with sem:
                reply = await judge(prompt, r["id"], r["route"])
            f.write(json.dumps({"id": r["id"], "route": r["route"], "task_type": r["task_type"],
                                **parse_subtype(reply), "reply": reply[:500]}, ensure_ascii=False) + "\n")
            f.flush()
        await asyncio.gather(*[one(r) for r in rows if (r["id"], r["route"]) not in done])
    print(f"classified {len(rows) - len(done)} traces -> {out / 'subtypes.jsonl'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", nargs="+", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--memory-items", required=True)
    ap.add_argument("--graft-cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="build the prompts and report their size; no calls")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
