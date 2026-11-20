# Small test (5% dev sets, same items for all models), 2026-11-20

Protocol-v9 loop: solver v1, verifier v2, native tool calls, N = 1, max_tokens 32,768. RULER = mean sub-task score, others accuracy.
Qwen3.8-27B W4A16 (ours), gpt-oss-20b (medium, MXFP4; no image input), Command A+ (official FP8, 4 H100).

| Benchmark | n | Qwen | gpt-oss | Cmd A+ | only Qwen | only gpt-oss | only Cmd A+ | all | none | perfect router Q+G | gain over Qwen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AIME 2025 | 20 | 1.000 | 0.700 | 0.900 | 2 | 0 | 0 | 14 | 0 | 1.000 | +0.000 |
| AIME 2026 | 20 | 1.000 | 0.700 | 0.900 | 1 | 0 | 0 | 13 | 0 | 1.000 | +0.000 |
| GPQA | 20 | 0.850 | 0.700 | 0.800 | 2 | 0 | 0 | 13 | 2 | 0.900 | +0.050 |
| GSM8K | 66 | 1.000 | 0.939 | 0.955 | 2 | 0 | 0 | 61 | 0 | 1.000 | +0.000 |
| IFEval (prompt-strict) | 27 | 0.963 | 0.926 | 0.889 | 0 | 0 | 0 | 21 | 0 | 1.000 | +0.037 |
| LiveCodeBench | 23 | 0.739 | 0.478 | 0.391 | 3 | 1 | 0 | 5 | 5 | 0.783 | +0.043 |
| MATH-500 | 25 | 0.960 | 0.880 | 0.920 | 1 | 0 | 0 | 22 | 1 | 0.960 | +0.000 |
| MMMU | 45 | 0.756 | n/a | 0.667 | 5 | - | 1 | 29 | 10 | 0.756 | +0.000 |
| OCRBench | 50 | 0.880 | n/a | 0.740 | 8 | - | 1 | 36 | 5 | 0.880 | +0.000 |
| RULER 32K | 33 | 0.697 | 0.867 | 0.695 | 0 | 3 | 1 | 18 | 5 | 0.897 | +0.200 |
| RULER 64K | 33 | 0.798 | 0.760 | 0.646 | 2 | 0 | 0 | 20 | 7 | 0.830 | +0.032 |
| **Mean over benchmarks** | | **0.877** | 0.772 (9) | 0.773 | | | | | | **0.910** | **+0.033** |

"all" = right for every model that has the benchmark; 42 items were right for exactly two of three. Perfect router over all three: 0.916.

Rule 4.2 (v9): Command A+ alone minus Qwen alone = -0.104, paired stratified bootstrap (10,000) 95% CI [-0.143, -0.066].
The lower bound is not above 0, so Command A+ is dropped. Compute: 362 items in 6,456 s on 4 H100 (25,825 GPU-s, 28,948 with load).
