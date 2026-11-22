# Per tool: questions where Qwen used it, against the no-tool twin (run-04)

Fixed / broken = tool route right and twin wrong / the reverse; p = sign test; verdict at p < 0.05.


## tools (twin: fast)

| tool | questions | task type | n | tool route right | twin right | fixed | broken | p |
|---|---|---|---|---|---|---|---|---|
| sympy | used | instruction | 11 | 72.7% | 63.6% | 1 | 0 | 1.000 |
| sympy | used | math | 366 | 96.2% | 94.0% | 12 | 4 | 0.077 |
| sympy | used | science_mc | 66 | 92.4% | 95.5% | 0 | 2 | 0.500 |
| sympy | used | ALL | 443 | 95.0% | 93.5% | 13 | 6 | 0.167 |
| sympy | only | science_mc | 4 | 75.0% | 100.0% | 0 | 1 | 1.000 |
| sympy | only | ALL | 4 | 75.0% | 100.0% | 0 | 1 | 1.000 |
| python_exec | used | code | 79 | 91.1% | 83.5% | 9 | 3 | 0.146 |
| python_exec | used | instruction | 101 | 83.2% | 77.2% | 10 | 4 | 0.180 |
| python_exec | used | math | 842 | 95.1% | 93.5% | 29 | 15 | 0.049 |
| python_exec | used | memory | 15 | 73.3% | 80.0% | 0 | 1 | 1.000 |
| python_exec | used | science_mc | 164 | 89.0% | 91.5% | 4 | 8 | 0.388 |
| python_exec | used | ALL | 1201 | 92.8% | 91.0% | 52 | 31 | 0.028 |
| python_exec | only | code | 75 | 90.7% | 82.7% | 9 | 3 | 0.146 |
| python_exec | only | instruction | 21 | 81.0% | 90.5% | 2 | 4 | 0.688 |
| python_exec | only | math | 371 | 94.1% | 92.7% | 13 | 8 | 0.383 |
| python_exec | only | memory | 11 | 72.7% | 81.8% | 0 | 1 | 1.000 |
| python_exec | only | science_mc | 31 | 74.2% | 87.1% | 0 | 4 | 0.125 |
| python_exec | only | ALL | 509 | 91.4% | 90.6% | 24 | 20 | 0.652 |
| constraint_check | used | code | 4 | 100.0% | 100.0% | 0 | 0 | 1.000 |
| constraint_check | used | instruction | 197 | 89.8% | 78.7% | 23 | 1 | 0.000 |
| constraint_check | used | math | 189 | 95.2% | 95.2% | 6 | 6 | 1.000 |
| constraint_check | used | memory | 35 | 71.4% | 65.7% | 5 | 3 | 0.727 |
| constraint_check | used | science_mc | 165 | 92.1% | 92.1% | 7 | 7 | 1.000 |
| constraint_check | used | ALL | 590 | 91.2% | 87.1% | 41 | 17 | 0.002 |
| constraint_check | only | instruction | 111 | 93.7% | 81.1% | 15 | 1 | 0.001 |
| constraint_check | only | math | 10 | 100.0% | 100.0% | 0 | 0 | 1.000 |
| constraint_check | only | memory | 31 | 71.0% | 64.5% | 5 | 3 | 0.727 |
| constraint_check | only | science_mc | 32 | 93.8% | 90.6% | 3 | 2 | 1.000 |
| constraint_check | only | ALL | 184 | 90.2% | 81.0% | 23 | 6 | 0.002 |

## deep_tools (twin: deep)

| tool | questions | task type | n | tool route right | twin right | fixed | broken | p |
|---|---|---|---|---|---|---|---|---|
| sympy | used | instruction | 14 | 78.6% | 92.9% | 0 | 2 | 0.500 |
| sympy | used | math | 614 | 96.7% | 97.4% | 4 | 8 | 0.388 |
| sympy | used | science_mc | 66 | 97.0% | 97.0% | 0 | 0 | 1.000 |
| sympy | used | ALL | 694 | 96.4% | 97.3% | 4 | 10 | 0.180 |
| sympy | only | math | 27 | 92.6% | 96.3% | 1 | 2 | 1.000 |
| sympy | only | science_mc | 6 | 100.0% | 100.0% | 0 | 0 | 1.000 |
| sympy | only | ALL | 33 | 93.9% | 97.0% | 1 | 2 | 1.000 |
| python_exec | used | code | 79 | 97.5% | 84.8% | 11 | 1 | 0.006 |
| python_exec | used | instruction | 108 | 89.8% | 91.7% | 7 | 9 | 0.804 |
| python_exec | used | math | 865 | 96.5% | 97.2% | 7 | 13 | 0.263 |
| python_exec | used | memory | 36 | 88.9% | 88.9% | 0 | 0 | 1.000 |
| python_exec | used | science_mc | 182 | 90.1% | 90.7% | 5 | 6 | 1.000 |
| python_exec | used | ALL | 1270 | 94.9% | 94.8% | 30 | 29 | 1.000 |
| python_exec | only | code | 65 | 96.9% | 83.1% | 10 | 1 | 0.012 |
| python_exec | only | instruction | 8 | 75.0% | 87.5% | 1 | 2 | 1.000 |
| python_exec | only | math | 245 | 95.9% | 96.7% | 3 | 5 | 0.727 |
| python_exec | only | memory | 28 | 92.9% | 92.9% | 0 | 0 | 1.000 |
| python_exec | only | science_mc | 73 | 84.9% | 84.9% | 3 | 3 | 1.000 |
| python_exec | only | ALL | 419 | 93.6% | 92.1% | 17 | 11 | 0.345 |
| constraint_check | used | code | 14 | 100.0% | 92.9% | 1 | 0 | 1.000 |
| constraint_check | used | instruction | 218 | 91.7% | 95.4% | 7 | 15 | 0.134 |
| constraint_check | used | math | 93 | 95.7% | 96.8% | 1 | 2 | 1.000 |
| constraint_check | used | memory | 212 | 92.0% | 92.9% | 7 | 9 | 0.804 |
| constraint_check | used | science_mc | 110 | 91.8% | 92.7% | 3 | 4 | 1.000 |
| constraint_check | used | ALL | 647 | 92.6% | 94.3% | 19 | 30 | 0.152 |
| constraint_check | only | instruction | 119 | 92.4% | 98.3% | 1 | 8 | 0.039 |
| constraint_check | only | memory | 204 | 92.6% | 93.6% | 7 | 9 | 0.804 |
| constraint_check | only | science_mc | 30 | 93.3% | 93.3% | 1 | 1 | 1.000 |
| constraint_check | only | ALL | 353 | 92.6% | 95.2% | 9 | 18 | 0.122 |

