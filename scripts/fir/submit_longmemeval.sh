#!/usr/bin/env bash
# test-04 route labels on LongMemEval (Fir or Nibi, def-sylu_gpu, one H100 per job). Qwen at --max-model-len 163840
# (configs/servers_longmemeval*.json); run items from flotilla.longmemeval run-items in $LME/runitems.
#   bash scripts/fir/submit_longmemeval.sh base    <route> <time> <shard>...  # fast tools deep deep_tools vote vote_tools
#   bash scripts/fir/submit_longmemeval.sh prepare <time> <shard>... [-- extra prepare args]  # GRAFT graphs, one job per shard
#   bash scripts/fir/submit_longmemeval.sh memory  <route> <time> <shard>...  # memory memory_deep vote_memory deep_tools_memory
#   ANTHROPIC_API_KEY=... bash scripts/fir/submit_longmemeval.sh judge <time> <name>  # PAID: Haiku check, then Haiku judge (Fir)
# Output: $LME/runs/<route>/<shard>/ (trace.jsonl, compute.json, servers.resolved.json), $LME/graft_cache, $LME/judge.
# Base routes run 6 items at a time (2 for Vote routes: 10 requests for 5 sequences), so no request waits in vLLM
# anywhere near the client timeout (3,600 s); CONC overrides.
# SUFFIX names a twin (its out dir is <shard><SUFFIX>, never shared with the twin). EXTRA_SBATCH adds sbatch options
# (e.g. --gpus-per-node=nvidia_h100_80gb_hbm3_3g.40gb:1 for a Nibi MIG slice).
set -euo pipefail
MODE=$1; shift
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
LME=${LME:-$SCRATCH/flotilla/lme}
ITEMS=$SCRATCH/flotilla/data/longmemeval/memory_items.jsonl
GPU=${GPU:-h100:1}
SB=(sbatch --parsable --account=def-sylu_gpu --gpus-per-node=$GPU --cpus-per-task=${CPUS:-12} --mem=${MEM:-200G}
    --chdir="$LME/logs" ${EXTRA_SBATCH:-})
JOB="$CODE/scripts/fir/lme_job.sbatch"
mkdir -p "$LME/logs" "$LME/runs"
case $MODE in
  base)
    R=$1; TIME=$2; shift 2
    for K in "$@"; do S=$(printf "lme_%02d" "$K")
      "${SB[@]}" --time=$TIME --job-name="lme-$R-$S${SUFFIX:-}" "$JOB" python -m flotilla.serve \
        --system "$CODE/configs/systems/qwen_strategy_$R.json" --servers "$CODE/configs/servers_longmemeval.json" \
        --items-dir "$LME/runitems/base" --out "$LME/runs/$R/$S${SUFFIX:-}" --benches "$S" --concurrency ${CONC:-$([[ $R == vote* ]] && echo 2 || echo 6)}
    done ;;
  prepare)
    TIME=$1; shift; SH=(); while [[ $# -gt 0 && $1 != -- ]]; do SH+=("$1"); shift; done; [[ ${1:-} == -- ]] && shift
    for K in "${SH[@]}"; do S=$(printf "lmem_%02d" "$K")
      "${SB[@]}" --time=$TIME --job-name="lme-prep-$S${SUFFIX:-}" --export=ALL,GRAFT=1,GRAFT_COMMIT=${GRAFT_COMMIT:-unknown} \
        "$JOB" python -m flotilla.serve --system "$CODE/configs/systems/qwen_strategy_memory.json" \
        --servers "$CODE/configs/servers_longmemeval_memory.json" --out "$LME/runs/prepare/$S${SUFFIX:-}" \
        --exec "python -m flotilla.memory_route prepare --items $LME/runitems/memory/$S.jsonl --url {url} --model {model} --cache $LME/graft_cache $*"
    done ;;
  memory)
    R=$1; TIME=$2; shift 2
    for K in "$@"; do S=$(printf "lmem_%02d" "$K")
      "${SB[@]}" --time=$TIME --job-name="lme-$R-$S${SUFFIX:-}" --export=ALL,GRAFT=1,GRAFT_COMMIT=${GRAFT_COMMIT:-unknown} \
        "$JOB" python -m flotilla.serve \
        --system "$CODE/configs/systems/qwen_strategy_$R.json" --servers "$CODE/configs/servers_longmemeval_memory.json" \
        --items-dir "$LME/runitems/memory" --out "$LME/runs/$R/$S${SUFFIX:-}" --benches "$S" --concurrency 32
    done ;;
  judge)
    # PAID (protocol-v10 addendum): Claude Haiku 5.5 judges every route's answers, on Fir (the fixed Haiku check lives
    # in GRAFT on Fir). The fixed check runs first as its own guarded CPU job; the judge (CPU, cost cap $1,
    # scripts/fir/lme_judge_cpu.sbatch) starts afterok on it. The key only from this shell's environment.
    # ROUTES="fast deep ..." limits the routes (default: every route folder under $LME/runs with trace.jsonl).
    TIME=$1; NAME=$2; RUNS=()
    : "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs this (never in a file)}"
    for d in "$LME"/runs/*/lme*; do
      R=$(basename "$(dirname "$d")"); [[ -f $d/trace.jsonl && $R != prepare ]] || continue
      [[ -z ${ROUTES:-} || " $ROUTES " == *" $R "* ]] && RUNS+=("$R=$d")
    done
    SGAR=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/SGAR
    C=$(cd "$SGAR" && CANARY=0 sbatch --parsable scripts/fir/run_real_guarded_cpu.sbatch configs/runs/exp/canary/haiku_replay38.yaml)
    mkdir -p "$LME/judge/$NAME"
    J=$(sbatch --parsable --time=$TIME --dependency=afterok:$C --job-name="lme-judge-$NAME" --chdir="$LME/logs" \
        --export=ALL,COST_CAP_USD=${COST_CAP_USD:-1} "$CODE/scripts/fir/lme_judge_cpu.sbatch" "$LME/judge/$NAME" "$ITEMS" "${RUNS[@]}")
    echo "haiku check $C  judge $J (${#RUNS[@]} run folders) -> $LME/judge/$NAME" ;;
  *) echo "mode: base | prepare | memory | judge" >&2; exit 2 ;;
esac
