Small test (5% dev sets, same items for every model). RULER = mean sub-task score, others accuracy. gpt-oss mean is over its 9 text benchmarks (no image input).

| benchmark | n | qwen | gptoss | cmda | only_qwen | only_gptoss | only_cmda | all | none | two_of_three | perfect_router_qwen_gptoss | perfect_router_all3 | router_gain_over_qwen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GSM8K | 66 | 1 | 0.939 | 0.955 | 2 | 0 | 0 | 61 | 0 | 3 | 1 | 1 | 0 |
| MATH-500 | 25 | 0.96 | 0.88 | 0.92 | 1 | 0 | 0 | 22 | 1 | 1 | 0.96 | 0.96 | 0 |
| AIME 2025 | 20 | 1 | 0.7 | 0.9 | 2 | 0 | 0 | 14 | 0 | 4 | 1 | 1 | 0 |
| AIME 2026 | 20 | 1 | 0.7 | 0.9 | 1 | 0 | 0 | 13 | 0 | 6 | 1 | 1 | 0 |
| GPQA-Diamond | 20 | 0.85 | 0.7 | 0.8 | 2 | 0 | 0 | 13 | 2 | 3 | 0.9 | 0.9 | 0.05 |
| IFEval | 27 | 0.963 | 0.926 | 0.889 | 0 | 0 | 0 | 21 | 0 | 6 | 1 | 1 | 0.037 |
| LiveCodeBench | 23 | 0.739 | 0.478 | 0.391 | 3 | 1 | 0 | 5 | 5 | 9 | 0.783 | 0.783 | 0.043 |
| RULER 32K | 33 | 0.697 | 0.867 | 0.696 | 0 | 3 | 1 | 18 | 5 | 6 | 0.897 | 0.927 | 0.2 |
| RULER 64K | 33 | 0.798 | 0.76 | 0.646 | 2 | 0 | 0 | 20 | 7 | 4 | 0.83 | 0.83 | 0.032 |
| MMMU | 45 | 0.756 |  | 0.667 | 5 | 0 | 1 | 29 | 10 | 0 | 0.756 | 0.778 | 0 |
| OCRBench | 50 | 0.88 |  | 0.74 | 8 | 0 | 1 | 36 | 5 | 0 | 0.88 | 0.9 | 0 |
| Mean over benchmarks | 362 | 0.877 | 0.772 | 0.773 | 26 | 4 | 3 | 252 | 35 | 42 | 0.91 | 0.916 | 0.033 |
