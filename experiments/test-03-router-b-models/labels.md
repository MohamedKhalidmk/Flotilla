Router labels: share of pool questions each model answered correctly.

| candidate | setup | valid | run | model | questions | correct | accuracy | math_acc | code_acc | science_mc_acc | instruction_acc |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F06 | S119 | scored before the grader fixes, audited | run-02 (real loop) | Qwen | 4760 | 4217 | 0.886 | 0.959 | 0.919 | 0.689 | 0.806 |
| F07 | S120 | scored before the grader fixes, audited | run-02 (real loop) | gpt-oss | 4760 | 3933 | 0.826 | 0.877 | 0.793 | 0.705 | 0.775 |
|  | S121 | invalid (pre-fix) | run-01 (v1, no tool loop, broken) | Qwen | 4856 | 2805 | 0.578 | 0.58 | 0.077 | 0.719 | 0.629 |
|  | S122 | invalid (pre-fix) | run-01 (v1, no tool loop, broken) | Phi | 4856 | 0 | 0 | 0 | 0 | 0 | 0 |
