#!/usr/bin/env bash
# Small test for one 1-GPU system, split into one job per benchmark group (Nibi starts 1-GPU jobs at once).
# Each job serves the model, runs its group's smoke items first (stops if any fails), then the group's items.
#   bash scripts/nibi/submit_groups.sh <system> <time> <group>...   groups: math mixed vision ruler
# Trillium: FLOTILLA_SBATCH="" (whole-node defaults). Output: $SCRATCH/flotilla/runs/smalltest-<system>-<group>/ (scored per group, merged by flotilla.core.scoring --run ...).
set -euo pipefail
SYS=$1; TIME=$2; shift 2  # Slurm time, e.g. 1:15:00 (measured runtime + about 50%)
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla  # Fir has no /project/def-sylu
for G in "$@"; do
  case $G in
    math)   B="gsm8k math500 aime2025 aime2026"; S="gsm8k/174 math500/test/geometry/248.json aime2026/28" ;;
    mixed)  B="gpqa ifeval lcb";                 S="gpqa/recoiTJPGUmzAkief ifeval/1001 lcb/abc373_g" ;;
    vision) B="mmmu ocrbench";                   S="mmmu/validation_Biology_14 ocrbench/35" ;;
    ruler)  B="ruler_32k ruler_64k";             S="ruler_64k/niah_single_1/2" ;;
    *) echo "unknown group $G"; exit 1 ;;
  esac
  sbatch ${FLOTILLA_SBATCH-$(bash "$CODE/scripts/nibi/sbatch_opts.sh" 1)} --gpus-per-node=h100:1 --time=$TIME --job-name="st-$SYS-$G" \
    --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.core.serve \
    --system "$CODE/configs/systems/$SYS.json" --servers "$CODE/configs/servers.json" --items-dir "$SCRATCH/flotilla/smalltest" \
    --out "$SCRATCH/flotilla/runs/smalltest-$SYS-$G" --benches $B --smoke-ids $S
done
