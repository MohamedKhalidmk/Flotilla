# Test 04: route overlap and failure causes (full labels, 1,450 questions)

Built from `graded/` (flotilla/strategy_labels.py) and `audit/` (flotilla/failure_audit.py) in this run. Causes for the
69 always-wrong questions were checked by hand: every question's answers, verifier checks and reasoning were read.

## Routes

| Route | Accuracy | Right | Only this route right | Wrong, another route right | Main causes of those misses |
|---|---|---|---|---|---|
| Fast | 0.825 | 1196 | 7 | 185 | wrong 95, verifier 73, no_answer 15, grader_suspect 2 |
| Tools | 0.872 | 1265 | 4 | 116 | wrong 66, verifier 38, no_answer 10, grader_suspect 1, cap 1 |
| Deep | 0.863 | 1251 | 5 | 130 | verifier 64, wrong 34, cap 23, no_answer 9 |
| Deep+Tools | 0.876 | 1270 | 9 | 111 | wrong 43, verifier 25, no_answer 24, cap 19 |
| Vote | 0.882 | 1279 | 3 | 102 | verifier 61, vote 15, cap 13, wrong 12, no_answer 1 |
| Vote+Tools | 0.899 | 1304 | 8 | 77 | verifier 29, vote 18, wrong 15, no_answer 9, cap 6 |

Some route right: 0.952. Cheapest-correct labels: {'fast': 1196, 'deep': 44, 'tools': 111, 'none': 69, 'vote_tools': 8, 'deep_tools': 15, 'vote': 7}.

The combos are not useless on the full labels: Vote+Tools is the most accurate route, and Deep+Tools beats Deep and Tools.
But the numbers above are depressed by the bugs below, which hit every route, so they will move once fixed.

## The 69 questions every route got wrong

| Cause (hand-checked) | Questions | Example |
|---|---|---|
| Verifier rejected a correct answer: the option check accepted only A to D (MMLU-Pro has A to J) | 21 | mmlupro-3588: every route answered E (gold E) first; rejected as invalid, retries moved to H |
| Instruction checker bug (verifier and grader both use it): "Do not include keywords" read as "include" (7), postscript accepted only as "P.S." (5), "* * *" paragraph divider not counted (4), "capital words at most N times" read as "all capitals" (3) | 19 | rlvrif-11110: answer "negative", no forbidden word, failed "0/1 constraints met" |
| Format clash: the task asks to wrap the whole output in JSON, the loop keeps only the final_answer field | 4 | rlvrif-12275: answer "park" (correct) failed the JSON check |
| Math grader missed a right answer (format) | 5 | prealgebra-724: "3.50" vs gold "\\$3.50"; geometry-625: answered option A, gold is option A's expression; precalculus-663: the negated unit vector, also valid |
| Gold answer wrong or ambiguous (GSM8K train) | 5 | gsm8k-2338: 10 bottles x 2 cups + 5 half bottles = 25 (gold 30); gsm8k-1464: "three times more" read as x3, gold uses x4 |
| Qwen wrong | 11 | 6 code (Deep and Vote also hit the 32,768-token cap on 2 to 3 routes each), 3 MMLU-Pro, AIME 2002 II-4, gsm8k-5520 |
| Instruction, not yet diagnosed | 4 | rlvrif-12433, 13923, 3747, 7128 |

So about 11 to 15 of the 69 are Qwen's own errors; the rest are the loop's checks or the data.

## Causes of all route failures (automatic, before the hand check)

`missed causes` above are automatic: `verifier` = a verifier attempt held an answer the grader accepts but the final differs;
`no_answer` = no parsable final answer; `cap` = a call stopped at 32,768 tokens; `vote` = a sample was right but lost the vote;
`grader_suspect` = the gold string appears in the answer; `wrong` = none of these (includes the instruction-checker bug).

## Same bugs elsewhere

- Test 03 (router B labels, 4,760 pool questions per model): the A-to-D option check rejected an E-J answer on 444 Qwen and 438
  gpt-oss labels; the instruction checker also graded those labels. The gpt-oss decision rested on these labels.
- Test 02 (small test): no E-J rejections (GPQA has four options, MMMU items carry their options). IFEval is scored by the
  benchmark scorer, but the in-loop verifier used the same instruction checker, so some correct IFEval answers may have been
  sent to a retry; not yet counted.
