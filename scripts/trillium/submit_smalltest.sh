#!/usr/bin/env bash
# Submit one system configuration's small test as a single job (servers + loop on one node). Run on trig-login01.
#   bash scripts/trillium/submit_smalltest.sh <system name> <gpus> <hours> [extra flotilla.serve args]
set -euo pipefail
SYS=$1; GPUS=$2; HOURS=$3; shift 3
CODE=/project/def-sylu/khaledmk/flotilla
SMOKE="gsm8k/174 math500/test/geometry/248.json aime2026/28 gpqa/recoiTJPGUmzAkief ifeval/1001 ocrbench/35 mmmu/validation_Biology_14 lcb/abc373_g ruler_64k/niah_single_1/2"
sbatch --gpus-per-node=h100:$GPUS --time=$HOURS:00:00 --job-name="st-$SYS" --chdir="$SCRATCH/flotilla/logs" \
  "$CODE/scripts/trillium/job.sbatch" python -m flotilla.serve --system "$CODE/configs/systems/$SYS.json" \
  --servers "$CODE/configs/servers.json" --items-dir "$SCRATCH/flotilla/smalltest" --out "$SCRATCH/flotilla/runs/smalltest-$SYS" \
  --smoke-ids $SMOKE "$@"
