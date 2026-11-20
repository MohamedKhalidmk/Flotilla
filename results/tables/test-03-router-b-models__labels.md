Router labels: share of pool questions each model answered correctly.

| run | model | questions | correct | accuracy | math_acc | code_acc | science_mc_acc | instruction_acc |
|---|---|---|---|---|---|---|---|---|
| run-02 (real loop) | Qwen | 4760 | 4217 | 0.886 | 0.959 | 0.919 | 0.689 | 0.806 |
| run-02 (real loop) | gpt-oss | 4760 | 3933 | 0.826 | 0.877 | 0.793 | 0.705 | 0.775 |
| run-01 (v1, no tool loop, broken) | Qwen | 4856 | 2805 | 0.578 | 0.58 | 0.077 | 0.719 | 0.629 |
| run-01 (v1, no tool loop, broken) | Phi | 4856 | 0 | 0 | 0 | 0 | 0 | 0 |
