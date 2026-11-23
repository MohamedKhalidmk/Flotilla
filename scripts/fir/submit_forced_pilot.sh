#!/usr/bin/env bash
# Pilot of the forced-tool and self-check routes (S170), after the toy gate (S169) passed; Fir or Nibi (twins).
#   bash scripts/fir/submit_forced_pilot.sh <route> <pool|lme> <time>
# route = forced_code | forced_sympy | forced_rules | self_check | fast | tools | deep | deep_tools
# Items: $SCRATCH/flotilla/forced_tools/items/pilot_pool.jsonl (153 dev pool questions; instruction ones carry
# RLVR-IFeval's ground_truth) and pilot_lme.jsonl (40 LongMemEval dev questions, whole history, long-context server).
# Output: $SCRATCH/flotilla/forced_tools/pilot/<route>/<part>/trace.jsonl. All routes the same day.
set -euo pipefail
R=$1; PART=$2; TIME=$3
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
F=$SCRATCH/flotilla/forced_tools
if [[ $PART == lme ]]; then SERVERS=$CODE/configs/servers_longmemeval.json; BENCH=pilot_lme; CONC=5
else SERVERS=$CODE/configs/servers.json; BENCH=pilot_pool; CONC=32; fi
mkdir -p "$F/logs" "$F/pilot/$R"
# PILOT_GPU=slice runs on a 3g.40gb MIG slice (they start within minutes; whole H100s queued for a day, 2026-11-23)
if [[ ${PILOT_GPU:-h100} == slice ]]; then RES="--account=def-sylu_gpu --gpus-per-node=nvidia_h100_80gb_hbm3_3g.40gb:1 --cpus-per-task=6 --mem=60G"
else RES="$(bash "$CODE/scripts/nibi/sbatch_opts.sh" 1) --gpus-per-node=h100:1 --cpus-per-task=12 --mem=200G"; fi
sbatch --parsable $RES \
  --time=$TIME --job-name="pilot-$R-$PART" --chdir="$F/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.serve \
  --system "$CODE/configs/systems/qwen_strategy_$R.json" --servers "$SERVERS" --items-dir "$F/items" \
  --out "$F/pilot/$R/$PART" --benches "$BENCH" --concurrency $CONC
