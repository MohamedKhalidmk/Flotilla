#!/usr/bin/env bash
# test-04 router 5, live RL over route steps (flotilla/rl_router.py), on Fir.
#   bash scripts/fir/submit_rl_router.sh dry-run  <name>   # CPU job: fake Qwen on 20 train questions + the GPU-hour estimate
#   bash scripts/fir/submit_rl_router.sh train    <name>   # priors (GPU, short) -> CHAIN training jobs (resume) -> dev eval
#   bash scripts/fir/submit_rl_router.sh evaluate <name>   # dev evaluation of <name>'s policy.npz
# Held-out is never run here: once, at the end, by hand:
#   ... python -m flotilla.rl_router evaluate --labels L --items I --out OUT --serve S --pool P --exclude X --held-out
# Output: $SCRATCH/flotilla/runs/rl-router/<name>/ (chains_*.jsonl, traces_*.jsonl, policy*.npz, table_*.md,
# beyond_oracle_*.md, compute.jsonl, server logs).
#
# Inputs (environment):
#   LABELS       graded folder (per_question.jsonl, split.json, summary.json); the ten-route labels once they exist
#   ITEMS        run items (quoted glob; LongMemEval items included once the Memory routes are labelled)
#   POOL         pool questions WITH gold (label_loop.grade); required for train/evaluate. Not on Fir yet: copy the
#                router pool (pool.clean.jsonl) from the cluster that graded run-03.
#   MEMORY_ITEMS LongMemEval items with answers (judge), only when the labels have Memory routes
#   AUDIT        always-wrong audit (diagnosis.json, always_wrong.md) -> the wrong-gold exclusion list
#   ROUTER_DIR   strategy_router output folder; priors come from its best router on dev (ROUTER=name to force one)
#   ALPHA        reward penalty per GPU-second (default 0.001), EPOCHS (2), MAX_STEPS (3), MAX_GPU_S (60)
#   GPUS         H100s per training job = vLLM replicas (default 1), TIME (per job), CHAIN (jobs in a row, resume)
# Estimate (rl_router estimate on run-03's six-route labels, route-accuracy prior, untrained policy with Thompson
# sampling, alpha 0.001): 20.9 GPU-s per training question (2.04 steps), 10.9 per greedy dev question; 2 epochs x 1,015
# train = 11.8 GPU-h, dev evaluation 0.65 GPU-h, ~10 min vLLM start per job: about 12.6 h on 1 H100, 3.3 h on 4.
# Labels' GPU-s are ~18% high (run-03 reran 263 questions). TIME 16 h = estimate + 25%; a job stops starting chains
# 90 min before its end (a Vote chain can take over an hour of wall time) and the next job in the chain resumes.
set -euo pipefail
MODE=${1:?dry-run, train or evaluate}; NAME=${2:?out dir name}
case $MODE in dry-run|train|evaluate) ;; *) echo "mode must be dry-run, train or evaluate" >&2; exit 2 ;; esac
CODE=${CODE:-/project/def-sylu/khaledmk/flotilla}; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
LABELS=${LABELS:-$SCRATCH/flotilla/test04-labels/run-03}
ITEMS=${ITEMS:-$SCRATCH/flotilla/labelitems_strategy/strat12_*.jsonl}
POOL=${POOL:-$SCRATCH/flotilla/pool.clean.jsonl}
AUDIT=${AUDIT:-$LABELS/audit}
ROUTER_DIR=${ROUTER_DIR:-$SCRATCH/flotilla/runs/strategy-router/train}
ALPHA=${ALPHA:-0.001}; EPOCHS=${EPOCHS:-2}; MAX_STEPS=${MAX_STEPS:-3}; MAX_GPU_S=${MAX_GPU_S:-60}
GPUS=${GPUS:-1}; TIME=${TIME:-16:00:00}; CHAIN=${CHAIN:-2}; EVAL_TIME=${EVAL_TIME:-4:00:00}
OUT=$SCRATCH/flotilla/runs/rl-router/$NAME
JOB="$CODE/scripts/trillium/job.sbatch"
mkdir -p "$OUT" "$SCRATCH/flotilla/logs"
[[ -f $AUDIT/diagnosis.json ]] || { echo "no $AUDIT/diagnosis.json (copy experiments/test-04-strategy-router/runs/run-03/audit)" >&2; exit 1; }
COMMON=(--labels "$LABELS" --items "$ITEMS" --out "$OUT")
secs() { IFS=: read -r h m s <<<"${1#*-}"; d=0; [[ $1 == *-* ]] && d=${1%%-*}; echo $(( d*86400 + 10#$h*3600 + 10#$m*60 + 10#$s )); }

if [[ $MODE == dry-run ]]; then
  # fake Qwen through the real loop (no GPU), and the estimate of the real run from the labels
  CPU_OPTS=(--account=def-sylu_cpu --cpus-per-task=4 --mem=16G --time=0:30:00 --chdir="$SCRATCH/flotilla/logs")
  D=$(sbatch --parsable "${CPU_OPTS[@]}" --job-name="rl-dry" "$JOB" python -m flotilla.rl_router dry-run "${COMMON[@]}" \
    --audit "$AUDIT" ${PRIOR:+--prior "$PRIOR"})
  S=$(sbatch --parsable "${CPU_OPTS[@]}" --job-name="rl-estimate" "$JOB" python -m flotilla.rl_router estimate \
    --labels "$LABELS" --items "$ITEMS" --out "$OUT/estimate" --alpha "$ALPHA" --epochs "$EPOCHS" ${PRIOR:+--prior "$PRIOR"})
  echo "dry-run $D  estimate $S  -> $OUT"
  exit 0
fi

[[ -f $POOL ]] || { echo "no pool with gold at $POOL (set POOL=...)" >&2; exit 1; }
LIVE=(--serve "$CODE/configs/servers.json" --server-name qwen_w4a16 --replicas "$GPUS" --pool "$POOL"
      ${MEMORY_ITEMS:+--memory-items "$MEMORY_ITEMS"} --concurrency $((64 * GPUS)))
GPU_OPTS=(--account=def-sylu_gpu --gpus-per-node="h100:$GPUS" --cpus-per-task=$((8 * GPUS)) --mem=$((64 * GPUS))G)

if [[ $MODE == train ]]; then
  # 1. priors from the best supervised router on dev (train + dev questions only) and the wrong-gold list
  P=$(sbatch --parsable --account=def-sylu_gpu --gpus-per-node=h100:1 --cpus-per-task=8 --mem=64G --time=0:30:00 \
    --job-name="rl-priors" --chdir="$SCRATCH/flotilla/logs" "$JOB" python -m flotilla.rl_router priors "${COMMON[@]:0:4}" \
    --router-dir "$ROUTER_DIR" ${ROUTER:+--router "$ROUTER"} --out "$OUT/priors.jsonl")
  "$CODE/envs/flotilla/bin/python" -c "import sys; sys.path.insert(0, '$CODE'); from flotilla import rl_router as r; \
    r.write_exclusions('$OUT/excluded_wrong_gold.txt', r.build_exclusions('$AUDIT'), '$AUDIT/diagnosis.json')"
  # 2. CHAIN training jobs; each resumes from the chain log (afterany: a job that hit its time limit still continues)
  STOP=$(( $(secs "$TIME") - 5400 ))
  DEP="afterok:$P"; T=""
  for k in $(seq 1 "$CHAIN"); do
    T=$(sbatch --parsable "${GPU_OPTS[@]}" --time="$TIME" --dependency="$DEP" --job-name="rl-train-$k" \
      --chdir="$SCRATCH/flotilla/logs" "$JOB" python -m flotilla.rl_router train "${COMMON[@]}" "${LIVE[@]}" \
      --prior "file:$OUT/priors.jsonl" --alpha "$ALPHA" --epochs "$EPOCHS" --max-steps "$MAX_STEPS" \
      --max-gpu-s "$MAX_GPU_S" --stop-after "$STOP")
    DEP="afterany:$T"
  done
  # 3. dev evaluation, greedy, with the beyond-oracle count
  E=$(sbatch --parsable "${GPU_OPTS[@]}" --time="$EVAL_TIME" --dependency="afterok:$T" --job-name="rl-eval" \
    --chdir="$SCRATCH/flotilla/logs" "$JOB" python -m flotilla.rl_router evaluate "${COMMON[@]}" "${LIVE[@]}" \
    --exclude "$OUT/excluded_wrong_gold.txt")
  echo "priors $P  train ...$T (chain $CHAIN)  eval $E  -> $OUT"
else
  [[ -f $OUT/excluded_wrong_gold.txt ]] || "$CODE/envs/flotilla/bin/python" -c "import sys; sys.path.insert(0, '$CODE'); \
    from flotilla import rl_router as r; r.write_exclusions('$OUT/excluded_wrong_gold.txt', r.build_exclusions('$AUDIT'), '$AUDIT/diagnosis.json')"
  E=$(sbatch --parsable "${GPU_OPTS[@]}" --time="$EVAL_TIME" --job-name="rl-eval" --chdir="$SCRATCH/flotilla/logs" \
    "$JOB" python -m flotilla.rl_router evaluate "${COMMON[@]}" "${LIVE[@]}" --exclude "$OUT/excluded_wrong_gold.txt")
  echo "eval $E -> $OUT"
fi
