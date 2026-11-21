Held-out 10% of the clean pool (476 questions, chosen by question id); trained on 4284. Keep rule: gpt-oss stays only if the router adds about 1 point or more.

| system | held_out_accuracy | gain_over_qwen | held_out_questions | source |
|---|---|---|---|---|
| Qwen alone | 0.895 | 0 | 476 | run-02/router/router_b_modernbert/router_b.json |
| gpt-oss alone | 0.853 | -0.042 | 476 | run-02/router/router_b_modernbert/router_b.json |
| Router B: ModernBERT-base fine-tune (final epoch, saved) | 0.899 | 0.004 | 476 | run-02/router/router_b_modernbert/router_b.json |
| Baseline: bge-small + logistic regression | 0.887 | -0.008 | 476 | run-02/router/router_b_lite/meta.json |
| Perfect router | 0.941 | 0.046 | 476 | run-02/router/router_b_modernbert/router_b.json |
