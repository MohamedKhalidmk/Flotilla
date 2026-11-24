# gsm8k-train-5436

Source: GSM8K (train). Task type: math.

## Question

```text
Wendy has 5 facial products she puts on in the morning and she waits 5 minutes between each product.  She also spends an additional 30 minutes putting on her make-up.  How much time does it take her to put on her "full face?"
```

Options: none (free answer).

## Gold

`55`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 50 | False |
| test 04 run-02 | tools | 50 | False |
| test 04 run-02 | deep | 50 minutes | False |
| test 04 run-02 | deep_tools | 50 | False |
| test 04 run-02 | vote | 50 minutes | False |
| test 04 run-02 | vote_tools | 50 | False |
| test 04 run-03 | fast | 50 | False |
| test 04 run-03 | tools | 50 | False |
| test 04 run-03 | deep | 50 minutes | False |
| test 04 run-03 | deep_tools | 50 | False |
| test 04 run-03 | vote | 50 minutes | False |
| test 04 run-03 | vote_tools | 50 | False |
| router B labels, Qwen | qwen | 50 | False |
| router B labels, gpt-oss | gptoss | 50 | False |

## Audit reasons

- test 04 run-02 hand diagnosis: 5 products with 5 minutes between each: 4 waits = 20 minutes + 30 = 50 (every route). The gold 55 counts 5 waits; ambiguous at best.
- test 04 run-03 hand diagnosis: 5 products with 5 minutes between each: 4 waits = 20 minutes + 30 = 50 (every route). The gold 55 counts 5 waits; ambiguous at best.
- test 03 gpt-oss failure audit: 5 products with 5 minutes between each: 4 waits = 20 minutes + 30 = 50 (every route). The gold 55 counts 5 waits; ambiguous at best.

---

MK's call (wrong gold / ambiguous / gold is right):
