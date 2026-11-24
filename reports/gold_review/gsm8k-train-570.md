# gsm8k-train-570

Source: GSM8K (train). Task type: math.

## Question

```text
Cindy tosses 5 dimes into the wishing pond.  Eric flips 3 quarters into the pond.  Garrick throws in 8 nickels.  Ivy then drops 60 pennies in.  If Eric dips his hands into the water and pulls out a quarter, how much money, in cents, did they put into the pond?
```

Options: none (free answer).

## Gold

`200`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | 225 | False |
| router B labels, gpt-oss | gptoss | 225 | False |

## Audit reasons

- test 02 hand checks: Ambiguous: they put in 50 + 75 + 40 + 60 = 225 cents (both models); the gold 200 subtracts the quarter Eric took back, which the question does not ask

---

MK's call (wrong gold / ambiguous / gold is right):
