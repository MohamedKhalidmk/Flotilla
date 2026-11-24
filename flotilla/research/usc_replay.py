# Sources: usc, longmemeval (docs/reference/REFERENCES.md)
"""F36 replay: apply the USC tie rule to saved Vote samples, without sampling again.

    python -m flotilla.research.usc_replay --traces DIR [DIR ...] --items memory_items.jsonl --ids ID [ID ...] \
        --url URL --model MODEL --out OUT
For each listed item, its trace's sample answers go through system.vote; on a free-text tie (no two answers match) one
system.usc_pick call picks an answer. OUT gets usc/trace.jsonl (the picked answer), s0..s4/trace.jsonl (each sample's
answer, to judge them one by one) and replay.jsonl (pick, reply, tokens, seconds). Grade with memory_route judge.
"""
import argparse
import asyncio
import json
from pathlib import Path

from flotilla.core import system
from flotilla.memory.longmemeval import history_prompt
from flotilla.core.trace import Trace


async def replay(traces: dict, items: dict, ids: list[str], srv: dict, out: Path) -> list[dict]:
    cfg = system.SystemConfig(servers={"q": srv}, solvers=["q"], tie_rule="usc")
    rows = []
    for i in ids:
        t = traces[i]
        answers = [s.get("final_answer") for m in t["models"] if ":" not in m["name"] for s in m["samples"]]
        v = system.vote("memory", answers)
        cands = [a for a in answers if a]
        rec = {"item_id": i, "n": len(cands), "tie": system.is_free_text_tie(v), "old_winner": cands.index(v["winner"])}
        if rec["tie"]:
            tr = Trace(run_id="usc", protocol_version="p", prompt_versions={}, benchmark="lme", item_id=i, split="dev")
            u = await system.usc_pick("q", srv, system.question_only(history_prompt(items[i])), cands, cfg, tr)
            rec.update(pick=u["index"], **{k: u[k] for k in ("parsed", "error", "reply", "tokens_in", "tokens_out", "latency_s")})
        else:
            rec["pick"] = rec["old_winner"]
        rows.append(rec)
        for name, ans in [("usc", cands[rec["pick"]])] + [(f"s{k}", a) for k, a in enumerate(cands)]:
            d = out / name
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "trace.jsonl", "a") as f:
                f.write(json.dumps({"item_id": i, "final_answer": ans}, ensure_ascii=False) + "\n")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", nargs="+", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    want = set(a.ids)
    traces = {}
    for d in a.traces:
        for line in open(Path(d) / "trace.jsonl"):
            t = json.loads(line)
            if t["item_id"] in want:
                traces[t["item_id"]] = t
    items = {}
    for line in open(a.items):
        it = json.loads(line)
        if it["item_id"] in want:
            items[it["item_id"]] = it
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists")
    srv = {"url": a.url, "model": a.model, "quant": "w4a16-ours"}
    rows = asyncio.run(replay(traces, items, a.ids, srv, out))
    (out / "replay.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(json.dumps({"items": len(rows), "ties": sum(r["tie"] for r in rows),
                      "moved_off_sample_0": sum(r["pick"] != r["old_winner"] for r in rows),
                      "unparsed": sum(r["tie"] and not r.get("parsed") for r in rows)}))


if __name__ == "__main__":
    main()
