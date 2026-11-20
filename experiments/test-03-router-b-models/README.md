# Test 03 · Router B (which model)

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 03 | 2026-11-20 | protocol-v9 → v10 | done | [run-02](runs/run-02/run.json) |

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

- 2026-11-19: run-01, broken: the label prompt offered tools but no tool loop ran, and code answers kept markdown fences.
  Kept as the record, not used.
- 2026-11-20: run-02, labels through the real loop; router B and the baseline trained and tested once.
