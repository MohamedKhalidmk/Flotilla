# Tool use on run-04's tool routes (2026-11-22)

Made by `tool_use.py` from the label traces (pool from Trillium, LongMemEval from Fir); every trace's answer is the one the labels graded.


## tools (no-tool twin: fast)
type | n | used tool | calls/q | calls/q when used | sympy | python | constraint | other | errored calls | cc draft failed | right with tool: tool route vs base | fixes/breaks | without tool: tool vs base
code | 79 | 79 (100.0%) | 3.20 | 3.20 | 0 | 249 | 4 | 0 | 127 (50.2%) | 0 | 91.1% vs 83.5% (n=79) | +9/-3 | - vs - (n=0)
instruction | 236 | 218 (92.4%) | 2.29 | 2.48 | 13 | 197 | 327 | 3 | 16 (3.0%) | 30 | 89.0% vs 79.8% (n=218) | +25/-5 | 94.4% vs 94.4% (n=18)
math | 898 | 852 (94.9%) | 1.94 | 2.05 | 395 | 1159 | 190 | 0 | 60 (3.4%) | 0 | 95.2% vs 93.5% (n=852) | +29/-15 | 82.6% vs 87.0% (n=46)
memory | 500 | 47 (9.4%) | 0.12 | 1.28 | 0 | 15 | 44 | 1 | 1 (1.7%) | 17 | 70.2% vs 70.2% (n=47) | +5/-5 | 84.3% vs 81.9% (n=453)
science_mc | 237 | 215 (90.7%) | 1.89 | 2.08 | 68 | 208 | 171 | 0 | 9 (2.0%) | 0 | 89.8% vs 92.1% (n=215) | +7/-12 | 77.3% vs 81.8% (n=22)
ALL | 1950 | 1411 (72.4%) | 1.56 | 2.16 | 476 | 1828 | 736 | 4 | 213 (7.0%) | 47 | 92.3% vs 89.9% (n=1411) | +75/-40 | 84.2% vs 82.7% (n=539)
sign test, fixes against breaks on questions with a tool call: p = 0.0014
errors by tool: {'err:python_exec': 178, 'err:sympy': 31, 'err:final_answer': 4}

## deep_tools (no-tool twin: deep)
type | n | used tool | calls/q | calls/q when used | sympy | python | constraint | other | errored calls | cc draft failed | right with tool: tool route vs base | fixes/breaks | without tool: tool vs base
code | 79 | 79 (100.0%) | 2.99 | 2.99 | 0 | 222 | 14 | 0 | 84 (35.6%) | 0 | 97.5% vs 84.8% (n=79) | +11/-1 | - vs - (n=0)
instruction | 236 | 228 (96.6%) | 2.59 | 2.68 | 19 | 163 | 430 | 0 | 6 (1.0%) | 17 | 91.2% vs 95.2% (n=228) | +8/-17 | 25.0% vs 87.5% (n=8)
math | 898 | 895 (99.7%) | 2.33 | 2.33 | 854 | 1141 | 94 | 0 | 134 (6.4%) | 0 | 96.4% vs 97.2% (n=895) | +8/-15 | 33.3% vs 100.0% (n=3)
memory | 500 | 241 (48.2%) | 0.52 | 1.09 | 0 | 37 | 224 | 1 | 1 (0.4%) | 83 | 92.5% vs 92.5% (n=241) | +8/-8 | 83.8% vs 83.8% (n=259)
science_mc | 237 | 222 (93.7%) | 1.79 | 1.91 | 72 | 226 | 126 | 0 | 20 (4.7%) | 0 | 90.5% vs 91.0% (n=222) | +6/-7 | 100.0% vs 100.0% (n=15)
ALL | 1950 | 1665 (85.4%) | 1.86 | 2.18 | 945 | 1789 | 888 | 1 | 245 (6.8%) | 100 | 94.4% vs 94.8% (n=1665) | +41/-48 | 82.5% vs 84.9% (n=285)
sign test, fixes against breaks on questions with a tool call: p = 0.5250
errors by tool: {'err:python_exec': 143, 'err:sympy': 101, 'err:final_answer': 1}

## vote_tools (no-tool twin: vote)
type | n | used tool | calls/q | calls/q when used | sympy | python | constraint | other | errored calls | cc draft failed | right with tool: tool route vs base | fixes/breaks | without tool: tool vs base
code | 79 | 79 (100.0%) | 13.92 | 13.92 | 0 | 1028 | 72 | 0 | 413 (37.5%) | 0 | 98.7% vs 91.1% (n=79) | +6/-0 | - vs - (n=0)
instruction | 236 | 236 (100.0%) | 11.58 | 11.58 | 83 | 783 | 1865 | 1 | 60 (2.2%) | 85 | 93.2% vs 97.5% (n=236) | +4/-14 | - vs - (n=0)
math | 898 | 898 (100.0%) | 11.60 | 11.60 | 4119 | 5613 | 683 | 0 | 789 (7.6%) | 0 | 97.9% vs 97.9% (n=898) | +4/-4 | - vs - (n=0)
memory | 500 | 440 (88.0%) | 3.12 | 3.55 | 2 | 281 | 1269 | 10 | 10 (0.6%) | 511 | 88.0% vs 91.8% (n=440) | +8/-25 | 76.7% vs 78.3% (n=60)
science_mc | 237 | 237 (100.0%) | 8.56 | 8.56 | 382 | 1091 | 555 | 0 | 93 (4.6%) | 0 | 92.4% vs 93.2% (n=237) | +2/-4 | - vs - (n=0)
ALL | 1950 | 1890 (96.9%) | 9.15 | 9.44 | 4586 | 8796 | 4444 | 11 | 1365 (7.7%) | 596 | 94.3% vs 95.6% (n=1890) | +24/-47 | 76.7% vs 78.3% (n=60)
sign test, fixes against breaks on questions with a tool call: p = 0.0086
errors by tool: {'err:python_exec': 776, 'err:sympy': 578, 'err:final_answer': 11}
