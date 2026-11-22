"""Tool use on run-04's tool routes (Tools, Deep+Tools, Vote+Tools), from the label traces.

    python tool_use.py --labels run-04-lme/per_question.jsonl --pool POOL_RUNS --lme LME_RUNS > runs/run-04/tool_use.md
POOL_RUNS is runs/strategy-labels (Trillium holds every pool folder: strat*, and fix* whose answers replaced the first
ones in run-03); LME_RUNS is lme/runs (Fir). Each route is compared with its no-tool twin (Fast, Deep, Vote) on the same
questions. An errored call: python_exec or sympy returned ok false (non-zero exit, timeout, exception or unparseable
input), or a tool name that does not exist. constraint_check returning ok false means the draft failed a constraint,
which is counted apart ("draft failed"), not as an error. Vote+Tools counts the calls of all five samples.
"""
import argparse
import json, glob, collections, sys
from math import comb
ap = argparse.ArgumentParser(); ap.add_argument('--labels', required=True); ap.add_argument('--pool', required=True); ap.add_argument('--lme', required=True)
A = ap.parse_args()
rows = {}
for l in open(A.labels):
    r = json.loads(l); rows[r['id']] = r
PAIRS = {'tools': 'fast', 'deep_tools': 'deep', 'vote_tools': 'vote'}
traces = {}
for route in PAIRS:
    t = {}
    for pref in ('strat', 'fix'):   # fix reruns replace the first answers (run-03)
        for f in sorted(glob.glob(f'{A.pool}/{route}/{pref}*/trace.jsonl')):
            for l in open(f):
                x = json.loads(l); t[x['item_id']] = x
    for f in sorted(glob.glob(f'{A.lme}/{route}/lme_*/trace.jsonl')):
        for l in open(f):
            x = json.loads(l); t[x['item_id']] = x
    traces[route] = t
# check the chosen trace is the one the labels graded
for route, t in traces.items():
    used = [i for i, r in rows.items() if r.get(route, {}).get('available')]
    miss = [i for i in used if i not in t]
    norm = lambda a: ('' if a is None else str(a)).strip().removeprefix('```python').strip('`').strip()
    diff = [i for i in used if i in t and not norm(t[i].get('final_answer')).startswith(norm(rows[i][route].get('answer')))]
    print(f"# {route}: {len(used)} labelled, {len(miss)} without trace, {len(diff)} answer differs", file=sys.stderr)
    if diff: print('  e.g.', diff[:3], repr(str(traces[route][diff[0]].get('final_answer'))[:80]), repr(str(rows[diff[0]][route].get('answer'))[:80]), file=sys.stderr)
def err(x):
    if x['name'] not in ('sympy', 'python_exec', 'constraint_check'): return 'unknown tool'
    if x['name'] == 'constraint_check': return None if x['output'] not in ('None', None) else 'error'
    return None if x['ok'] else 'error'
out = {}
for route, base in PAIRS.items():
    stats = collections.defaultdict(lambda: collections.Counter())
    for i, r in rows.items():
        if not r.get(route, {}).get('available') or i not in traces[route]: continue
        tt = r['task_type']
        for key in (tt, 'ALL'):
            s = stats[key]; tl = traces[route][i].get('tools') or []
            s['n'] += 1; s['used'] += bool(tl); s['calls'] += len(tl)
            for x in tl:
                s['call:' + (x['name'] if x['name'] in ('sympy','python_exec','constraint_check') else 'other')] += 1
                e = err(x)
                if e: s['err'] += 1; s['err:' + x['name']] += 1
                if x['name'] == 'constraint_check' and not e and not x['ok']: s['cc_failed_draft'] += 1
            s['q_with_err'] += any(err(x) for x in tl)
            g = 'with' if tl else 'without'
            s[g + '_n'] += 1; s[g + '_tool_right'] += bool(r[route]['correct']); s[g + '_base_right'] += bool(r[base]['correct'])
            if tl:
                s['fix'] += (r[route]['correct'] and not r[base]['correct']); s['break'] += (r[base]['correct'] and not r[route]['correct'])
    out[route] = {k: dict(v) for k, v in stats.items()}
for route, st in out.items():
    print(f"\n## {route} (no-tool twin: {PAIRS[route]})")
    print("type | n | used tool | calls/q | calls/q when used | sympy | python | constraint | other | errored calls | cc draft failed | right with tool: tool route vs base | fixes/breaks | without tool: tool vs base")
    for k, s in sorted(st.items(), key=lambda kv: (kv[0] == 'ALL', kv[0])):
        n = s['n']; u = s.get('used', 0); c = s.get('calls', 0); wn = s.get('with_n', 0); on = s.get('without_n', 0)
        pc = lambda a, b: f"{100*a/b:.1f}%" if b else '-'
        print(f"{k} | {n} | {u} ({pc(u,n)}) | {c/n:.2f} | {c/u if u else 0:.2f} | {s.get('call:sympy',0)} | {s.get('call:python_exec',0)} | {s.get('call:constraint_check',0)} | {s.get('call:other',0)} | {s.get('err',0)} ({pc(s.get('err',0),c)}) | {s.get('cc_failed_draft',0)} | "
              f"{pc(s.get('with_tool_right',0),wn)} vs {pc(s.get('with_base_right',0),wn)} (n={wn}) | +{s.get('fix',0)}/-{s.get('break',0)} | {pc(s.get('without_tool_right',0),on)} vs {pc(s.get('without_base_right',0),on)} (n={on})")
    a, b = st['ALL'].get('fix', 0), st['ALL'].get('break', 0)
    print(f"sign test, fixes against breaks on questions with a tool call: p = {min(1, 2 * sum(comb(a + b, i) for i in range(min(a, b) + 1)) / 2 ** (a + b)):.4f}")
    print('errors by tool:', {k: v for k, v in st['ALL'].items() if k.startswith('err:')})
