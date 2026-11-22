#!/usr/bin/env bash
# LLM-verifier test (F33/F34 against F15/F17), LongMemEval dev items only (76), free on Qwen, all arms the same day.
#   bash scripts/fir/submit_llm_verifier.sh <arm> <time> <repeat> [begin]   # arm: fast fast_llmv deep deep_llmv
# Items: $LME/runitems/base/lme_dev.jsonl (bench lme_dev, built from data/longmemeval/split.json's dev ids).
# Output: $LME/runs/<arm>/lme_dev_r<repeat><SUFFIX>/. LME defaults to $SCRATCH/flotilla/lme_llmv, so the run-04-lme
# label folders are never touched. GPU and EXTRA_SBATCH as scripts/fir/submit_longmemeval.sh (Nibi: a 3g.40gb slice).
set -euo pipefail
ARM=$1; TIME=$2; REP=$3; BEGIN=${4:-now}
CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
LME=${LME:-$SCRATCH/flotilla/lme_llmv}
mkdir -p "$LME/logs" "$LME/runs/$ARM"
sbatch --parsable --account=def-sylu_gpu --gpus-per-node=${GPU:-h100:1} --cpus-per-task=${CPUS:-12} --mem=${MEM:-200G} \
  --chdir="$LME/logs" ${EXTRA_SBATCH:-} --time=$TIME --begin=$BEGIN --job-name="llmv-$ARM-r$REP${SUFFIX:-}" \
  "$CODE/scripts/fir/lme_job.sbatch" python -m flotilla.serve \
  --system "$CODE/configs/systems/qwen_strategy_$ARM.json" --servers "$CODE/configs/servers_longmemeval.json" \
  --items-dir "$LME/runitems/base" --out "$LME/runs/$ARM/lme_dev_r$REP${SUFFIX:-}" --benches lme_dev --concurrency ${CONC:-6}
