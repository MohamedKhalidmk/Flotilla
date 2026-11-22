---
role: verifier
version: v2
replaces: v1 (2026-11-19, protocol-v2): the retry message now tells the model its previous answer was wrong and gives the verifier's reason; both attempts are logged
used_by: the last step before an answer is returned (ablation: verifier on/off)
output_schema: {"verdict": "accept|reject", "checks": [{"name": string, "passed": boolean, "detail": string}], "reason": string}
---

# Verifier (v2)

Sources: original (docs/reference/REFERENCES.md)

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

## On reject: one retry
The solver gets its original messages plus this user message, then answers again. The second answer is returned whatever its verdict.

### Retry message
Your previous answer was wrong. A checker rejected it.

Previous answer: {previous_answer}
Failed checks: {failed_checks}
Reason: {reason}

Solve the task again from the start, fix the problem above, and end with the same JSON block.

## Logging
Both attempts are recorded in the trace under `verifier.attempts`: for each attempt its number, final answer, verdict, and every check with its detail (including error output such as a failing test or an unparseable answer).
