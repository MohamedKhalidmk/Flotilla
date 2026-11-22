#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=%x-%j.out
# PAID (user-approved 2026-11-22): (1) one Claude Sonnet 5.5 verdict per split Haiku judge group (memory_route
# tiebreak), (2) Claude Haiku 5.5 sub-types of every reasoning_error trace (flotilla.error_subtypes). A cost guard sums
# cost_usd in both usage logs every minute and stops past COST_CAP_USD (default $1). The key comes only from the
# submitting shell's environment. Submitted afterok the fixed Haiku check (GRAFT haiku_replay38).
set -euo pipefail
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs sbatch}"
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
source "$CODE/scripts/trillium/modules.sh"
export PYTHONPATH="$CODE" PYTHONUNBUFFERED=1
PY="$CODE/envs/flotilla/bin/python"
J=$SCRATCH/flotilla/lme/judge
T=$SCRATCH/flotilla/test04-labels
L=$SCRATCH/flotilla/pool_traces
LME=$SCRATCH/flotilla/lme
CAP="${COST_CAP_USD:-1}"
START=$(date +%s)
spent() {
  "$PY" "$CODE/scripts/sum_cost.py" "$START" "$J/haiku-v10-maj3-sonnet/usage.jsonl" "$T/subtypes_maj3/usage.jsonl"
}
guard() {
  local pid=$1
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    S=$(spent)
    echo "[cost guard] $(date +%H:%M) spent \$$S of \$$CAP"
    if awk -v s="$S" -v c="$CAP" 'BEGIN{exit !(s > c)}'; then
      echo "[cost guard] over the cap: stopping"
      pkill -TERM -s "$pid" || true
      exit 3
    fi
  done
}
cd "$CODE"
setsid "$PY" -m flotilla.memory_route tiebreak --items "$SCRATCH/flotilla/data/longmemeval/memory_items.jsonl" \
  --verdicts "$J/haiku-v10-maj3/verdicts.jsonl" --out "$J/haiku-v10-maj3-sonnet" &
P1=$!
guard "$P1"
wait "$P1"
setsid "$PY" -m flotilla.error_subtypes --stages "$T/stages_maj3_pool/stages.jsonl" "$T/stages_maj3_lme/stages.jsonl" \
  --runs $(cat "$SCRATCH/flotilla/subtype_runs.txt") --pool "$L/pool.clean.jsonl" \
  --memory-items "$SCRATCH/flotilla/data/longmemeval/memory_items.jsonl" --graft-cache "$LME/graft_cache" \
  --out "$T/subtypes_maj3" &
P2=$!
guard "$P2"
wait "$P2"
echo "[extras] $(date -Is) finished, spent \$$(spent)"
