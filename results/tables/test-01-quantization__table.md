MATH-500, all 500 questions, greedy, math-verify. Rule 4.1: 4-bit if within 1.0 point of 8-bit.

| model | build | bits | accuracy | correct | n | hit_token_cap | max_tokens | output_tokens | wall_seconds | run |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | BF16 | 16-bit reference | 0.978 | 489 | 500 | 1 | 131072 | 1037977 | 2,985 | run-01/math500-qwen-bf16 |
| Qwen3.8-27B | FP8 (ours) | 8-bit | 0.984 | 492 | 500 | 0 | 131072 | 926002 | 906.6 | run-01/math500-qwen-fp8-ours |
| Qwen3.8-27B | INT4 (RedHat) | 4-bit | 0.988 | 494 | 500 | 1 | 131072 | 1149490 | 1,992 | run-01/math500-qwen-int4-redhat |
| Qwen3.8-27B | W4A16 (ours) | 4-bit | 0.984 | 492 | 500 | 2 | 131072 | 1219049 | 2,136 | run-01/math500-qwen-w4a16-ours |
| Phi-4-reasoning-plus | BF16 | 16-bit reference | 0.824 | 412 | 500 | 379 | 30000 | 12030474 | 21,996 | run-01/math500-phi-bf16 |
| Phi-4-reasoning-plus | FP8 (NVIDIA) | 8-bit | 0.818 | 409 | 500 | 368 | 30000 | 11803306 | 9,820 | run-01/math500-phi-fp8-nvidia |
| Phi-4-reasoning-plus | FP8 (ours) | 8-bit | 0.82 | 410 | 500 | 377 | 30000 | 12043088 | 17,120 | run-01/math500-phi-fp8-ours |
| Phi-4-reasoning-plus | W4A16 (AMD) | 4-bit | 0.776 | 388 | 500 | 386 | 30000 | 12342755 | 16,687 | run-01/math500-phi-w4a16-amd |
| Phi-4-reasoning-plus | W4A16 (ours) | 4-bit | 0.786 | 393 | 500 | 398 | 30000 | 12769728 | 17,274 | run-01/math500-phi-w4a16-ours |
