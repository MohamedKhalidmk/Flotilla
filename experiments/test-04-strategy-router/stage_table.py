"""Error-stage counts per route and task type for run-04-lme-maj3 (PROTOCOL.md 7.1).

    python stage_table.py STAGES.jsonl [STAGES.jsonl ...] > runs/run-04/maj3/error_stages.md
Input: rows from `python -m flotilla.scoring stages` (pool part and LongMemEval part). Labels are not changed.
"""
import json
import sys
from collections import Counter, defaultdict

from flotilla.scoring import LIVE_STAGES, STAGE_RULES

ROUTES = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools", "memory", "memory_deep", "deep_tools_memory",
          "vote_memory"]
rows = [json.loads(l) for p in sys.argv[1:] for l in open(p)]
stages = [s for s in STAGE_RULES if s != "none"]
print("# Error stages on run-04-lme-maj3 (one stage per wrong answer, PROTOCOL.md 7.1)\n")
print(f"{len(rows)} route answers tagged. Live stages (taggable without gold): {', '.join(LIVE_STAGES)}.\n")
print("## Per route (all task types)\n")
print("| route | answers | wrong | " + " | ".join(stages) + " |")
print("|---|---|---|" + "---|" * len(stages))
by = defaultdict(Counter)
for r in rows:
    by[r["route"]][r["error_stage"]] += 1
for rt in ROUTES:
    c = by.get(rt)
    if not c:
        continue
    n = sum(c.values())
    print(f"| {rt} | {n} | {n - c['none']} | " + " | ".join(str(c[s]) if c[s] else "" for s in stages) + " |")
types = sorted({r["task_type"] for r in rows})
for tt in types:
    print(f"\n## {tt}\n")
    print("| route | answers | wrong | " + " | ".join(stages) + " |")
    print("|---|---|---|" + "---|" * len(stages))
    for rt in ROUTES:
        c = Counter(r["error_stage"] for r in rows if r["route"] == rt and r["task_type"] == tt)
        if not c:
            continue
        n = sum(c.values())
        print(f"| {rt} | {n} | {n - c['none']} | " + " | ".join(str(c[s]) if c[s] else "" for s in stages) + " |")
flags = Counter(f for r in rows if r["error_stage"] != "none" for f in r.get("error_flags") or [])
print("\n## Flags on wrong answers\n")
print(", ".join(f"{k} {v}" for k, v in flags.most_common()))
ev = Counter((r["route"], r.get("evidence_shown")) for r in rows if r["route"] in ROUTES[6:])
print("\n## Memory routes: gold evidence among the facts shown (all answers)\n")
for rt in ROUTES[6:]:
    print(f"- {rt}: shown {ev[(rt, True)]}, not shown {ev[(rt, False)]}, no answer session {ev[(rt, None)]}")
