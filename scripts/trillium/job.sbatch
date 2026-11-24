#!/bin/bash
# Generic Trillium GPU job: runs one Flotilla command offline. Submit from trig-login01 with the job's
# working directory on scratch (/project is read-only on Trillium compute nodes):
#   sbatch --gpus-per-node=h100:1 --time=3:00:00 --job-name=q-w4 --chdir=$SCRATCH/flotilla/logs \
#          $PROJECT/flotilla/scripts/trillium/job.sbatch envs/quant/bin/python -m flotilla.core.quantize ...
# First argument: a program in the serving env ("python"), or a path relative to the code dir such as
# envs/quant/bin/python (Trillium submits with --export=NONE, so env vars can't select the env).
# Whole-node GPU jobs must not use -p; the scheduler routes them. Records GPU memory every 30 s.
#SBATCH --account=def-sylu
#SBATCH --nodes=1
#SBATCH --output=%x-%j.out
set -euo pipefail
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla  # Fir has no /project/def-sylu
source "$CODE/scripts/trillium/modules.sh"
export HF_HOME="$SCRATCH/flotilla/hf" HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export FLOTILLA_RUNS="$SCRATCH/flotilla/runs" PYTHONPATH="$CODE" PYTHONUNBUFFERED=1
# $HOME is read-only on Trillium compute nodes too: every cache goes to scratch (FlashInfer wrote to ~/.cache)
C="$SCRATCH/flotilla/cache"
export XDG_CACHE_HOME="$C" VLLM_CACHE_ROOT="$C/vllm" TRITON_CACHE_DIR="$C/triton" TORCHINDUCTOR_CACHE_DIR="$C/inductor" \
       FLASHINFER_WORKSPACE_BASE="$C" CUDA_CACHE_PATH="$C/nv" MPLCONFIGDIR="$C/mpl" HUMMING_CACHE_DIR="$C/humming" \
       TIKTOKEN_ENCODINGS_BASE="$C/tiktoken" TIKTOKEN_RS_CACHE_DIR="$C/tiktoken"
mkdir -p "$FLOTILLA_RUNS" "$C"/{vllm,triton,inductor,nv,mpl,humming}
# Compile caches on node-local disk when the cluster gives one: several jobs compiling into one shared-scratch cache
# at the same moment failed with "Stale file handle" (Nibi, 2026-11-20).
if [[ -n "${SLURM_TMPDIR:-}" && -d "$SLURM_TMPDIR" ]]; then
  export TORCHINDUCTOR_CACHE_DIR="$SLURM_TMPDIR/inductor" TRITON_CACHE_DIR="$SLURM_TMPDIR/triton" \
         HUMMING_CACHE_DIR="$SLURM_TMPDIR/humming"  # two jobs compiling into one shared humming cache crashed (Fir)
  # vLLM, FlashInfer and CUDA JIT caches too (as GRAFT's run_qwen_graft.sbatch): 33 G41 jobs starting together on Fir
  # slices with these on shared scratch all stalled after the model load until the 1 h startup timeout (2026-11-23).
  export VLLM_CACHE_ROOT="$SLURM_TMPDIR/vllm" FLASHINFER_WORKSPACE_BASE="$SLURM_TMPDIR" CUDA_CACHE_PATH="$SLURM_TMPDIR/nv"
  mkdir -p "$SLURM_TMPDIR"/{vllm,nv}
fi
# humming also writes a tmp folder under $HOME (read-only on Trillium compute nodes)
export HUMMING_TMP_DIR="${SLURM_TMPDIR:-$C}/humming-tmp"
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
