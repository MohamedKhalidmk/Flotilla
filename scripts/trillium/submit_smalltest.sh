#!/usr/bin/env bash
# Submit one system configuration's small test as a single job (servers + loop on one node). Run on trig-login01.
#   bash scripts/trillium/submit_smalltest.sh <system name> <gpus> <time> [extra flotilla.core.serve args]
# Other clusters: put their extra sbatch options in FLOTILLA_SBATCH (Nibi: --cpus-per-task and --mem, see scripts/nibi/sbatch_opts.sh).
set -euo pipefail
SYS=$1; GPUS=$2; TIME=$3; shift 3  # Slurm time, e.g. 2:30:00 (measured runtime + about 50%)
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla  # Fir has no /project/def-sylu
SMOKE="gsm8k/174 math500/test/geometry/248.json aime2026/28 gpqa/recoiTJPGUmzAkief ifeval/1001 ocrbench/35 mmmu/validation_Biology_14 lcb/abc373_g ruler_64k/niah_single_1/2"
sbatch ${FLOTILLA_SBATCH:-} --gpus-per-node=h100:$GPUS --time=$TIME --job-name="st-$SYS" --chdir="$SCRATCH/flotilla/logs" \
  "$CODE/scripts/trillium/job.sbatch" python -m flotilla.core.serve --system "$CODE/configs/systems/$SYS.json" \
  --servers "$CODE/configs/servers.json" --items-dir "$SCRATCH/flotilla/smalltest" --out "$SCRATCH/flotilla/runs/smalltest-$SYS" \
  --smoke-ids $SMOKE "$@"
