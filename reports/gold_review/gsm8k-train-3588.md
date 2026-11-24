# gsm8k-train-3588

Source: GSM8K (train). Task type: math.

## Question

```text
A group of bedbugs infested an old mattress. Every day, the number of bedbugs would triple. After four days, there were 810 bedbugs burrowing into the mattress. How many bedbugs did the group start with?
```

Options: none (free answer).

## Gold

`30`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 10 | False |
| test 04 run-02 | tools | 10 | False |
| test 04 run-02 | deep | 10 | False |
| test 04 run-02 | deep_tools | 10 | False |
| test 04 run-02 | vote | 10 | False |
| test 04 run-02 | vote_tools | 10 | False |
| test 04 run-03 | fast | 10 | False |
| test 04 run-03 | tools | 10 | False |
| test 04 run-03 | deep | 10 | False |
| test 04 run-03 | deep_tools | 10 | False |
| test 04 run-03 | vote | 10 | False |
| test 04 run-03 | vote_tools | 10 | False |
| router B labels, Qwen | qwen | 10 | False |
| router B labels, gpt-oss | gptoss | 10 | False |

## Audit reasons

- test 04 run-02 hand diagnosis: Tripling each day for four days: start x 3^4 = 810, start = 10 (every route). The gold 30 uses three triplings.
- test 04 run-03 hand diagnosis: Tripling each day for four days: start x 3^4 = 810, start = 10 (every route). The gold 30 uses three triplings.
- test 03 gpt-oss failure audit: Tripling each day for four days: start x 3^4 = 810, start = 10 (every route). The gold 30 uses three triplings.

---

MK's call (wrong gold / ambiguous / gold is right):
