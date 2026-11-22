# Test 03 · Router B (which model)

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 03 | 2026-11-20 | protocol-v9 → v10 | done | [run-02](runs/run-02/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| F06 | S119 | Qwen |
| F07 | S120 | gpt-oss |
| F13 | S124 | Router B: ModernBERT-base fine-tune (final epoch, saved) |
| F14 | S125 | Baseline: bge-small + logistic regression |
|  | S121 | Qwen |
|  | S122 | Phi |

## Question

Does a trained router between Qwen and gpt-oss beat Qwen alone by about 1 point or more?

## Setup

Both models answer the leakage-checked router pool (4,760 questions) through the real Flotilla loop. A ModernBERT-base
fine-tune (router B) and a bge-small + logistic regression baseline learn which model to send each question to,
trained on 4,284 and tested once on 476 held-out questions chosen by question id. Config: [config.yaml](config.yaml).

## Result

| System | Held-out accuracy |
|---|---|
| Qwen alone | [0.895](table.csv) |
| gpt-oss alone | [0.853](table.csv) |
| Router B (ModernBERT) | [0.899](table.csv) |
| bge + logistic regression | [0.887](table.csv) |
| Perfect router | [0.941](table.csv) |

Router B adds [+0.004](table.csv) over Qwen alone. [table.csv](table.csv) · [labels.csv](labels.csv) · [figure.png](figure.png)

## Decision

**gpt-oss dropped (protocol-v10).** The router gain is below the 1-point rule. Flotilla runs Qwen alone, and test 04
asks whether choosing a strategy per question helps instead.

## Revisions

- 2026-11-21: **run-01 marked invalid** (setups S121, S122; registry rule for pre-fix runs): one call with tools offered and no tool loop, code graded with fences.
- 2026-11-21: **run-02 marked "scored before the grader fixes, audited"** (user; setups S119, S120, S124, S125): the labels were graded before the A-D option, instruction-checker, float and math-format fixes; run-03's audit rechecked every wrong gpt-oss label (227 lost to bugs) and the gpt-oss drop stands. Rechecking test 03 with the fixed graders stays low priority.
- 2026-11-19: run-01, broken: the label prompt offered tools but no tool loop ran, and code answers kept markdown fences.
  Kept as the record, not used.
- 2026-11-20: run-02, labels through the real loop; router B and the baseline trained and tested once.
