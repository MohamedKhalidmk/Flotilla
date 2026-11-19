#!/usr/bin/env bash
# Router A (vLLM Semantic Router v0.4.0) has no Docker on the cluster: convert its CPU image to Apptainer.
# Run on trig-login01 (internet). Apptainer's temp/cache must not be on Lustre (Alliance docs).
set -uo pipefail
module load apptainer >/dev/null 2>&1
OUT="$SCRATCH/flotilla/images"
mkdir -p "$OUT"
export APPTAINER_TMPDIR="/tmp/$USER-apptainer-tmp" APPTAINER_CACHEDIR="/tmp/$USER-apptainer-cache"
mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"
for tag in v0.4.0 0.4.0 latest; do
  echo "== trying vllm-sr:$tag"
  if apptainer pull --force "$OUT/vllm-sr-$tag.sif" "docker://ghcr.io/vllm-project/semantic-router/vllm-sr:$tag"; then
    echo "PULLED $OUT/vllm-sr-$tag.sif"; ls -la "$OUT/vllm-sr-$tag.sif"; break
  fi
done
rm -rf "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"
