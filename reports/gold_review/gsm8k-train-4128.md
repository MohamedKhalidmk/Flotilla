# gsm8k-train-4128

Source: GSM8K (train). Task type: math.

## Question

```text
Sonia and Joss are moving to their new house at the lake. They have too much stuff in their previous house and decide to make multiple trips to move it all to the new house. They spend 15 minutes filling the car with their stuff and spend 30 minutes driving from the previous house to the new house. Fortunately, they did not waste any time unloading their stuff into the new house. In total they make 6 trips to complete the move. How many hours did they spend moving?
```

Options: none (free answer).

## Gold

`7`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | 4.5 | False |
| router B labels, gpt-oss | gptoss | 4.5 | False |

## Audit reasons

- test 02 hand checks: 6 trips x (15 + 30) minutes = 4.5 hours (both models); the gold 7 assumes drives back that the question never mentions, and 6 x 75 minutes would be 7.5, not 7

---

MK's call (wrong gold / ambiguous / gold is right):
