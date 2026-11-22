#!/usr/bin/env bash
# test-04 supervised routers (flotilla/strategy_router.py) on Fir: one GPU job for the two ModernBERT routers
# (def-sylu_gpu), one CPU job for bge-small + logistic regression and kNN (def-sylu_cpu), then a GPU job that evaluates
# all four on dev and writes the table (afterok both). Held-out is never evaluated here: that is one later run of
#   ... python -m flotilla.strategy_router evaluate --labels L --items I --out OUT --held-out
#   bash scripts/fir/submit_strategy_router.sh dry-run|train <out dir under $SCRATCH/flotilla/runs/strategy-router>
# Inputs: LABELS (graded folder: per_question.jsonl, split.json, summary.json) and ITEMS (question shards, glob kept
# quoted so Python expands it). Models come from the shared offline HF cache ($SCRATCH/flotilla/hf: ModernBERT-base,
# bge-small-en-v1.5). Times = measured runtime + ~50% (below); override with GPU_TIME, CPU_TIME, EVAL_TIME.
set -euo pipefail
MODE=${1:?dry-run or train}; NAME=${2:?out dir name}
case $MODE in dry-run|train) ;; *) echo "mode must be dry-run or train" >&2; exit 2 ;; esac
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
LABELS=${LABELS:-$SCRATCH/flotilla/test04-labels/run-03}
ITEMS=${ITEMS:-$SCRATCH/flotilla/labelitems_strategy/strat12_*.jsonl}
OUT=$SCRATCH/flotilla/runs/strategy-router/$NAME
# Measured in the dry run (2026-11-21, jobs 4864960-2): ModernBERT 0.14-0.25 s per step (bs 16, max_len 1024, H100),
# GPU job 48 s in all; bge + LR + kNN on the full splits 62 s (CPU); evaluate 14.5 min on 8 CPUs, now on a GPU.
# Real training: 2 routers x 3 epochs x 64 steps ~ 1.5-2.5 min of steps + loading, about 4 min; +50% and startup.
GPU_TIME=${GPU_TIME:-0:10:00}; CPU_TIME=${CPU_TIME:-0:05:00}; EVAL_TIME=${EVAL_TIME:-0:10:00}
mkdir -p "$OUT" "$SCRATCH/flotilla/logs"
read -ra ITEM_GLOBS <<< "$ITEMS"  # several globs, space-separated (pool shards and LongMemEval items for run-04-lme)
ARGS=(--labels "$LABELS" --items "${ITEM_GLOBS[@]}" --out "$OUT")
read -ra TRAIN_ARGS <<< "${TRAIN_ARGS:-}"  # training only, e.g. TRAIN_ARGS="--train-frac 0.5 --frac-seed 20261121" (learning curve)
JOB="$CODE/scripts/trillium/job.sbatch"
G=$(sbatch --parsable --account=def-sylu_gpu --gpus-per-node=h100:1 --cpus-per-task=8 --mem=64G --time="$GPU_TIME" \
  --job-name="sr-$MODE-mb" --chdir="$SCRATCH/flotilla/logs" "$JOB" python -m flotilla.strategy_router "$MODE" "${ARGS[@]}" ${TRAIN_ARGS[@]+"${TRAIN_ARGS[@]}"} \
  --routers label success)
C=$(sbatch --parsable --account=def-sylu_cpu --cpus-per-task=8 --mem=32G --time="$CPU_TIME" \
  --job-name="sr-$MODE-emb" --chdir="$SCRATCH/flotilla/logs" "$JOB" python -m flotilla.strategy_router "$MODE" "${ARGS[@]}" ${TRAIN_ARGS[@]+"${TRAIN_ARGS[@]}"} \
  --routers bge_lr knn --device cpu)
# evaluate on a GPU: ModernBERT inference over 217 dev questions took over 10 min on 8 CPUs (dry run job 4864962)
E=$(sbatch --parsable --account=def-sylu_gpu --gpus-per-node=h100:1 --cpus-per-task=8 --mem=64G --time="$EVAL_TIME" \
  --dependency="afterok:$G:$C" --job-name="sr-$MODE-eval" --chdir="$SCRATCH/flotilla/logs" "$JOB" \
  python -m flotilla.strategy_router evaluate "${ARGS[@]}" ${TRAIN_ARGS[@]+"${TRAIN_ARGS[@]}"})
echo "gpu $G  cpu $C  eval $E  -> $OUT"
