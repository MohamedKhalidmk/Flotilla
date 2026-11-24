# gsm8k-train-5887

Source: GSM8K (train). Task type: math.

## Question

```text
Nina has four times more math homework and eight times more reading homework than Ruby. If Ruby has six math homework and two reading homework, how much homework is Nina having altogether?
```

Options: none (free answer).

## Gold

`48`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | 40 | False |
| router B labels, gpt-oss | gptoss | 40 | False |

## Audit reasons

- test 02 hand checks: Ambiguous 'times more': 4 x 6 + 8 x 2 = 40 (both models); the gold 48 reads it as 5x and 9x

---

MK's call (wrong gold / ambiguous / gold is right):
