#!/bin/bash
# Generic Trillium GPU job: runs one Flotilla command offline. Submit from trig-login01 with the job's
# working directory on scratch (/project is read-only on Trillium compute nodes):
#   sbatch --gpus-per-node=h100:1 --time=3:00:00 --job-name=q-w4 --chdir=$SCRATCH/flotilla/logs \
#          $PROJECT/flotilla/scripts/trillium/job.sbatch envs/quant/bin/python -m flotilla.quantize ...
# First argument: a program in the serving env ("python"), or a path relative to the code dir such as
# envs/quant/bin/python (Trillium submits with --export=NONE, so env vars can't select the env).
# Whole-node GPU jobs must not use -p; the scheduler routes them. Records GPU memory every 30 s.
#SBATCH --account=def-sylu
#SBATCH --nodes=1
#SBATCH --output=%x-%j.out
set -euo pipefail
CODE=/project/def-sylu/khaledmk/flotilla
source "$CODE/scripts/trillium/modules.sh"
export HF_HOME="$SCRATCH/flotilla/hf" HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export FLOTILLA_RUNS="$SCRATCH/flotilla/runs" PYTHONPATH="$CODE" PYTHONUNBUFFERED=1
# $HOME is read-only on Trillium compute nodes too: every cache goes to scratch (FlashInfer wrote to ~/.cache)
C="$SCRATCH/flotilla/cache"
export XDG_CACHE_HOME="$C" VLLM_CACHE_ROOT="$C/vllm" TRITON_CACHE_DIR="$C/triton" TORCHINDUCTOR_CACHE_DIR="$C/inductor" \
       FLASHINFER_WORKSPACE_BASE="$C" CUDA_CACHE_PATH="$C/nv" MPLCONFIGDIR="$C/mpl"
mkdir -p "$FLOTILLA_RUNS" "$C"/{vllm,triton,inductor,nv,mpl}
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader -l 30 > "gpu-mem-$SLURM_JOB_ID.csv" &
MON=$!
echo "[job] $(date -Is) start on $(hostname): $*"
if [[ "$1" == */* ]]; then PROG="$CODE/$1"; else PROG="$CODE/envs/flotilla/bin/$1"; fi
set +e
"$PROG" "${@:2}"
rc=$?
set -e
kill $MON 2>/dev/null || true
echo "[job] $(date -Is) end rc=$rc; peak GPU MiB: $(cut -d, -f2 gpu-mem-$SLURM_JOB_ID.csv | tr -dc '0-9\n' | sort -n | tail -1)"
exit $rc
