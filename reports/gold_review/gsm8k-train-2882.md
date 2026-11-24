# gsm8k-train-2882

Source: GSM8K (train). Task type: math.

## Question

```text
Dexter and Jay are using a gallon of white paint to paint the walls. Dexter used 3/8 of the gallon of paint while Jay used 5/8 of a gallon of paint. If a gallon is equal to 4 liters, how many liters of paint were left from Dexter and Jay combined?
```

Options: none (free answer).

## Gold

`4`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | 0 | False |
| test 04 run-02 | tools | 0 | False |
| test 04 run-02 | deep | 0 | False |
| test 04 run-02 | deep_tools | 0 | False |
| test 04 run-02 | vote | 0 | False |
| test 04 run-02 | vote_tools | 0 | False |
| test 04 run-03 | fast | 0 | False |
| test 04 run-03 | tools | 0 | False |
| test 04 run-03 | deep | 0 | False |
| test 04 run-03 | deep_tools | 0 | False |
| test 04 run-03 | vote | 0 | False |
| test 04 run-03 | vote_tools | 0 | False |
| router B labels, Qwen | qwen | 0 | False |
| router B labels, gpt-oss | gptoss | 0 | False |

## Audit reasons

- test 04 run-02 hand diagnosis: Dexter used 3/8 and Jay 5/8 of one gallon, so nothing is left: every route answered 0. The gold 4 (litres) assumes each had a gallon, which the question does not say.
- test 04 run-03 hand diagnosis: Dexter used 3/8 and Jay 5/8 of one gallon, so nothing is left: every route answered 0. The gold 4 (litres) assumes each had a gallon, which the question does not say.
- test 03 gpt-oss failure audit: Dexter used 3/8 and Jay 5/8 of one gallon, so nothing is left: every route answered 0. The gold 4 (litres) assumes each had a gallon, which the question does not say.

---

MK's call (wrong gold / ambiguous / gold is right):
