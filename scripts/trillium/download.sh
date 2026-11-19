#!/usr/bin/env bash
# Run on trig-login01 (internet). Compute nodes have none, so every model and dataset is fetched here first.
#   bash scripts/trillium/download.sh
set -euo pipefail
source "$(dirname "$0")/modules.sh"
ROOT="${FLOTILLA_ROOT:-$PROJECT/flotilla}"
export HF_HOME="$SCRATCH/flotilla/hf"
mkdir -p "$HF_HOME"
PY="$ROOT/envs/flotilla/bin/python"
"$PY" - <<'PY'
import os
from huggingface_hub import snapshot_download
models = [
    "Qwen/Qwen3.8-27B",                      # solver (protocol 1.4)
    "microsoft/Phi-4-reasoning-plus",        # solver, keep-or-drop by rule 4.2b
    "RedHatAI/Qwen3.8-27B-INT4",             # community W4A16 to compare with ours
    "nvidia/Phi-4-reasoning-plus-FP8",       # community 8-bit to compare with ours
]
datasets = [
    "HuggingFaceH4/MATH-500",                # quantization decision benchmark (rule 4.1)
    "openai/gsm8k",                          # harness check (test) and router training (train split)
    "HuggingFaceH4/ultrachat_200k",          # GPTQ calibration text (not a benchmark: no leakage)
    # router B training sources (protocol 5): disjoint from the test sets by split, year or date,
    # then checked by 13-gram overlap and embedding similarity before training
    "EleutherAI/hendrycks_math",             # MATH train split only (MATH-500 comes from MATH test)
    "di-zhang-fdu/AIME_1983_2024",           # AIME before 2025
    "TIGER-Lab/MMLU-Pro",                    # science multiple choice (no GPQA source)
    "allenai/RLVR-IFeval",                   # instruction following (checked against IFEval prompts)
    "livecodebench/code_generation_lite",    # code: only problems released before 2024-08-01 are used
]
for m in models:
    try:
        p = snapshot_download(m, allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.py", "*.jinja", "tokenizer*"])
        print("model ok", m, p, flush=True)
    except Exception as e:
        print("model FAILED", m, type(e).__name__, str(e)[:200], flush=True)
for d in datasets:
    try:
        p = snapshot_download(d, repo_type="dataset")
        print("dataset ok", d, p, flush=True)
    except Exception as e:
        print("dataset FAILED", d, type(e).__name__, str(e)[:200], flush=True)
PY
du -sh "$HF_HOME"
