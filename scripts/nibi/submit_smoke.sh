#!/usr/bin/env bash
# Smoke-only check of one 1-GPU system: serve it, run the given items, stop. Prints the job id.
#   bash scripts/nibi/submit_smoke.sh <system> <time> <id>...   (Trillium: FLOTILLA_SBATCH=--export=NONE)
set -euo pipefail
SYS=$1; TIME=$2; shift 2
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
sbatch --parsable ${FLOTILLA_SBATCH-$(bash "$CODE/scripts/nibi/sbatch_opts.sh" 1)} --gpus-per-node=h100:1 --time=$TIME \
  --job-name="smoke-$SYS" --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.core.serve \
  --system "$CODE/configs/systems/$SYS.json" --servers "$CODE/configs/servers.json" --items-dir "$SCRATCH/flotilla/smalltest" \
  --out "$SCRATCH/flotilla/runs/smoke-$SYS-$(date +%H%M%S)" --smoke-only --smoke-ids "$@"
