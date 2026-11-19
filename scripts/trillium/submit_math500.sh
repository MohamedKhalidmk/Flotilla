#!/usr/bin/env bash
# Submit MATH-500 runs (rule 4.1), one H100 each. Run on trig-login01.
#   bash scripts/trillium/submit_math500.sh <name> <model path or id> [max_tokens] [max_model_len]
set -euo pipefail
NAME=$1; MODEL=$2; MAXTOK=${3:-131072}; MAXLEN=${4:-0}
mkdir -p "$SCRATCH/flotilla/logs"
sbatch --gpus-per-node=h100:1 --time=8:00:00 --job-name="m500-$NAME" --chdir="$SCRATCH/flotilla/logs" \
  /project/def-sylu/khaledmk/flotilla/scripts/trillium/job.sbatch python -m flotilla.eval_math500 \
  --model "$MODEL" --name "math500-$NAME" --max-tokens "$MAXTOK" --max-model-len "$MAXLEN"
