#!/usr/bin/env bash
# Separate environment for quantization only (llm-compressor). Run on trig-login01.
# Why separate: llm-compressor 0.15.0 needs compressed-tensors 0.20.1, torch <= 2.14.1 and
# transformers <= 5.21.0, while the serving env's vllm 0.32.0 is built on compressed-tensors 0.17.0,
# torch 2.13.0 and transformers 5.19.0 (checked 2026-11-19). Quantized checkpoints are saved in the
# compressed-tensors format that vLLM reads; every one is loaded by vLLM in its MATH-500 run.
set -euo pipefail
source "$(dirname "$0")/modules.sh"
ROOT="${FLOTILLA_ROOT:-$PROJECT/flotilla}"
ENV="$ROOT/envs/quant"
[ -x "$ENV/bin/python" ] || virtualenv --no-download --system-site-packages "$ENV"
"$ENV/bin/pip" install -q --no-index --upgrade pip
"$ENV/bin/pip" install -q --no-index "torch==2.14.1" "transformers==5.20.1" accelerate datasets numpy pillow pyyaml requests tqdm loguru
"$ENV/bin/pip" freeze | grep -iE "^(torch|transformers)==" > "$ROOT/quant-pins.txt"
"$ENV/bin/pip" install -q -c "$ROOT/quant-pins.txt" "compressed-tensors==0.20.1" "llmcompressor==0.15.0" "auto-round>=0.15.1" nvidia-ml-py
"$ENV/bin/python" -c "import torch, transformers, llmcompressor, compressed_tensors; print('quant env ok', torch.__version__, transformers.__version__, llmcompressor.__version__, compressed_tensors.__version__)"
"$ENV/bin/pip" freeze > "$ROOT/quant-env-freeze.txt"
