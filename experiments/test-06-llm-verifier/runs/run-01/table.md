# Test 06 run-01 (2026-11-22, Nibi 3g.40gb slices, LongMemEval dev, 76 questions)

Judged by Claude Haiku 5.5, official LongMemEval prompts, majority of 3 verdicts per answer (9 of 999 answers split).

| Arm | ID | Right per repeat (of 76) | Mean | Spread | Rejected by the check | Retry flips: right to wrong / wrong to right / same | GPU-seconds per run | Time on check and retry |
|---|---|---|---|---|---|---|---|---|
| Fast | F15 | 62, 63, 60 | 81.1% | 3.9 pts | 0-2 (exact checks only) | none | 2,132-2,388 | 0-3% |
| Fast + LLM check | F33 | 58, 58, 58 | 76.3% | 0 | 13-15 (17-20%) | 4-7 / 1-3 / 5-8 | 4,461-4,986 | 53-57% |
| Deep | F17 | 69, 71, 71 | 92.5% | 2.6 pts | 1 (exact checks only) | none | 3,172-3,431 | 1-2% |
| Deep + LLM check | F34 | 65, 63, 64 | 84.2% | 2.6 pts | 14-16 (18-21%) | 6-8 / 0-1 / 7-8 | 5,483-5,937 | 48-50% |

Flips sum over the 3 repeats: Fast + check 18 right to wrong against 6 wrong to right; Deep + check 21 against 2.
Checker replies with no verdict (accepted): 2 and 1. Full rows: [table.csv](table.csv).

Keep rule (user, before any result): keep the check only if it beats its baseline by more than the repeat spread
without turning more right answers wrong than it fixes. Fast + check is 4.8 points below Fast, Deep + check 8.3 below
Deep, and both turn 3-10 times more right answers wrong than they fix, at about twice the GPU time. Both fail.

Jobs: Nibi 28424070-28424093 (12 runs; the Fir twins 5143762-5143791 cancelled); Haiku check Fir 5356015, judge Fir
5356016 (2,997 verdicts, $0.075). Runs: `$SCRATCH/flotilla/lme_llmv/nibi/runs` on Fir; verdicts
`$SCRATCH/flotilla/lme_llmv/judge/haiku-maj3/{verdicts,combined}.jsonl`.
