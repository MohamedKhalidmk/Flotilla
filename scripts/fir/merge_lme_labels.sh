#!/usr/bin/env bash
# test-04: merge the LongMemEval route labels into the pool labels (run-03) as a new label set, on a Fir CPU node.
#   bash scripts/fir/merge_lme_labels.sh <judge name> [OUT name, default run-04-lme]
# Takes, per route and shard, the one run folder under $LME/runs/<route>/ whose trace.jsonl has all 25 items (a
# retried shard's _a2 or _n2 folder when the first attempt has none), and refuses to submit if any shard is missing
# or has two complete folders. Verdicts come from $LME/judge/<judge name>/verdicts.jsonl (Haiku judge).
set -euo pipefail
JUDGE=${1:?judge name}; NAME=${2:-run-04-lme}
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
LME=${LME:-$SCRATCH/flotilla/lme}
DATA=$SCRATCH/flotilla/data/longmemeval
V=$LME/judge/$JUDGE/verdicts.jsonl
[[ -s $V ]] || { echo "no verdicts at $V"; exit 2; }
ARGS=()
for R in fast tools deep deep_tools vote vote_tools memory memory_deep vote_memory deep_tools_memory; do
  P=$([[ $R == *memory* ]] && echo lmem || echo lme)
  for K in $(seq -w 0 19); do
    found=()
    for d in "$LME/runs/$R/${P}_$K"*; do
      [[ -f $d/trace.jsonl && $(wc -l < "$d/trace.jsonl") -eq 25 ]] && found+=("$d")
    done
    [[ ${#found[@]} -eq 1 ]] || { echo "route $R shard $K: ${#found[@]} complete folders (${found[*]:-none})"; exit 3; }
    ARGS+=("$R=${found[0]}")
  done
done
OUT=$SCRATCH/flotilla/test04-labels/$NAME
[[ -e $OUT ]] && { echo "$OUT exists: never overwrite a label set"; exit 4; }
echo "${#ARGS[@]} run folders (10 routes x 20 shards)"
sbatch --parsable --account=def-sylu_cpu --cpus-per-task=32 --mem=64G --time=${TIME:-1:00:00} --job-name="lme-merge-$NAME" \
  --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.strategy_labels \
  --pool-labels "$SCRATCH/flotilla/test04-labels/run-03" --memory-items "$DATA/memory_items.jsonl" --verdicts "$V" \
  --memory-split "$DATA/split.json" --runs "${ARGS[@]}" --build-runs "$LME"/runs/prepare/lmem_* \
  --graft-cache "$LME/graft_cache" --out "$OUT" --workers 32
