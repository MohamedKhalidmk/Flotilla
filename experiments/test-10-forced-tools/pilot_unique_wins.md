# Pilot: unique wins and oracle gains (153 non-memory questions)

Computed 2026-11-26. Every answer graded with the same router-label grader (label_loop.grade; instruction answers by
RLVR-IFeval ground truth, code by public tests on Fir). Run-04's six base routes were regraded from their stored answers,
because their stored instruction verdicts used the older regex grader (stored totals 141-150, regraded 113-124).

Right of 153: pilot forced_code 135, deep_tools 134, deep 131, forced_rules 130, self_check 124, tools 124,
forced_sympy 122, fast 116; run-04 vote 124, deep 118, deep_tools 117, fast 116, vote_tools 115, tools 113.

Unique wins (right on this route only):
- among the 8 pilot routes: deep 2 (rlvrif-74, rlvrif-9966); every other route 0.
- among 14 columns (8 pilot routes plus run-04's 6): every forced route 0.

Oracle (best of the routes) and what each forced route adds:

| Existing set | Oracle | + forced_code | + forced_sympy | + forced_rules | + self_check | + all four |
|---|---|---|---|---|---|---|
| pilot's 4 comparators (fast, tools, deep, deep_tools; same day) | 140 | +3 | +1 | +3 | +2 | not computed |
| run-04's 6 base routes | 132 | +11 | +8 | +8 | +8 | not computed |
| both (10 columns) | 141 | +2 | +1 | +2 | +2 | +3 |

The forced routes' gains overlap: the questions they add are shared between them, so none is unique.
