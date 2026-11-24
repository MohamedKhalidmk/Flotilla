# gsm8k-train-1213

Source: GSM8K (train). Task type: math.

## Question

```text
Lyssa and Precious took an English proficiency exam. Lyssa answered 20% of the items incorrectly. Precious got 12 mistakes. How many more correct answers did Lyssa get than precious if there were 75 items in the exam?
```

Options: none (free answer).

## Gold

`3`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | -3 | False |
| router B labels, gpt-oss | gptoss | -3 | False |

## Audit reasons

- test 02 hand checks: Lyssa: 75 - 15 = 60 correct; Precious: 75 - 12 = 63. Lyssa got 3 fewer, so -3 answers the question as asked; the gold 3 answers the reverse question

---

MK's call (wrong gold / ambiguous / gold is right):
