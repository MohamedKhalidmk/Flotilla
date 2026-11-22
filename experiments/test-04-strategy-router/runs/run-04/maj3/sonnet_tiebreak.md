# Sonnet tiebreak on split Haiku verdicts (run-04-lme-maj3-sonnet, 2026-11-22)

The 56 answer groups whose three Haiku verdicts split (34 at 2/3 yes, 22 at 1/3) each got one Claude Sonnet 5.5
verdict with the same official LongMemEval prompt (thinking off with between_tools; Sonnet 5.5 takes no temperature);
Sonnet's verdict replaces the Haiku majority for those groups (`memory_route tiebreak`, judge folder
haiku-v10-maj3-sonnet, Fir 5231463 after the Haiku check 5231462). Sonnet differs from the Haiku majority on 22 of 56.
Labels merged into run-04-lme-maj3-sonnet (Fir 5232994); run-04-lme-maj3 stays the label set; routers not retrained.

| route | right before | right after | wrong->right | right->wrong |
|---|---|---|---|---|
| fast | 404 | 407 | 4 | 1 |
| tools | 417 | 419 | 5 | 3 |
| deep | 441 | 443 | 2 | 0 |
| deep_tools | 441 | 443 | 2 | 0 |
| vote | 450 | 451 | 1 | 0 |
| vote_tools | 434 | 433 | 1 | 2 |
| memory routes | 212-223 | +0 to +1 | 1 | 0 |

7 of 500 memory labels change (0.4% of 1,950): lme-06878be2 vote_tools -> fast (dev), lme-gpt4_194be4b3 deep_tools
-> fast (held-out), and 5 in train (lme-1f2b8d4f deep -> fast, lme-3c1045c8 none -> vote, lme-4baee567 tools -> fast,
lme-5d3d2817 tools -> deep_tools, lme-80ec1f4f_abs tools -> deep_tools). Cost $0.04 of the job's $0.263.
