# mmlupro-3700

Source: MMLU-Pro. Task type: science_mc.

## Question

```text
Consider a kinetic experiment in which the chemical re-action is accompanied by a temperature change. Using the Heisenberg uncertainty principle, calculate the uncertainty in a simultaneous measurement of time and temperature.

A. ∆T ∆t ≤ h/4π
B. ∆T ∆t \geq h/c
C. ∆T ∆t = h^2/c^2
D. ∆T ∆t = h/c
E. ∆T ∆t \geq 2πh
F. ∆T ∆t \geq h^2/c
G. ∆T ∆t ≤ h/c
H. ∆T ∆t \geq hc
I. ∆T ∆t \geq h/4π
J. ∆T ∆t = kT^2
```

The options are listed at the end of the question above.

## Gold

`B`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | B | True |
| test 04 run-02 | tools | I | False |
| test 04 run-02 | deep | A | False |
| test 04 run-02 | deep_tools | I | False |
| test 04 run-02 | vote | A | False |
| test 04 run-02 | vote_tools | I | False |
| test 04 run-03 | fast | I | False |
| test 04 run-03 | tools | I | False |
| test 04 run-03 | deep | I | False |
| test 04 run-03 | deep_tools | I | False |
| test 04 run-03 | vote | I | False |
| test 04 run-03 | vote_tools | I | False |
| router B labels, Qwen | qwen | E | False |
| router B labels, gpt-oss | gptoss | A | False |

## Audit reasons

- test 04 run-03 hand diagnosis: With E = kT, Heisenberg gives dT dt >= h/(4 pi k); no option has the k. The gold B, h/c, has the wrong units (h/c is not energy x time / temperature). Every route picked I (h/4 pi), the closest form. The item is broken.

---

MK's call (wrong gold / ambiguous / gold is right):
