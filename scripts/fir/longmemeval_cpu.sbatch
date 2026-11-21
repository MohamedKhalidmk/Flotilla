#!/bin/bash
# LongMemEval for the Memory-route labels (flotilla/longmemeval.py): leakage units, leakage check (13-gram + bge-small
# embedding, flotilla/leakage.py), clean items, split, test sample, Qwen prompt-token counts. CPU only, offline.
# Data first, on a Fir login node: raw files in $SCRATCH/flotilla/data/longmemeval/raw (manifest.json there), test sets
# and BAAI/bge-small-en-v1.5 in $SCRATCH/flotilla/hf. Code: a copy of the working tree in $CODE (default below).
#   sbatch --chdir=$SCRATCH/flotilla/logs scripts/fir/longmemeval_cpu.sbatch [all|leakage|tokens]
#SBATCH --account=def-sylu_cpu
#SBATCH --job-name=lme-prep
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=4:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
STEP=${1:-all}
CODE=${LME_CODE:-$SCRATCH/flotilla/lme_code}
ENV=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla/envs/flotilla
source "$CODE/scripts/trillium/modules.sh"
export HF_HOME="$SCRATCH/flotilla/hf" HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$CODE" PYTHONUNBUFFERED=1 OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export XDG_CACHE_HOME="${SLURM_TMPDIR:-$SCRATCH/flotilla/cache}" TOKENIZERS_PARALLELISM=false
PY="$ENV/bin/python"
D=$SCRATCH/flotilla/data/longmemeval
RAW=$D/raw
QWEN=$SCRATCH/flotilla/quant/qwen3.8-27b-w4a16
cd "$CODE"
t() { echo "[job] $(date -Is) $*"; }
t "start on $(hostname), step $STEP"
if [[ $STEP == all || $STEP == leakage ]]; then
  "$PY" -m flotilla.longmemeval units --raw-dir "$RAW" --out "$D/units.jsonl"; t "units done"
  "$PY" -m flotilla.leakage --pool "$D/units.jsonl" --report "$D/leakage_units.json" > "$D/leakage_units.log"; t "leakage done"
  "$PY" -m flotilla.longmemeval build --raw-dir "$RAW" --leakage "$D/leakage_units.json" --out-dir "$D" \
       --report "$CODE/reports/leakage/longmemeval.json"; t "build done"
  "$PY" -m flotilla.longmemeval sample --items "$D/memory_items.jsonl" --out "$CODE/tests/data/longmemeval_sample.jsonl"
fi
if [[ $STEP == all || $STEP == tokens ]]; then
  "$PY" -m flotilla.longmemeval tokens --raw-dir "$RAW" --split "$D/split.json" --tokenizer "$QWEN" \
       --out "$D/prompt_tokens.jsonl" --summary "$D/prompt_tokens_summary.json" --workers $SLURM_CPUS_PER_TASK; t "tokens done"
fi
t "end"
