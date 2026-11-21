#!/bin/bash
# LongMemEval GPU job (test 04 route labels): optional GRAFT setup, then scripts/trillium/job.sbatch with the command.
# With GRAFT=1 (graph builds, Memory routes): GRAFT's code is copied to node-local disk and its venv unpacked there
# (as GRAFT's scripts/fir/common.sh does), and GRAFT_PYTHON points at a wrapper that runs that venv with GRAFT's own
# modules (StdEnv/2023, python/3.12, arrow/25.0.0), so the bridge never sees Flotilla's python/3.14 modules.
#   sbatch --account=def-sylu_gpu --gpus-per-node=h100:1 ... --export=ALL,GRAFT=1 scripts/fir/lme_job.sbatch python -m ...
#SBATCH --nodes=1
#SBATCH --output=%x-%j.out
set -euo pipefail
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
SGAR=${GRAFT_SRC:-$(readlink -f "$HOME/projects/def-sylu")/khaledmk/SGAR}
SGAR_SCRATCH=$HOME/scratch/sgar
export FLOTILLA_GRAFT_CACHE=${FLOTILLA_GRAFT_CACHE:-$SCRATCH/flotilla/lme/graft_cache}
if [[ "${GRAFT:-0}" == 1 ]]; then
  t0=$(date +%s); L="$SLURM_TMPDIR/SGAR"; mkdir -p "$L"
  (cd "$SGAR" && tar cf - --warning=no-file-changed --exclude='./*.out' --exclude=./.venv --exclude=./envs \
     --exclude=./results --exclude=./data --exclude=./.git . || [[ $? == 1 ]]) | tar xf - -C "$L"
  for d in results data envs; do [[ -e "$SGAR/$d" ]] && ln -sfn "$SGAR/$d" "$L/$d"; done
  tar xf "$SGAR_SCRATCH/venv.tar" -C "$L"
  # GRAFT's module environment, captured in a subshell (readonly variables left out)
  ( module --force purge >/dev/null 2>&1 || true
    module load StdEnv/2023 gcc python/3.12 arrow/25.0.0
    export -p | grep -v -E '^declare -[a-zA-Z]*r' > "$SLURM_TMPDIR/graft.env"
    # GRAFT's gateway needs openai for its local vLLM backend; the packed venv lacks it (Qwen job 28252727 failed on it)
    "$L/.venv/bin/python" -c "import openai" 2>/dev/null || "$L/.venv/bin/python" -m pip install -q --no-index openai \
      || echo "WARNING: openai not installable into GRAFT's venv; GRAFT on Qwen will fail" )
  cat > "$SLURM_TMPDIR/graft_python" <<WRAP
#!/bin/bash
P="\${PYTHONPATH:-}"; source "$SLURM_TMPDIR/graft.env"; export PYTHONPATH="\$P"
export HF_HOME="$SCRATCH/flotilla/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
exec "$L/.venv/bin/python" "\$@"
WRAP
  chmod +x "$SLURM_TMPDIR/graft_python"
  export GRAFT_REPO="$L" GRAFT_PYTHON="$SLURM_TMPDIR/graft_python" GRAFT_COMMIT="${GRAFT_COMMIT:-unknown}"
  (cd "$L" && PYTHONPATH="$L" "$GRAFT_PYTHON" -c "import torch, openai, my_method.agent, eval.methods, baselines.claude_gateway.server; print('[graft] imports ok, cuda', torch.cuda.is_available())") || { echo "[graft] env broken"; exit 3; }
  echo "[graft] code and venv on $SLURM_TMPDIR in $(( $(date +%s) - t0 )) s; commit $GRAFT_COMMIT; cache $FLOTILLA_GRAFT_CACHE"
fi
exec bash "$CODE/scripts/trillium/job.sbatch" "$@"
