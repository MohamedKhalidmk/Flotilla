#!/usr/bin/env bash
# Test sets for the final run and the leakage check (protocol 1.1, 5). Run on trig-login01 (internet).
# GPQA (Idavidrein/gpqa) is gated: it needs a Hugging Face token with the dataset's terms accepted
# (HF_TOKEN in the environment); without one it is reported as FAILED and fetched later.
set -euo pipefail
source "$(dirname "$0")/modules.sh"
export HF_HOME="$SCRATCH/flotilla/hf"
"$PROJECT/flotilla/envs/flotilla/bin/python" - <<'PY'
from huggingface_hub import snapshot_download
for d in ["google/IFEval", "MathArena/aime_2025", "MathArena/aime_2026", "opencompass/AIME2025",
          "lmms-lab/MMMU", "echo840/OCRBench", "lmms-lab/OCRBench", "Idavidrein/gpqa"]:
    try:
        print("dataset ok", d, snapshot_download(d, repo_type="dataset"), flush=True)
    except Exception as e:
        print("dataset FAILED", d, type(e).__name__, str(e)[:160], flush=True)
PY
