# Pilot: unique wins and oracle gains (153 non-memory questions)

Corrected 2026-11-26. The first version (commit 00e69f0) used a math checker that could not import sympy and
math_verify, so math answers all counted as wrong and run-04's code answers (stored cut at 500 characters) were
regraded from the cut text. Here every answer is graded on Fir in the job environment with label_loop.grade (the pilot
grader); run-04's six base routes are regraded from their stored answers except code, where run-04's own public-test
verdict is kept (same tests, the stored text is cut).

Right of 153:
- pilot (same day): forced_code 142, deep 141, deep_tools 141, forced_rules 138, self_check 132, tools 131,
  forced_sympy 129, fast 124.
- run-04 base routes, pilot grader (old regex grader in brackets): vote 142 (150), deep 133 (144), fast 130 (141),
  deep_tools 130 (143), vote_tools 129 (145), tools 126 (143). The whole difference is the 36 instruction questions.

Unique wins (right on this route only):
- among the 8 pilot routes: deep 2; every other route 0.
- among the 14 columns (8 pilot routes plus run-04's 6): every route 0.

Oracle (best of the routes) and what each forced route adds:

| Existing set | Oracle | + forced_code | + forced_sympy | + forced_rules | + self_check | + all four |
|---|---|---|---|---|---|---|
| pilot's 4 comparators (fast, tools, deep, deep_tools; same day) | 147 | +3 | +1 | +3 | +2 | +4 |
| run-04's 6 base routes | 145 | +5 | +2 | +3 | +3 | +6 |
| both (10 columns) | 148 | +2 | +1 | +2 | +2 | +3 |

The run-04 oracle under the old grader was 151.
