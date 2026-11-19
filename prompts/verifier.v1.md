---
role: verifier
version: v1
used_by: the last step before an answer is returned (ablation: verifier on/off)
output_schema: {"verdict": "accept|reject", "checks": [{"name": string, "passed": boolean, "detail": string}], "reason": string}
---

# Verifier (v1)

The verifier is **tool-first**: deterministic checks run before any model is asked.

## Deterministic checks (no LLM)
| Task type | Check |
|---|---|
| math | final_answer parses; sympy re-evaluates any expression; numeric answers in the task's required form |
| code | runs against the task's public tests in the sandbox (never hidden tests) |
| science_mc / MMMU | final_answer is one valid option letter |
| instruction | our own constraint checker (written from the task text, not from IFEval's grading code) |
| vision_doc | answer string is non-empty and in the requested format |
| any | JSON block present and parseable; answer within length limit |

## LLM check (only if the deterministic checks pass and the task type has no exact check)
### System
Decide whether the answer below is acceptable for the task. Reject only for a concrete, stated problem.
Return only this JSON:
{"verdict": "accept"|"reject", "checks": [], "reason": "one sentence"}

### User
Task: {task_text}
Answer: {final_answer}

## On reject
The system retries once with the rejection reason appended to the solver prompt; the second answer is returned whatever its verdict, and both are logged.
