"""test-04 table: one row per route the captain (Qwen) can choose, from the newest graded run under runs/
(graded*/summary.json and per_question.jsonl, written by flotilla/strategy_labels.py). Routes with no graded run
yet stay as planned rows with empty cells; nothing is typed by hand."""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import jsonl, write_table

ROUTES = [("fast", "Fast", "thinking off, no tools, 1 sample"),
          ("tools", "Tools", "thinking off, native sympy / Python / constraint tools"),
          ("deep", "Deep", "full thinking, no tools"),
          ("deep_tools", "Deep+Tools", "full thinking with the tools"),
          ("vote", "Vote", "full thinking, 5 samples, majority (tests on code)"),
          ("vote_tools", "Vote+Tools", "Vote with the tools in every sample"),
          ("memory", "Memory", "GRAFT retrieval on the full T-REx base, all on Qwen"),
          ("memory_deep", "Memory+Deep", "GRAFT facts, then Deep"),
          ("vote_memory", "Vote+Memory", "GRAFT facts, then Vote"),
          ("deep_tools_memory", "Deep+Tools+Memory", "GRAFT facts, then Deep+Tools")]

graded = sorted(HERE.glob("runs/run-03/graded/summary.json"))  # full labels, fixed graders
summ = json.loads(graded[-1].read_text()) if graded else {"per_strategy": {}, "labels": {}}
run = graded[-1].parent.parent.name if graded else ""
per_q = jsonl(graded[-1].parent / "per_question.jsonl") if graded else []
n = summ.get("questions")
rows = []
for key, name, what in ROUTES:
    s = summ["per_strategy"].get(key)
    rows.append({"route": name, "what_it_does": what, "questions": n if s else None,
                 "accuracy": s["accuracy"] if s else None,
                 "output_tokens_per_question": round(s["mean_output_tokens"]) if s else None,
                 "gpu_seconds_per_question": round(s["gpu_seconds_job"] / n, 1) if s else None,
                 "cheapest_correct": summ["labels"].get(key, 0) if s else None,
                 "run": f"{run}/{graded[-1].parent.name}" if s else "", "status": "labels" if s else "planned"})
if graded:
    rows.append({"route": "Some route right (oracle)", "what_it_does": "best route per question, known only after trying all",
                 "questions": n, "accuracy": summ.get("best_any_strategy"), "output_tokens_per_question": None,
                 "gpu_seconds_per_question": None, "cheapest_correct": None, "run": f"{run}/{graded[-1].parent.name}",
                 "status": "labels"})
note = (f"Full labels: {n} pool questions, every route on every question, graded against gold (flotilla/strategy_labels.py). "
        f"Cheapest correct = the label a router learns. No route right: {summ['labels'].get('none', 0)}; "
        f"some route right: {summ.get('best_any_strategy')}. GPU-seconds = whole job / questions (server load included)."
        if graded else "Not run yet.")
write_table(HERE, "table", rows, note)
print(len(rows), "rows,", sum(r["status"] == "labels" for r in rows), "from", run)
