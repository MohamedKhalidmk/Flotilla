#!/bin/zsh
# Holds the Cohere trial key in this process's memory only (hidden input; never written to disk) and runs the job
# scripts queued in $Q one at a time with the key in their environment. Stops when $Q/STOP appears or after 12 h idle.
set -u
Q=/Users/mk/flotilla-data/cohere-queue
setopt nullglob
mkdir -p $Q/done
read -s "COHERE_API_KEY?Paste the Cohere trial key (input hidden), then press Enter: "
echo
export COHERE_API_KEY
echo "runner up; watching $Q"
idle=0
while [ ! -f $Q/STOP ] && [ $idle -lt 43200 ]; do
  job=$(ls $Q/*.sh 2>/dev/null | sort | head -1)
  if [ -n "$job" ]; then
    name=$(basename $job .sh)
    mv $job $Q/done/$name.sh
    echo "== $(date +%H:%M:%S) running $name"
    zsh $Q/done/$name.sh 2>&1 | tee $Q/done/$name.log
    echo "== $(date +%H:%M:%S) finished $name"
    idle=0
  else
    sleep 5; idle=$((idle + 5))
  fi
done
unset COHERE_API_KEY
rm -f $Q/STOP
echo "runner stopped; key cleared"
