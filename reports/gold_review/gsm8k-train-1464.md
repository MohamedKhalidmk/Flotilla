# gsm8k-train-1464

Source: GSM8K (train). Task type: math.

## Question

```text
During the outbreak of the coronavirus, a company had to ramp up its toilet paper production three times more to cover the increased demand. If the company was producing 7000 toilet paper per day, calculate its total toilet paper production during March of 2020 after increasing its production.
```

Options: none (free answer).

## Gold

`868000`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 651000 | False |
| test 04 run-02 | tools | 651000 | False |
| test 04 run-02 | deep | 651000 | False |
| test 04 run-02 | deep_tools | 651000 | False |
| test 04 run-02 | vote | 651000 | False |
| test 04 run-02 | vote_tools | 651000 | False |
| test 04 run-03 | fast | 651000 | False |
| test 04 run-03 | tools | 651000 | False |
| test 04 run-03 | deep | 651000 | False |
| test 04 run-03 | deep_tools | 651000 | False |
| test 04 run-03 | vote | 651000 | False |
| test 04 run-03 | vote_tools | 651000 | False |
| router B labels, Qwen | qwen | 651000 | False |
| router B labels, gpt-oss | gptoss | 651000 | False |

## Audit reasons

- test 04 run-02 hand diagnosis: 'Three times more' read as 3 x 7000 x 31 = 651,000 by every route; the gold 868,000 uses 4 x 7000 x 31. The wording is ambiguous; Qwen's reading is the common one.
- test 04 run-03 hand diagnosis: 'Three times more' read as 3 x 7000 x 31 = 651,000 by every route; the gold 868,000 uses 4 x 7000 x 31. The wording is ambiguous; Qwen's reading is the common one.
- test 03 gpt-oss failure audit: 'Three times more' read as 3 x 7000 x 31 = 651,000 by every route; the gold 868,000 uses 4 x 7000 x 31. The wording is ambiguous; Qwen's reading is the common one.

---

MK's call (wrong gold / ambiguous / gold is right):
