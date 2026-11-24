# mmlupro-9752

Source: MMLU-Pro. Task type: science_mc.

## Question

```text
From the indices of refraction given below, calculate the rotation of the plane of polarization for violet light \lambda = 396.0 nm, in a quartz plate cut perpendicular to the optic axis and 1 mm thick. [\lambda / (396.0 nm)] [n_R/ (1.55610)] [n_L/ (1.55821)] (Refractive Indices for Quartz)

A. 50 degrees
B. 90 degrees
C. 45 degrees
D. 30 degrees
E. 120 degrees
F. 150 degrees
G. 75 degrees
H. 60 degrees
I. 135 degrees
J. 100 degrees
```

The options are listed at the end of the question above.

## Gold

`A`

## Answers

| Run | Route or model | Answer | Graded correct |
|---|---|---|---|
| test 04 run-02 | fast | E | False |
| test 04 run-02 | tools | A | True |
| test 04 run-02 | deep | (no answer) | False |
| test 04 run-02 | deep_tools | A | True |
| test 04 run-02 | vote | A | True |
| test 04 run-02 | vote_tools | E | False |
| test 04 run-03 | fast | H | False |
| test 04 run-03 | tools | H | False |
| test 04 run-03 | deep | H | False |
| test 04 run-03 | deep_tools | H | False |
| test 04 run-03 | vote | E | False |
| test 04 run-03 | vote_tools | H | False |
| router B labels, Qwen | qwen | A | True |
| router B labels, gpt-oss | gptoss | H | False |

## Audit reasons

- test 04 run-03 hand diagnosis: Rotation = pi d (n_L - n_R) / lambda = pi x 1 mm x 0.00211 / 396 nm = 16.7 rad = 959 degrees, which is 59 degrees modulo 180: option H (60), the answer of five routes (Vote answered E). The gold A (50 degrees) does not follow from the given indices.

---

MK's call (wrong gold / ambiguous / gold is right):
