# Test 06 · LLM verifier

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 06 | 2026-11-22 | protocol-v10 | done: F33 and F34 dropped (user, 2026-11-22) | [run-01](runs/run-01/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md).

| Candidate | Setup | Row in this test |
|---|---|---|
| F15 | S159 | Fast (baseline: exact checks only) |
| F33 | S160 | Fast + LLM check |
| F17 | S161 | Deep (baseline: exact checks only) |
| F34 | S162 | Deep + LLM check |

## Question

Verifier v2 has an LLM check for task types with no exact check, but the loop never ran it: free-text answers (such
as LongMemEval's) were accepted with no check at all. Does running it, with Qwen as the checker, improve accuracy
enough to pay for its compute, without turning right answers wrong?

## Setup

- **Items:** LongMemEval dev only, 76 questions (the router split's dev ids, `data/longmemeval/split.json`; train and
  held-out untouched). Whole history in the prompt, as test 04's base routes (`configs/servers_longmemeval.json`).
- **Arms:** Fast and Deep, each with and without the LLM check (`llm_verify` in `configs/systems/qwen_strategy_*_llmv.json`).
  Everything else as test 04: solver prompt v1, verifier v2, temperature 0 for one sample.
- **The check** (`flotilla/core/system.py`, `llm_check`): runs only when the exact checks pass and the task type has none.
  Qwen W4A16 on the solver's own server, thinking off, temperature 0, at most 1,024 tokens, with verifier v2's
  prompt (`prompts/verifier.v2.md`, "LLM check"): the full task text (history and question) and the answer. A reject
  gets the existing one retry (told it was wrong and why); the retry's answer is final and is not checked again. A
  checker reply with no verdict accepts.
- **Repeats:** 3 per arm, all 12 runs submitted together the same day (Fir H100 twinned with Nibi 3g.40gb slices;
  the later twin cancelled). Script: `scripts/fir/submit_llm_verifier.sh`; output `$SCRATCH/flotilla/lme_llmv/runs/<arm>/lme_dev_r<k>`.
- **Scoring:** Claude Haiku 5.5 with LongMemEval's official judge prompts, as test 04's labels, after the fixed Haiku
  check. Both the final answer and, where the check rejected, the first answer are judged, so each retry is a
  right-to-wrong, wrong-to-right, or no-change flip.
- **Reported:** accuracy per arm (mean and spread over repeats); reject rate; flips; extra GPU-seconds (checker and
  retry calls' time over the arm's solver time, from the traces).

## Decision

Keep rule (user, set 2026-11-22, before any result): keep the LLM check only if it beats its baseline by more than
the repeat spread, without turning more right answers wrong than it fixes. Otherwise drop it and log why. Labels
(test 04) are not touched until the user decides.

Result (run-01): both fail. Decision (user, 2026-11-22): F33 and F34 dropped; the LLM check stays off. Reason: each
scores below its baseline by more than the repeat spread (Fast 76.3% against 81.1%, Deep 84.2% against 92.5%) and its
retries turn 3-10 times more right answers wrong than they fix (18 against 6, 21 against 2), at about twice the GPU time.

## Revisions

- 2026-11-22: run-01 submitted.
- 2026-11-22: run-01 scored ([table](runs/run-01/table.md)): Fast 81.1% against 76.3% with the check, Deep 92.5% against
  84.2%; the retries turn 18 and 21 right answers wrong while fixing 6 and 2. Both fail the keep rule.
