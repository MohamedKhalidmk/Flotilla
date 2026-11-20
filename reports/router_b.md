# Router B, 2026-11-20

Labels: the real Flotilla loop (flotilla/label_loop.py) over the 4,760 clean pool questions (leakage-checked against every
test set, small-test items included), graded from the pool (code fences stripped). Qwen 4,217/4,760 (88.6%), gpt-oss
3,933/4,760 (82.6%). Per type, Qwen / gpt-oss: math 95.9 / 87.7, code 91.9 / 79.3, science MC 68.9 / 70.5,
instruction 80.7 / 77.5 (%).

Held-out 10% (476 questions, chosen by question id), same split for both routers:

| | accuracy | vs Qwen alone |
|---|---|---|
| Qwen alone | 0.895 | |
| gpt-oss alone | 0.853 | -4.2 |
| ModernBERT-base fine-tune (router_b.py), final epoch (saved) | 0.899 | +0.4 |
| bge-small + logistic regression (router_b_lite.py) | 0.887 | -0.8 |
| perfect router | 0.941 | +4.6 |

ModernBERT's epoch 1 scored 0.906; choosing an epoch by held-out score would tune on the test data, so the saved final
model is the result. Decision (user's rule, set before the result): router gain under about 1 point, so gpt-oss is dropped
and Qwen runs alone. Caveat: the pool has no long-context questions, where gpt-oss led on the small test (RULER 32K
0.867 vs 0.697); a fixed long-input rule is a separate, open decision.
