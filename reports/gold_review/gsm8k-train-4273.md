# gsm8k-train-4273

Source: GSM8K (train). Task type: math.

## Question

```text
Brinley's teacher took the grade six students to the San Diego Zoo to watch and learn about animals. While at the zoo, Brinley counted 100 snakes, 80 arctic foxes, and 20 leopards. She also saw ten times more bee-eaters than leopards, half as many cheetahs as snakes, and twice as many alligators as the total number of Arctic foxes and leopards. What's the total number of animals Brinley counted at the zoo?
```

Options: none (free answer).

## Gold

`670`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| router B labels, Qwen | qwen | 650 | False |
| router B labels, gpt-oss | gptoss | 650 | False |

## Audit reasons

- test 02 hand checks: 100 + 80 + 20 + 200 bee-eaters + 50 cheetahs + 2 x (80 + 20) alligators = 650 (both models); the gold 670 does not add up

---

MK's call (wrong gold / ambiguous / gold is right):
