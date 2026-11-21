#!/usr/bin/env bash
# Router labels through the Flotilla loop: one 1-GPU job per label shard (flotilla/label_loop.py make-items).
#   bash scripts/nibi/submit_labels.sh <system> <time> <shard number>...   (Trillium: FLOTILLA_SBATCH=--export=NONE)
# Output: $SCRATCH/flotilla/runs/labels-<system>/label_XX/trace.jsonl, graded later with label_loop score.
set -euo pipefail
SYS=$1; TIME=$2; shift 2
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
for K in "$@"; do S=$(printf "label_%02d" "$K")
  sbatch --parsable ${FLOTILLA_SBATCH-$(bash "$CODE/scripts/nibi/sbatch_opts.sh" 1)} --gpus-per-node=h100:1 --time=$TIME \
    --job-name="lbl-$SYS-$S" --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.serve \
    --system "$CODE/configs/systems/$SYS.json" --servers "$CODE/configs/servers.json" --items-dir "$SCRATCH/flotilla/labelitems" \
    --out "$SCRATCH/flotilla/runs/labels-$SYS/$S" --benches "$S"
done
