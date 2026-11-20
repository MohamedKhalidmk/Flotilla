# Test 04 · Strategy router

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 04 | 2026-11-20 | protocol-v10 | running (fixing labels) | [run-02](runs/run-02/run.json) |

## Question

With one model (Qwen3.8-27B, 4-bit), can a router that picks a **route** per question beat Qwen's best fixed route,
either on accuracy or on compute at nearly the same accuracy?

## Setup

**Routes.** Every route runs through the same Flotilla loop (solver prompt v1, verifier v2 with one retry,
`max_tokens` 32,768). Configs are in [`configs/systems/`](../../configs/systems/).

| Route | Thinking | Tools | Samples |
|---|---|---|---|
| Fast | off | none | 1 |
| Tools | off | sympy, python_exec, constraint_check (native calls) | 1 |
| Deep | full | none | 1 |
| Deep+Tools | full | as Tools | 1 |
| Vote | full | none | 5 at temperature 0.6, majority (public tests on code) |
| Vote+Tools | full | as Tools | 5 |
| Memory, Memory+Deep, Vote+Memory, Deep+Tools+Memory | as named | as named | GRAFT facts from the full T-REx graph first, all on Qwen |

Thinking is switched off through Qwen's chat template (`enable_thinking: false`). With tools off, the prompt says no
tools are available (`prompts/solver.v1.md`, section "No-tool wording"). Memory routes come last, after the GRAFT run
on the full T-REx graph (test 05).

**Labels.** 1,500 questions from the leakage-checked router pool, never the 5% small test, the full benchmarks, router
B's 476 held-out questions or GRAFT's 100 FactConsolidation questions; drawn by
[`flotilla/strategy_items.py`](../../flotilla/strategy_items.py) (seed 20261120: 910 math, 249 science MC,
249 instruction, 92 code). LongMemEval adds long inputs for the Memory routes. Every route answers every question;
correctness, tokens, calls and time are kept per question ([`flotilla/strategy_labels.py`](../../flotilla/strategy_labels.py)).

**Split.** 70% train, 15% dev, 15% held-out, stratified by source and task type. Routers iterate on train and dev only.
Then one evaluation on held-out and one on the 5% small test, both reported even if the router loses.

**Routers.** Every route is tried only on the training questions; on a new question the router picks one route straight
away, which is where the compute saving comes from.

1. Label classifier: ModernBERT-base predicts the cheapest correct route.
2. Success predictor: ModernBERT-base predicts each route's chance of being right; the cheapest route above a
   threshold tuned on dev is picked.
3. bge-small + logistic regression, set up as 2.
4. Nearest neighbours over the training questions.
5. Live RL from the best of 1-4: any route step in any order or stop, sees the verifier's verdict after each step,
   reward +1 if correct minus a time penalty, trained with real Qwen runs on train questions.

## Result

Pilot, 50 pool questions, six routes ([table.csv](table.csv)):

| Route | Accuracy | Output tokens | GPU-s per question | Cheapest correct |
|---|---|---|---|---|
| Fast | [0.74](table.csv) | [2,110](table.csv) | [3.9](table.csv) | [37](table.csv) |
| Tools | [0.82](table.csv) | [2,615](table.csv) | [13.3](table.csv) | [6](table.csv) |
| Deep | [0.84](table.csv) | [6,058](table.csv) | [14.1](table.csv) | [2](table.csv) |
| Deep+Tools | [0.82](table.csv) | [6,291](table.csv) | [17.0](table.csv) | [0](table.csv) |
| Vote | [0.82](table.csv) | [21,821](table.csv) | [17.7](table.csv) | [0](table.csv) |
| Vote+Tools | [0.82](table.csv) | [19,995](table.csv) | [17.1](table.csv) | [0](table.csv) |

Some route is right on [90%](table.csv) of the pilot questions, against [0.84](table.csv) for the best single route.
All six routes have answered the other 1,450 questions ([run-02](runs/run-02/run.json)). The hand check of the failures
found bugs in the verifier's option check and the instruction checker
([failure report](runs/run-02/audit/failure_report.md), pilot: [always wrong](runs/run-01/audit/always_wrong.md)), so
the full labels are fixed and regraded before they are shown here or used for training.
[table.csv](table.csv) · [figure.png](figure.png)

## Decision

Rule, fixed before any result: **keep a router if it is within 1 point of the best fixed route at lower compute,
or more than 1 point better.** Otherwise Flotilla uses the best fixed route for every question. Then the full
benchmarks run once with the final system and once with the best single route on the same questions.

## Revisions

- 2026-11-20: design written; four-route pilot on Nibi.
- 2026-11-20: plan widened to ten routes (combos and Memory); run-01 holds the six-route pilot and its failure audit.
- 2026-11-20: run-02, six routes on 1,450 questions graded; verifier A-to-D option bug fixed (system.py), instruction
  checker bugs found. Labels to be regraded and affected questions rerun.
