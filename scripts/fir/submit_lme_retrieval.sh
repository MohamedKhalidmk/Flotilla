#!/usr/bin/env bash
# LongMemEval dev retrieval comparison (user, 2026-11-22): five GRAFT retrieval rules on the G41 graphs, Memory route
# (base route Fast), answered by Qwen, free. Configs: configs/systems/lme_retrieval/{f50,f100,f200,g39,g40}.json.
#   bash scripts/fir/submit_lme_retrieval.sh <variant> <repeat> <time> [dependency]
# Items: $D/items/lmedev.jsonl (the 76 dev histories). Graphs and retrieval cache: $D/cache_g41_fix (reused, never
# rebuilt: the configs carry the build's writer settings). Output: $D/ret/<variant>/r<repeat>/ (trace.jsonl, compute.json).
# Repeat 0 of a variant fills the retrieval cache; later repeats depend on it (afterok) so two jobs never write it at once.
set -euo pipefail
V=$1; R=$2; TIME=$3; DEP=${4:-}
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
D=$SCRATCH/flotilla/lme/devv2
mkdir -p "$D/ret/$V" "$D/logs"
sbatch --parsable --account=def-sylu_gpu --gpus-per-node=${GPU:-h100:1} --cpus-per-task=12 --mem=100G --chdir="$D/logs" \
  --time=$TIME ${DEP:+--dependency=afterok:$DEP} --job-name="lmeret-$V-r$R" \
  --export=ALL,GRAFT=1,GRAFT_COMMIT=${GRAFT_COMMIT:-unknown},FLOTILLA_GRAFT_CACHE=$D/cache_g41_fix \
  "$CODE/scripts/fir/lme_job.sbatch" python -m flotilla.serve --system "$CODE/configs/systems/lme_retrieval/$V.json" \
  --servers "$CODE/configs/servers_longmemeval_memory.json" --items-dir "$D/items" --benches lmedev \
  --out "$D/ret/$V/r$R" --concurrency 32
