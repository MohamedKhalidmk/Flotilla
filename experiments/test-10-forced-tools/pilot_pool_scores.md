# Pilot pool scores (153 non-memory questions per route)

Corrected 2026-11-26. The first version of this file (commit c260f9a) graded math with a checker that could not import sympy and math_verify on the login node, so every math answer counted as wrong; these numbers are regraded on Fir with the job environment (scripts/trillium/modules.sh), the router-label grader (label_loop.grade): math by sympy and format match, MMLU-Pro by letter, LiveCodeBench by public tests, instruction questions by RLVR-IFeval ground truth. Memory is the Haiku judge result of 2026-11-24 on 40 LongMemEval dev questions.

| Route | Right of 153 | AIME | GSM8K | MATH | MMLU-Pro | LiveCodeBench | Instructions | Memory of 40 |
|---|---|---|---|---|---|---|---|---|
| forced_code | 142 | 17/17 | 23/24 | 29/29 | 32/35 | 12/12 | 29/36 | 37/40 |
| deep_tools | 141 | 17/17 | 23/24 | 29/29 | 30/35 | 11/12 | 31/36 | 36/40 |
| deep | 141 | 17/17 | 23/24 | 29/29 | 30/35 | 10/12 | 32/36 | 36/40 |
| forced_rules | 138 | 17/17 | 23/24 | 28/29 | 34/35 | 11/12 | 25/36 | 35/40 |
| self_check | 132 | 14/17 | 23/24 | 29/29 | 33/35 | 11/12 | 22/36 | 28/40 |
| tools | 131 | 16/17 | 23/24 | 26/29 | 31/35 | 11/12 | 24/36 | 35/40 |
| forced_sympy | 129 | 14/17 | 23/24 | 27/29 | 32/35 | 12/12 | 21/36 | 34/40 |
| fast | 124 | 16/17 | 23/24 | 28/29 | 30/35 | 10/12 | 17/36 | 35/40 |
