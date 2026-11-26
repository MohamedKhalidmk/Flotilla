# Grader audit: results graded with the old instruction grader

Asked by the user 2026-11-26. From now on every number uses the pilot grader (flotilla label_loop.grade: instruction
questions by RLVR-IFeval's own ground-truth rule). The old grader checked instruction answers with the regex
constraint_check. On the 153 pilot questions, math, GSM8K, AIME, MMLU-Pro and code give the same verdicts under both
graders; only the 36 instruction questions change.

## Regraded where it was free (the 153 pilot questions, run-04 stored answers, regraded on Fir from stdin)

| Route (run-04) | Old grader | Pilot grader | Instructions old to new (of 36) |
|---|---|---|---|
| Fast | 141 | 130 | 30 to 19 |
| Tools | 143 | 126 | 33 to 16 |
| Deep | 144 | 133 | 35 to 24 |
| Deep+Tools | 143 | 130 | 32 to 19 |
| Vote | 150 | 142 | 36 to 28 |
| Vote+Tools | 145 | 129 | 33 to 17 |
| Oracle of the six | 151 | 145 | |

The old grader passed 31% to 52% of the instruction answers the ground-truth rule fails, most for the tool routes.

## Results that used the old grader (not yet regraded)

All of these include run-04's (or run-03's) 236 instruction questions. Regrading them needs RLVR-IFeval's ground-truth
column for the 200 instruction questions outside the pilot; it is not on Fir (only the pilot's 36 were attached) and
is probably on Nibi. Fetching it from Hugging Face (allenai/RLVR-IFeval) is a download and needs the user's yes.

| Where | Result (old grader) | Regraded |
|---|---|---|
| Flotilla test 04 run-03 table (1,450 pool) | Fast 0.903, Tools 0.925, Deep 0.952, Deep+Tools 0.943, Vote 0.967, Vote+Tools 0.963, oracle 0.988 | pilot subset only, above |
| Flotilla test 04 run-04 summary (1,950 with LongMemEval) | Fast 0.879 and the other routes' accuracies, best any 0.984 | not yet |
| STATUS row 16, IDEAS 24: strategy routers on run-04 labels | F30 0.959 at 72% of Vote's compute, F31 0.963 | not yet (labels change, routers would need retraining; retraining is held for the relabel) |
| STATUS row 26: tool use by task type | Tools beats Fast +75/-40, Deep+Tools ties Deep, Vote+Tools loses to Vote | not yet |
| STATUS row 29: constraint_check on instruction questions | Tools 77% either way on questions with a real constraint | not yet |
| STATUS row 31: per tool | constraint_check helps Tools +41/-18 (instructions +23/-1), hurts Vote+Tools | not yet; the instruction part is the most affected |
| Flotilla test 03 router B (held-out) | Qwen 0.895, gpt-oss 0.853, router B 0.899, perfect router 0.941 | not yet |
| Flotilla test 02 small test, run-01 and run-02 | marked "scored before the grader fixes, audited" already | not regraded |
| STATUS row 32, IDEAS 29: the pilot's first numbers (commits c260f9a, 00e69f0) | math counted wrong by a broken checker | corrected 2026-11-26 (pilot_pool_scores.md, pilot_unique_wins.md) |

Not affected: LongMemEval results (Haiku judge), GRAFT tests (MemoryAgentBench substring match), test 06 LLM verifier
(LongMemEval only).
