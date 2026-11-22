#!/usr/bin/env bash
# Supersede check on chat histories (flotilla/supersede_check.py): build GRAFT graphs for the toy histories
# (tests/data/supersede_toy.jsonl) with a writer config. Free (Qwen). Then, on a login node (CPU, seconds):
#   python -m flotilla.supersede_check --items $OUT/toy.jsonl --cache $OUT/cache_<name> --out $OUT/report_<name>.json
#   bash scripts/fir/submit_supersede_check.sh <system.json> <name> [time]
# Example: bash scripts/fir/submit_supersede_check.sh $SCRATCH/flotilla/lme/devv2/system_g41.json g41
# Output: $SCRATCH/flotilla/lme/supersede/cache_<name>. GPU and EXTRA_SBATCH as
# scripts/fir/submit_longmemeval.sh.
set -euo pipefail
SYS=$1; NAME=$2; TIME=${3:-0:45:00}
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
OUT=$SCRATCH/flotilla/lme/supersede
mkdir -p "$OUT/logs"
cp "$CODE/tests/data/supersede_toy.jsonl" "$OUT/toy.jsonl"
sbatch --parsable --account=def-sylu_gpu --gpus-per-node=${GPU:-h100:1} --cpus-per-task=${CPUS:-12} --mem=${MEM:-100G} \
  --chdir="$OUT/logs" ${EXTRA_SBATCH:-} --time=$TIME --job-name="supersede-$NAME${SUFFIX:-}" \
  --export=ALL,GRAFT=1,GRAFT_COMMIT=${GRAFT_COMMIT:-unknown} \
  "$CODE/scripts/fir/lme_job.sbatch" python -m flotilla.serve --system "$SYS" \
  --servers "$CODE/configs/servers_longmemeval_memory.json" --out "$OUT/prep_$NAME${SUFFIX:-}" \
  --exec "python -m flotilla.memory_route prepare --items $OUT/toy.jsonl --system $SYS --url {url} --model {model} --cache $OUT/cache_$NAME${SUFFIX:-} --batch-size 4"
