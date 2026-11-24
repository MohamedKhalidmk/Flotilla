#!/bin/zsh
# Command A+ small-test screen on Cohere's hosted API (protocol-v5, section 4.2). Free trial key only.
# The key is read with hidden input, kept in this process's environment, and never written anywhere.
# Calls (trial: 1,000 per month, 20 per minute): 2 used by the first smoke attempt, 1 probe, up to 3 for the smoke check,
# at most 894 for the run: 900 in all. 18 per minute.
set -u
cd /Users/mk/flotilla
P=/Users/mk/flotilla-data/venv/bin/python
ITEMS=/Users/mk/flotilla-data/smalltest
RUNS=/Users/mk/flotilla-data/runs
OUT=$RUNS/cmda-smalltest
SMOKE=$RUNS/cmda-smoke2
mkdir -p $OUT

read -s "COHERE_API_KEY?Paste the Cohere trial key (input hidden), then press Enter: "
echo
export COHERE_API_KEY

echo "== probe: one GSM8K call, shows where the answer text lands"
$P scripts/mac/cohere_probe.py || { echo "PROBE FAILED. Stopping."; unset COHERE_API_KEY; exit 1; }

echo "== smoke check: 2 OCRBench items (image input, thinking on)"
$P -m flotilla.core.smalltest --config configs/systems/cmda_alone.json --items-dir $ITEMS --benches ocrbench \
  --out $SMOKE --max-calls 3 --concurrency 1 --rpm 18
if [ ! -s $SMOKE/trace.jsonl ] || ! grep -q '"final_answer": "' $SMOKE/trace.jsonl; then
  echo "SMOKE CHECK FAILED: see $SMOKE/trace.jsonl. Stopping before the full run."
  unset COHERE_API_KEY
  exit 1
fi
echo "smoke check passed"

run() {
  $P -m flotilla.core.smalltest --config configs/systems/cmda_alone.json --items-dir $ITEMS --out $OUT \
    --max-calls 894 --rpm 18 --concurrency 8 2>&1 | tee -a $OUT/run.log
}

echo "== full small test (all benchmark files present now)"
run

echo "== waiting for the RULER items (up to 3 hours), then running them with the same caps"
waited=0
while [ ! -f $ITEMS/ruler_64k.jsonl ] && [ $waited -lt 10800 ]; do sleep 60; waited=$((waited + 60)); done
if [ -f $ITEMS/ruler_64k.jsonl ]; then run; else echo "RULER items did not arrive; run this script again later (it resumes)."; fi

unset COHERE_API_KEY
echo "DONE. Calls used: $(cat $OUT/calls.json)"
