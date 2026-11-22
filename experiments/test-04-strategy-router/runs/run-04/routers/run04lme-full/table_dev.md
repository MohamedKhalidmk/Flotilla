test-04 supervised routers on dev (293 questions), trained on train (1365), tuned on dev (flotilla/strategy_router.py, seed 20261120). Best fixed route (keep-rule reference): vote. GPU-seconds per question from the labels (route job GPU-s spread by wall time). Keep rule: within 1 point of the best fixed route at lower compute, or more than 1 point better. Labels /scratch/khaledmk/flotilla/test04-labels/run-04-lme (9920470343dce6ee).

| row | kind | split | questions | accuracy | gpu_seconds_per_question | output_tokens_per_question | points_vs_best_fixed | gpu_vs_best_fixed | picked | params | keep_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| label | router | dev | 293 | 0.904 | 10.91 | 2298 | -6.1 | 0.318 | fast:123 tools:16 deep:154 |  | drop |
| success | router | dev | 293 | 0.959 | 24.76 | 8127 | -0.7 | 0.722 | fast:19 tools:7 deep:168 vote_tools:30 vote:69 | tau=0.96 | keep (within 1 point, less compute) |
| bge_lr | router | dev | 293 | 0.963 | 31.17 | 14538 | -0.3 | 0.909 | tools:1 deep:23 deep_tools:21 vote_tools:89 vote:159 | C=1.0 tau=0.97 | keep (within 1 point, less compute) |
| knn | router | dev | 293 | 0.952 | 22.97 | 11666 | -1.4 | 0.67 | fast:10 tools:21 deep:56 deep_tools:53 vote_tools:55 vote:98 | k=50 tau=0.99 | drop |
| fast | fixed route | dev | 293 | 0.894 | 9.63 | 1612 | -7.2 | 0.281 | fast:293 |  |  |
| tools | fixed route | dev | 293 | 0.911 | 11.56 | 1809 | -5.5 | 0.337 | tools:293 |  |  |
| deep | fixed route | dev | 293 | 0.945 | 15.24 | 3774 | -2 | 0.444 | deep:293 |  |  |
| deep_tools | fixed route | dev | 293 | 0.918 | 18.71 | 4334 | -4.8 | 0.545 | deep_tools:293 |  |  |
| vote_tools | fixed route | dev | 293 | 0.942 | 30.09 | 16668 | -2.4 | 0.878 | vote_tools:293 |  |  |
| vote (best fixed) | fixed route | dev | 293 | 0.966 | 34.29 | 16436 | 0 | 1 | vote:293 |  |  |
| oracle | cheapest correct route, known only after trying all | dev | 293 | 0.983 | 7.67 | 1685 | 1.7 | 0.224 | fast:111 tools:50 deep:121 deep_tools:7 vote_tools:3 vote:1 |  |  |
