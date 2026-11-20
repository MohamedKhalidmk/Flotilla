# Test 01 · Quantization

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 01 | 2026-11-19 | protocol-v1 (rule 4.1) | done | [run-01](runs/run-01/run.json) |

## Question

Does 4-bit lose accuracy against 8-bit and 16-bit for the solver models?

## Setup

MATH-500, all 500 questions, 0-shot, greedy, scored with math-verify ([`flotilla/eval_math500.py`](../../flotilla/eval_math500.py)).
Qwen3.8-27B in BF16, FP8 (ours), W4A16 (ours) and RedHat's INT4; Phi-4-reasoning-plus in BF16, FP8 (ours and NVIDIA)
and W4A16 (ours and AMD). Config: [config.yaml](config.yaml).

## Result

| Build | Qwen3.8-27B | Phi-4-reasoning-plus |
|---|---|---|
| 16-bit | [0.978](table.csv) | [0.824](table.csv) |
| 8-bit (ours) | [0.984](table.csv) | [0.820](table.csv) |
| 4-bit (ours) | [0.984](table.csv) | [0.786](table.csv) |

Qwen's 4-bit build ties its 8-bit build. Phi hit the 30,000-token cap on most questions in every build
([379 to 398 of 500](table.csv)). [table.csv](table.csv) · [figure.png](figure.png)

## Decision

Rule 4.1: 4-bit if within 1 point of 8-bit. **Qwen runs 4-bit (W4A16, ours).** Phi was later dropped (protocol-v9).

## Revisions

- 2026-11-19: run-01.
