# Majority of 3 Haiku verdicts on LongMemEval (run-04-lme-maj3, 2026-11-22)

Haiku 5.5 takes no temperature, so every answer got two more verdicts (judge haiku-v10-r2, Fir 5210454, $0.256; canary 5210453 34/100 as before, $0.027) and the label uses the majority with haiku-v10's first verdict (`memory_route combine-verdicts`; folder haiku-v10-maj3). 56 of 5,008 answer groups were split. Labels merged by `scripts/fir/merge_lme_labels.sh haiku-v10-maj3 run-04-lme-maj3` (Fir 5213207); run-04-lme is kept; routers not retrained.

pool rows unchanged: 1450; memory rows: 500

| route | right before | right after | wrong->right | right->wrong |
|---|---|---|---|---|
| fast | 404/500 (80.8%) | 404/500 (80.8%) | 1 | 1 |
| tools | 415/500 (83.0%) | 417/500 (83.4%) | 4 | 2 |
| deep | 440/500 (88.0%) | 441/500 (88.2%) | 1 | 0 |
| deep_tools | 440/500 (88.0%) | 441/500 (88.2%) | 2 | 1 |
| vote | 451/500 (90.2%) | 450/500 (90.0%) | 0 | 1 |
| vote_tools | 433/500 (86.6%) | 434/500 (86.8%) | 1 | 0 |
| memory | 212/500 (42.4%) | 212/500 (42.4%) | 0 | 0 |
| memory_deep | 216/500 (43.2%) | 217/500 (43.4%) | 1 | 0 |
| deep_tools_memory | 221/500 (44.2%) | 223/500 (44.6%) | 2 | 0 |
| vote_memory | 220/500 (44.0%) | 220/500 (44.0%) | 0 | 0 |

labels changed: 6 of 500 memory questions (1.2%); of all 1950: 0.3%
moves (old -> new): [(('deep_tools', 'tools'), 2), (('deep', 'deep_tools'), 2), (('vote', 'none'), 1), (('fast', 'tools'), 1)]
label counts before: {'fast': 250, 'deep_tools': 49, 'none': 15, 'vote_tools': 2, 'tools': 111, 'deep': 59, 'vote': 6, 'deep_tools_memory': 1, 'memory': 5, 'memory_deep': 2}
label counts after:  {'fast': 249, 'deep_tools': 49, 'none': 16, 'vote_tools': 2, 'tools': 114, 'deep': 57, 'vote': 5, 'deep_tools_memory': 1, 'memory': 5, 'memory_deep': 2}

Changed labels: lme-3c1045c8 vote -> none (train), lme-4baee567 fast -> tools (train), lme-5d3d2817 deep_tools -> tools (train), lme-80ec1f4f_abs deep_tools -> tools (train), lme-a2f3aa27 deep -> deep_tools (train), lme-gpt4_194be4b3 deep -> deep_tools (held-out). No dev label changed, so the routers' dev numbers stand.

lme-3c1045c8: the answer "2.5 years" equals the gold, yet the majority on every route is no; Haiku is consistently wrong on this question, so it stays a label error unless corrected by hand.
