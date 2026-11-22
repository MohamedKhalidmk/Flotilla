"""Sum cost_usd in usage logs since a start time (cost guards of the paid CPU jobs).

    python scripts/sum_cost.py START_EPOCH USAGE.jsonl [USAGE.jsonl ...]
Missing files count as zero; unreadable lines are skipped. Prints the total with four decimals.
"""
import json
import os
import sys


def total(start: float, paths: list[str]) -> float:
    s = 0.0
    for p in paths:
        if not os.path.exists(p):
            continue
        for line in open(p):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ts", 0) >= start:
                s += r.get("cost_usd", 0.0)
    return s


if __name__ == "__main__":
    print(f"{total(float(sys.argv[1]), sys.argv[2:]):.4f}")