## vote_tools (twin: vote)

| tool | questions | task type | n | tool route right | twin right | fixed | broken | p |
|---|---|---|---|---|---|---|---|---|
| sympy | used | instruction | 35 | 91.4% | 97.1% | 0 | 2 | 0.500 |
| sympy | used | math | 807 | 97.8% | 97.8% | 3 | 3 | 1.000 |
| sympy | used | memory | 2 | 50.0% | 50.0% | 0 | 0 | 1.000 |
| sympy | used | science_mc | 126 | 92.1% | 93.7% | 1 | 3 | 0.625 |
| sympy | used | ALL | 970 | 96.7% | 97.1% | 4 | 8 | 0.388 |
| python_exec | used | code | 79 | 98.7% | 91.1% | 6 | 0 | 0.031 |
| python_exec | used | instruction | 169 | 92.9% | 98.2% | 1 | 10 | 0.012 |
| python_exec | used | math | 897 | 97.9% | 97.9% | 4 | 4 | 1.000 |
| python_exec | used | memory | 109 | 89.0% | 90.8% | 2 | 4 | 0.688 |
| python_exec | used | science_mc | 207 | 92.3% | 92.8% | 2 | 3 | 1.000 |
| python_exec | used | ALL | 1461 | 95.9% | 96.3% | 15 | 21 | 0.405 |
| python_exec | only | code | 39 | 100.0% | 89.7% | 4 | 0 | 0.125 |
| python_exec | only | instruction | 5 | 100.0% | 100.0% | 0 | 0 | 1.000 |
| python_exec | only | math | 41 | 100.0% | 97.6% | 1 | 0 | 1.000 |
| python_exec | only | memory | 18 | 83.3% | 72.2% | 2 | 0 | 0.500 |
| python_exec | only | science_mc | 10 | 100.0% | 100.0% | 0 | 0 | 1.000 |
| python_exec | only | ALL | 113 | 97.3% | 91.2% | 7 | 0 | 0.016 |
| constraint_check | used | code | 40 | 97.5% | 92.5% | 2 | 0 | 0.500 |
| constraint_check | used | instruction | 231 | 93.1% | 97.4% | 4 | 14 | 0.031 |
| constraint_check | used | math | 459 | 98.0% | 98.3% | 2 | 3 | 1.000 |
| constraint_check | used | memory | 419 | 88.1% | 92.4% | 6 | 24 | 0.001 |
| constraint_check | used | science_mc | 215 | 92.1% | 93.0% | 2 | 4 | 0.688 |
| constraint_check | used | ALL | 1364 | 93.2% | 95.3% | 16 | 45 | 0.000 |
| constraint_check | only | instruction | 58 | 93.1% | 94.8% | 3 | 4 | 1.000 |
| constraint_check | only | memory | 322 | 87.6% | 91.9% | 6 | 20 | 0.009 |
| constraint_check | only | science_mc | 23 | 95.7% | 100.0% | 0 | 1 | 1.000 |
| constraint_check | only | ALL | 403 | 88.8% | 92.8% | 9 | 25 | 0.009 |

## Summary (all task types)

| tool | route | questions | n | fixed | broken | p | verdict |
|---|---|---|---|---|---|---|---|
| constraint_check | deep_tools | only | 353 | 9 | 18 | 0.122 | neutral |
| constraint_check | deep_tools | used | 647 | 19 | 30 | 0.152 | neutral |
| constraint_check | tools | only | 184 | 23 | 6 | 0.002 | helps |
| constraint_check | tools | used | 590 | 41 | 17 | 0.002 | helps |
| constraint_check | vote_tools | only | 403 | 9 | 25 | 0.009 | hurts |
| constraint_check | vote_tools | used | 1364 | 16 | 45 | 0.000 | hurts |
| python_exec | deep_tools | only | 419 | 17 | 11 | 0.345 | neutral |
| python_exec | deep_tools | used | 1270 | 30 | 29 | 1.000 | neutral |
| python_exec | tools | only | 509 | 24 | 20 | 0.652 | neutral |
| python_exec | tools | used | 1201 | 52 | 31 | 0.028 | helps |
| python_exec | vote_tools | only | 113 | 7 | 0 | 0.016 | helps |
| python_exec | vote_tools | used | 1461 | 15 | 21 | 0.405 | neutral |
| sympy | deep_tools | only | 33 | 1 | 2 | 1.000 | neutral |
| sympy | deep_tools | used | 694 | 4 | 10 | 0.180 | neutral |
| sympy | tools | only | 4 | 0 | 1 | 1.000 | neutral |
| sympy | tools | used | 443 | 13 | 6 | 0.167 | neutral |
| sympy | vote_tools | used | 970 | 4 | 8 | 0.388 | neutral |
