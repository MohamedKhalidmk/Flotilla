"""One results table, one row per question, from Flotilla run folders (trace.jsonl + scores.jsonl).

    python -m flotilla.research.results_table --runs RUN_DIR [RUN_DIR ...] --out results/table.csv [--jsonl results/table.jsonl]
Columns cover every decision the system makes, so routing, memory, tools and voting can be judged from real data:
router pick, GRAFT use and whether its facts held the answer, tool calls, verifier verdict and retry, each vote,
final answer, correctness, tokens, calls and time. The JSONL copy keeps the nested fields (votes, tools) in full.
"""
import argparse
import csv
import json
from pathlib import Path


def _answer_in(gold, text: str) -> bool | None:
    if gold is None or not text:
        return None
    golds = gold if isinstance(gold, list) else [gold]
    t = text.lower()
    return any(str(g).lower() in t for g in golds if str(g).strip())


def rows_for(run: Path) -> list[dict]:
    scores = {}
    sp = run / "scores.jsonl"
    if sp.exists():
        for line in open(sp):
            s = json.loads(line)
            scores[s["item_id"]] = s
    out = []
    for line in open(run / "trace.jsonl"):
        t = json.loads(line)
        sc = scores.get(t["item_id"], {})
        samples = [{"model": m["name"], "answer": s.get("final_answer"), "confidence": s.get("confidence"),
                    "tokens_out": s.get("tokens_out"), "error": s["text"][:200] if s["text"].startswith("ERROR") else None}
                   for m in t["models"] for s in m["samples"]]
        ver = t.get("verifier") or {}
        attempts = ver.get("attempts", [])
        retr = t.get("retrieval") or {}
        facts_text = "\n".join(retr.get("facts", [])) if isinstance(retr.get("facts"), list) else str(retr.get("facts") or "")
        tools = t.get("tools", [])
        out.append({
            "run": run.name, "bench": t["benchmark"], "item_id": t["item_id"], "split": t.get("split"),
            "protocol": t.get("protocol_version"),
            "router": (t.get("router") or {}).get("router"), "task_type": (t.get("router") or {}).get("task_type"),
            "routed_models": "|".join((t.get("router") or {}).get("models", [])),
            "routed_tools": "|".join((t.get("router") or {}).get("tools", [])),
            "graft_used": bool(retr), "graft_facts": len(retr.get("facts", [])) if isinstance(retr.get("facts"), list) else None,
            "graft_answer_in_facts": _answer_in(t.get("gold"), facts_text) if retr else None,
            "tool_calls": len(tools), "tool_names": "|".join(x.get("name", "") for x in tools),
            "tool_ok": sum(bool(x.get("ok")) for x in tools),
            "verifier_verdict": ver.get("verdict"), "retried": len(attempts) > 1,
            "retry_changed_answer": (len(attempts) > 1 and attempts[0].get("final_answer") != attempts[-1].get("final_answer")),
            "n_samples": len(samples), "votes": samples,
            "vote_winner": (t.get("vote") or {}).get("winner"), "vote_rule": (t.get("vote") or {}).get("rule"), "vote_counts": (t.get("vote") or {}).get("counts"),
            "final_answer": t.get("final_answer"), "correct": sc.get("correct"), "score": sc.get("score"),
            "tokens_total": t.get("tokens_total"), "tokens_out": sum(s["tokens_out"] or 0 for s in samples),
            "calls": t.get("calls"), "wall_seconds": t.get("wall_seconds"), "error_stage": t.get("error_stage"),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jsonl", default=None)
    a = ap.parse_args()
    rows = [r for run in a.runs if (Path(run) / "trace.jsonl").exists() for r in rows_for(Path(run))]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    if a.jsonl:
        with open(a.jsonl, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} rows from {len(a.runs)} runs -> {a.out}")


if __name__ == "__main__":
    main()
