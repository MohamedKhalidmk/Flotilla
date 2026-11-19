#!/usr/bin/env bash
# Run once on Trillium's GPU login node (trig-login01), which has internet; compute nodes do not.
# Builds the Flotilla Python environment in project space so jobs can use it offline.
#   bash scripts/trillium/setup_env.sh
# Prebuilt cluster wheels where they exist (vllm, torch, transformers, lm_eval, compressed_tensors),
# PyPI for the rest (llmcompressor, lmms_eval). Versions are recorded in env-freeze.txt.
set -euo pipefail
# pyarrow (needed by vllm) comes from the arrow module, which must be loaded before the env is made
# and before it is activated; jobs load the same modules (scripts/trillium/modules.sh).
source "$(dirname "$0")/modules.sh"
ROOT="${FLOTILLA_ROOT:-$PROJECT/flotilla}"
ENV="$ROOT/envs/flotilla"
mkdir -p "$ROOT/envs"
[ -x "$ENV/bin/python" ] || virtualenv --no-download --system-site-packages "$ENV"
"$ENV/bin/pip" install -q --no-index --upgrade pip
# everything the cluster prebuilds, from its wheelhouse only (built for these GPUs and CPUs; cp314)
# vllm brings its own torch, flashinfer and attention kernels; asking for flash_attn or a torch pin on top
# makes the set unresolvable (tested 2026-11-19), so only vllm and the eval packages are named.
"$ENV/bin/pip" install -q --no-index "vllm==0.32.0" "lm_eval==0.4.11" transformers compressed_tensors
# not in the wheelhouse: from PyPI, without letting them replace the cluster torch/vllm
"$ENV/bin/pip" install -q llmcompressor lmms_eval --no-deps
"$ENV/bin/pip" install -q datasets accelerate evaluate sympy latex2sympy2_extended math-verify huggingface_hub pyyaml pandas
"$ENV/bin/python" - <<'PY'
import importlib
for m in ["vllm", "torch", "transformers", "llmcompressor", "compressed_tensors", "lm_eval", "lmms_eval"]:
    try:
        mod = importlib.import_module(m)
        print(f"{m:20s} {getattr(mod, '__version__', '?')}")
    except Exception as e:
        print(f"{m:20s} IMPORT FAILED: {type(e).__name__}: {str(e)[:120]}")
PY
"$ENV/bin/pip" freeze > "$ROOT/env-freeze.txt"
echo "env ready: $ENV"
