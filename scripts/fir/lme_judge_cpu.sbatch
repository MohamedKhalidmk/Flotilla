#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=%x-%j.out
# PAID: LongMemEval's judge on Claude Haiku 5.5 (protocol-v10 addendum) for every route's answers, with a cost guard
# like GRAFT's scripts/fir/run_real_guarded_cpu.sbatch: every minute it sums cost_usd in this judge folder's usage.jsonl
# (only rows written since the job started) and stops past COST_CAP_USD (default $1). CPU only; needs internet (Fir or
# Nibi compute nodes, not Trillium). The key comes only from the submitting shell's environment (sbatch passes it on).
#   submitted by scripts/fir/submit_longmemeval.sh judge, after the fixed Haiku check (afterok)
#   args: OUT_DIR ITEMS route=DIR [route=DIR ...]
set -euo pipefail
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs sbatch}"
CODE=/project/def-sylu/khaledmk/flotilla; [[ -d $CODE ]] || CODE=$(readlink -f "$HOME/projects/def-sylu")/khaledmk/flotilla
source "$CODE/scripts/trillium/modules.sh"
export PYTHONPATH="$CODE" PYTHONUNBUFFERED=1
PY="$CODE/envs/flotilla/bin/python"
OUT=$1; ITEMS=$2; shift 2
CAP="${COST_CAP_USD:-1}"
START=$(date +%s)
mkdir -p "$OUT"
echo "[judge] $(date -Is) start on $(hostname): $# run folders, cap \$$CAP"
setsid "$PY" -m flotilla.memory_route judge --backend haiku --items "$ITEMS" --runs "$@" --out "$OUT/verdicts.jsonl" \
  --concurrency "${JUDGE_CONCURRENCY:-8}" &
JPID=$!
spent() {
  "$PY" -c '
import json, os, sys
start, path, total = float(sys.argv[1]), sys.argv[2], 0.0
if os.path.exists(path):
    for line in open(path):
        try:
            r = json.loads(line)
            if r["ts"] >= start:
                total += r["cost_usd"]
        except (ValueError, KeyError):
            pass
print(f"{total:.4f}")' "$START" "$OUT/usage.jsonl"
}
while kill -0 "$JPID" 2>/dev/null; do
  sleep 60
  SPENT=$(spent)
  echo "[cost guard] $(date +%H:%M) spent \$$SPENT of \$$CAP"
  if awk -v s="$SPENT" -v c="$CAP" 'BEGIN{exit !(s > c)}'; then
    echo "[cost guard] over the cap: stopping the judge"
    kill -TERM -- -"$JPID" 2>/dev/null || true
    exit 3
  fi
done
wait "$JPID"
echo "[judge] $(date -Is) finished, this job spent \$$(spent); verdicts $(wc -l < "$OUT/verdicts.jsonl")"
