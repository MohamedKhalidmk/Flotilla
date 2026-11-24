# gsm8k-train-5496

Source: GSM8K (train). Task type: math.

## Question

```text
A trolley driver picked up 10 people on his 1st stop.  On the next stop, 3 people got off and twice as many people from the 1st stop got on.  On the third stop, 18 people got off and 2 got on.  How many people are currently on the trolley?
```

Options: none (free answer).

## Gold

`12`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | 11 | False |
| router B labels, gpt-oss | gptoss | 11 | False |

## Audit reasons

- test 02 hand checks: 10, then -3 + 20 = 27, then -18 + 2 = 11 (both models); the gold 12 is off by one

---

MK's call (wrong gold / ambiguous / gold is right):
