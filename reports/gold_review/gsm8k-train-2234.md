# gsm8k-train-2234

Source: GSM8K (train). Task type: math.

## Question

```text
Susie babysits every day for 3 hours a day at the rate of $10 per hour. She spent 3/10 of the money she earned from last week to buy a make-up set. She then spent 2/5 of her money on her skincare products. How much is left from her earnings last week, in dollars?
```

Options: none (free answer).

## Gold

`63`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 88.20 | False |
| test 04 run-02 | tools | 88.2 | False |
| test 04 run-02 | deep | 88.2 | False |
| test 04 run-02 | deep_tools | 63 | True |
| test 04 run-02 | vote | 63 | True |
| test 04 run-02 | vote_tools | 63 | True |
| test 04 run-03 | fast | 88.20 | False |
| test 04 run-03 | tools | 88.2 | False |
| test 04 run-03 | deep | 88.2 | False |
| test 04 run-03 | deep_tools | 63 | True |
| test 04 run-03 | vote | 63 | True |
| test 04 run-03 | vote_tools | 63 | True |
| router B labels, Qwen | qwen | 88.2 | False |
| router B labels, gpt-oss | gptoss | 88.2 | False |

## Audit reasons

- test 02 hand checks: Ambiguous: earnings 210, make-up 63, then 2/5 of the remaining 147 = 58.8, leaving 88.2 (both models); the gold 63 takes 2/5 of the original 210

---

MK's call (wrong gold / ambiguous / gold is right):
