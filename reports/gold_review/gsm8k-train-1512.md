# gsm8k-train-1512

Source: GSM8K (train). Task type: math.

## Question

```text
In a certain company, for every customer served, an employee gets as many bonus points, as 20% of the number of customers served. On Monday, Tom served 10 customers per hour for 8 hours. How many bonus points did Tom earn that day?
```

Options: none (free answer).

## Gold

`16`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 1280 | False |
| test 04 run-02 | tools | 16 | True |
| test 04 run-02 | deep | 1280 | False |
| test 04 run-02 | deep_tools | 1280 | False |
| test 04 run-02 | vote | 1280 | False |
| test 04 run-02 | vote_tools | 1280 | False |
| test 04 run-03 | fast | 1280 | False |
| test 04 run-03 | tools | 16 | True |
| test 04 run-03 | deep | 1280 | False |
| test 04 run-03 | deep_tools | 1280 | False |
| test 04 run-03 | vote | 1280 | False |
| test 04 run-03 | vote_tools | 1280 | False |
| router B labels, Qwen | qwen | 1280 | False |
| router B labels, gpt-oss | gptoss | 1280 | False |

## Audit reasons

- test 02 hand checks: Ambiguous: 'for every customer served ... as many bonus points as 20% of the number of customers' gives 16 per customer, 1,280 in all (both models); the gold 16 reads it as 16 in total

---

MK's call (wrong gold / ambiguous / gold is right):
