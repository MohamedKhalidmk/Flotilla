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
# Keep only the verdicts of the chosen folders: the judge grades every folder with a trace.jsonl, including a timed-out
# first attempt with part of a shard (vote_memory/lmem_16, 22 answers, 2026-11-21), and verdicts are keyed by
# (item, route), so a stray verdict could replace the chosen folder's. A verdict is kept when its answer is the chosen
# folder's final answer for that item; every chosen answer must have exactly one kept verdict.
VS=$LME/judge/$JUDGE/verdicts.selected.jsonl
python3 - "$V" "$VS" "${ARGS[@]}" <<'PY'
import json, sys
src, dst, pairs = sys.argv[1], sys.argv[2], sys.argv[3:]
want = {}
for kv in pairs:
    route, d = kv.split("=", 1)
    for line in open(f"{d}/trace.jsonl"):
        t = json.loads(line)
        want[(t["item_id"], route)] = t.get("final_answer")
kept, n_in = {}, 0
for line in open(src):
    v = json.loads(line); n_in += 1
    k = (v["item_id"], v["route"])
    if k in want and v.get("answer") == want[k] and k not in kept:
        kept[k] = line
missing = [k for k in want if k not in kept]
if missing:
    sys.exit(f"{len(missing)} chosen answers have no matching verdict, e.g. {missing[:3]}")
open(dst, "w").writelines(kept.values())
print(f"verdicts: {n_in} in, {len(kept)} kept (one per chosen answer), {n_in - len(kept)} dropped")
PY
V=$VS
OUT=$SCRATCH/flotilla/test04-labels/$NAME
[[ -e $OUT ]] && { echo "$OUT exists: never overwrite a label set"; exit 4; }
echo "${#ARGS[@]} run folders (10 routes x 20 shards)"
sbatch --parsable --account=def-sylu_cpu --cpus-per-task=32 --mem=64G --time=${TIME:-1:00:00} --job-name="lme-merge-$NAME" \
  --chdir="$SCRATCH/flotilla/logs" "$CODE/scripts/trillium/job.sbatch" python -m flotilla.routers.strategy_labels \
  --pool-labels "$SCRATCH/flotilla/test04-labels/run-03" --memory-items "$DATA/memory_items.jsonl" --verdicts "$V" \
  --memory-split "$DATA/split.json" --runs "${ARGS[@]}" --build-runs "$LME"/runs/prepare/lmem_* \
  --graft-cache "$LME/graft_cache" --out "$OUT" --workers 32
