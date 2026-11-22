"""Per tool, route and task type: questions where Qwen used the tool against the no-tool twin (run-04 labels).

    python tool_by_tool.py --labels per_question.jsonl --pool POOL_RUNS --lme LME_RUNS > runs/run-04/tool_by_tool.md
Same trace choice as tool_use.py. "used" = at least one call to the tool in the question's trace (any sample);
"only" = used it and no other tool. Fixed = tool route right, twin wrong; broken = the reverse. p = two-sided sign test
on fixed against broken. Verdict per tool and route: helps / hurts when p < 0.05, else neutral.
"""
import argparse
import glob
import json
from collections import defaultdict
from math import comb

PAIRS = {"tools": "fast", "deep_tools": "deep", "vote_tools": "vote"}
TOOLS = ("sympy", "python_exec", "constraint_check")


def sign_p(a: int, b: int) -> float:
    n = a + b
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(a, b) + 1)) / 2 ** n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--lme", required=True)
    a = ap.parse_args()
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.labels)}
    print("# Per tool: questions where Qwen used it, against the no-tool twin (run-04)\n")
    print("Fixed / broken = tool route right and twin wrong / the reverse; p = sign test; verdict at p < 0.05.\n")
    summary = []
    for route, base in PAIRS.items():
        t = {}
        for pref in ("strat", "fix"):
            for f in sorted(glob.glob(f"{a.pool}/{route}/{pref}*/trace.jsonl")):
                for line in open(f):
                    x = json.loads(line)
                    t[x["item_id"]] = x
        for f in sorted(glob.glob(f"{a.lme}/{route}/lme_*/trace.jsonl")):
            for line in open(f):
                x = json.loads(line)
                t[x["item_id"]] = x
        S = defaultdict(lambda: [0, 0, 0, 0, 0])  # n, tool right, twin right, fixed, broken
        for i, r in rows.items():
            if not r.get(route, {}).get("available"):
                continue
            used = {c["name"] for c in t[i]["tools"]}
            ok, ok0 = bool(r[route]["correct"]), bool(r[base]["correct"])
            for tool in TOOLS:
                if tool not in used:
                    continue
                for kind in ("used", "only") if used == {tool} else ("used",):
                    for tt in (r["task_type"], "ALL"):
                        s = S[(tool, kind, tt)]
                        s[0] += 1; s[1] += ok; s[2] += ok0; s[3] += ok and not ok0; s[4] += ok0 and not ok
        print(f"\n## {route} (twin: {base})\n")
        print("| tool | questions | task type | n | tool route right | twin right | fixed | broken | p |")
        print("|---|---|---|---|---|---|---|---|---|")
        for tool in TOOLS:
            for kind in ("used", "only"):
                keys = sorted((k for k in S if k[0] == tool and k[1] == kind), key=lambda k: (k[2] == "ALL", k[2]))
                for k in keys:
                    n, a1, a0, fx, br = S[k]
                    p = sign_p(fx, br)
                    print(f"| {tool} | {kind} | {k[2]} | {n} | {a1/n:.1%} | {a0/n:.1%} | {fx} | {br} | {p:.3f} |")
                    if k[2] == "ALL":
                        verdict = "neutral" if p >= 0.05 else ("helps" if fx > br else "hurts")
                        summary.append((tool, route, kind, n, fx, br, p, verdict))
    print("\n## Summary (all task types)\n")
    print("| tool | route | questions | n | fixed | broken | p | verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for tool, route, kind, n, fx, br, p, v in sorted(summary):
        print(f"| {tool} | {route} | {kind} | {n} | {fx} | {br} | {p:.3f} | {v} |")


if __name__ == "__main__":
    main()
