#!/usr/bin/env bash
# test-04 route labelling: one 1-GPU job per shard of labelitems_strategy (flotilla/strategy_items.py).
#   bash scripts/nibi/submit_strategy.sh <route> <time> <shard number>...   (Trillium: FLOTILLA_SBATCH=--export=NONE)
# route = fast | tools | deep | vote | deep_tools | vote_tools (configs/systems/qwen_strategy_<route>.json)
# Output: $SCRATCH/flotilla/runs/strategy-labels/<route>/strat_KK/trace.jsonl, graded with flotilla.strategy_labels.
set -euo pipefail
R=$1; TIME=$2; shift 2
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
for K in "$@"; do S=$(printf "${STRAT_PREFIX:-strat}_%02d" "$K")
  sbatch --parsable ${FLOTILLA_SBATCH-$(bash "$CODE/scripts/nibi/sbatch_opts.sh" 1)} --gpus-per-node=h100:1 --time=$TIME \
    --job-name="st4-$R-$S" --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.serve \
    --system "$CODE/configs/systems/qwen_strategy_$R.json" --servers "$CODE/configs/servers.json" \
    --items-dir "$SCRATCH/flotilla/labelitems_strategy" --out "$SCRATCH/flotilla/runs/strategy-labels/$R/$S" --benches "$S"
done
