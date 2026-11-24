# gsm8k-train-2338

Source: GSM8K (train). Task type: math.

## Question

```text
A bottle can hold 2 cups of water. How many cups of water are needed to fill up 10 whole bottles and 5 half-capacity bottles?
```

Options: none (free answer).

## Gold

`30`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 25 | False |
| test 04 run-02 | tools | 25 | False |
| test 04 run-02 | deep | 25 | False |
| test 04 run-02 | deep_tools | 25 | False |
| test 04 run-02 | vote | 25 | False |
| test 04 run-02 | vote_tools | 25 | False |
| test 04 run-03 | fast | 25 | False |
| test 04 run-03 | tools | 25 | False |
| test 04 run-03 | deep | 25 | False |
| test 04 run-03 | deep_tools | 25 | False |
| test 04 run-03 | vote | 25 | False |
| test 04 run-03 | vote_tools | 25 | False |
| router B labels, Qwen | qwen | 25 | False |
| router B labels, gpt-oss | gptoss | 25 | False |

## Audit reasons

- test 04 run-02 hand diagnosis: 10 bottles x 2 cups + 5 half bottles x 1 cup = 25 cups. Every route answered 25; the gold says 30.
- test 04 run-03 hand diagnosis: 10 bottles x 2 cups + 5 half bottles x 1 cup = 25 cups. Every route answered 25; the gold says 30.
- test 03 gpt-oss failure audit: 10 bottles x 2 cups + 5 half bottles x 1 cup = 25 cups. Every route answered 25; the gold says 30.

---

MK's call (wrong gold / ambiguous / gold is right):
