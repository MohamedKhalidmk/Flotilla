# Do more labels help the routers? (test 04, planned 2026-11-21, not run)

> IDs ([registry](../reference/REGISTRY.md), 2026-11-21): the four routers trained on run-04-lme get new IDs from F29 (each fraction and draw is a setup, from S147); the routes they choose between are F06 and F15-F23.

Idea from the planning chat, approved by the user as a plan only: run it once the four supervised routers have trained
on all ten routes (`run-04-lme`), not before.

## Question

Is the supervised routers' dev accuracy still rising when they see the whole train split? If yes, more labelled
questions are worth their GPU time; if it has flattened, they are not.

## Setup

- **Labels:** `run-04-lme` (pool run-03 plus LongMemEval with all ten routes), the same split.json as the real training.
- **Subsets:** 50%, 75% and 100% of the train split. Nested (the 50% set is inside the 75% set), drawn stratified by
  (benchmark source, task type) so LongMemEval and every pool task type keep their share, seeded. Three draws
  (seeds 20261121, +1, +2) for 50% and 75%, so the repeat spread is known; 100% is the real training run.
- **Same everything else:** the same dev set, routers (label classifier, success predictor, bge + LR, kNN),
  hyperparameters, epochs and the 0.5-point tuning margin. Dev only; held-out is never read here.
- **Reported:** per router and fraction, dev accuracy (mean and spread over draws), its gap to Vote, and mean GPU-seconds
  per question of the picked routes, in `experiments/test-04-strategy-router/runs/run-NN/` with table and figure.

## Code needed (small)

`flotilla/routers/strategy_router.py`: a `--train-frac F --frac-seed S` option that keeps a nested, stratified fraction of the
train ids before training, recorded in the run's config; a unit test that the subsets are nested, stratified and
seed-stable. `scripts/fir/submit_strategy_router.sh`: pass the two options through and name the out dir by fraction and
seed.

## Cost

Training measured in the dry run: about 4 minutes for the two ModernBERT routers on one H100, about 1 minute for bge +
LR and kNN on CPU, about 10 minutes to evaluate. Seven training runs (2 fractions x 3 draws, plus 100%), all free.

## Reading the result (set by the user 2026-11-21, before any result)

"Still climbing" = the best router's dev accuracy at 100% beats its mean at 75% by more than the spread (max minus min)
between the three 75% draws. Only then the next step below; otherwise no new labels.

## If still climbing: about 1,000 harder pool questions

- **Sources, first from the clean pool's unlabelled part** (4,760 clean questions, 1,500 labelled, router B's held-out
  excluded as before): MATH level 5 and AIME 1983-2024 for top-level maths, MMLU-Pro's hardest STEM categories for
  science MC, LiveCodeBench problems before the test window (2024-08-01) at hard difficulty for code. If those run
  short, new sources need the same rules as the pool (disjoint from every test set by split, year or release date) and
  the full leakage check (13-gram and embedding) before any run; GPQA, AIME 2025/2026 and LiveCodeBench's test window
  stay out.
- **"Harder"**, chosen before labelling: by source difficulty tags (MATH level, LCB difficulty, MMLU-Pro category), not
  by Qwen's answers, so the draw does not peek at labels.
- **Labelled on all six base routes** through the same loop and graders as run-03 (the Memory routes stay unavailable
  on pool questions). The new questions join train only; dev and held-out stay as they are, so the curve and the final
  check stay comparable.
- **Cost:** run-03 used about 62.6 GPU-seconds per question across the six routes; harder questions think longer, so
  about 2 to 3 times that: roughly 35 to 50 H100-hours, free, on 3g.40gb slices and full H100s as twins.
- Then retrain once on the larger train split and compare on the same dev set.
