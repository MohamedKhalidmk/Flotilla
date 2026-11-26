# Pilot pool scores (153 non-memory questions per route)

Scored 2026-11-26 from the Fir pilot traces (forced_tools/pilot/<route>/pool) with the router-label grader (flotilla label_loop.grade): math by sympy and format match, MMLU-Pro by letter, LiveCodeBench by public tests (run on Fir), instruction questions by RLVR-IFeval ground truth (run on Fir, it needs langdetect). Memory is the Haiku judge result of 2026-11-24 on 40 LongMemEval dev questions.

| Route | Right of 153 | AIME | GSM8K | MATH | MMLU-Pro | LiveCodeBench | Instructions | Empty answers | Memory of 40 |
|---|---|---|---|---|---|---|---|---|---|
| forced_code | 135 | 17/17 | 23/24 | 22/29 | 32/35 | 12/12 | 29/36 | 1 | 37/40 |
| deep_tools | 134 | 17/17 | 23/24 | 22/29 | 30/35 | 11/12 | 31/36 | 0 | 36/40 |
| deep | 131 | 17/17 | 21/24 | 21/29 | 30/35 | 10/12 | 32/36 | 2 | 36/40 |
| forced_rules | 130 | 17/17 | 23/24 | 20/29 | 34/35 | 11/12 | 25/36 | 0 | 35/40 |
| self_check | 124 | 14/17 | 23/24 | 21/29 | 33/35 | 11/12 | 22/36 | 1 | 28/40 |
| tools | 124 | 16/17 | 23/24 | 19/29 | 31/35 | 11/12 | 24/36 | 0 | 35/40 |
| forced_sympy | 122 | 14/17 | 23/24 | 20/29 | 32/35 | 12/12 | 21/36 | 2 | 34/40 |
| fast | 116 | 16/17 | 23/24 | 20/29 | 30/35 | 10/12 | 17/36 | 2 | 35/40 |
