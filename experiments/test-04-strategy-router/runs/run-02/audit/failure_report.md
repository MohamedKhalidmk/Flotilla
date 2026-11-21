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

Every question is listed with its question, gold, each route's answers and the diagnosis in
[always_wrong.md](always_wrong.md) ([html](always_wrong.html), [pdf](always_wrong.pdf)).

| Diagnosis (hand-checked) | Questions | What it was |
|---|---|---|
| Grader bug | 34 | Instruction checker: "Do not include keywords" read as "include" (7), postscript accepted only as "P.S." (5), "* * *" divider not counted (4), "capital words at most N" read as "all capitals" (3), whole-output-JSON rule tested on the final_answer field (4), bullets plus a JSON demand no answer can meet (1). Code: float outputs compared as text although the task allows 1e-5 to 1e-9 error (5). Math: "\\$3.50", \\text{} answers, option letter vs option value, the other valid sign of a vector (5). |
| Verifier bug | 22 | MMLU-Pro (options A to J): routes answered the gold letter first, the option check accepted only A to D, rejected it, and the retry moved off it. |
| Wrong gold | 6 | Five GSM8K train golds wrong or ambiguous; one interactive code problem the stored tests cannot judge. |
| Model wrong | 7 | 2 MMLU-Pro, AIME 2002 II-4, gsm8k-5520, 3 instruction questions where no route followed the format rule. |

So 7 of the 69 are Qwen's own errors.

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
