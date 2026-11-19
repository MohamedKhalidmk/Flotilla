# Sourced by setup_env.sh and by every Trillium job script: the same modules every time.
# Tested on trig-login01, 2026-11-19:
#   python/3.14 + arrow/24.0.0 + opencv/4.13 on the default stack -> pyarrow 24.0.0 and cv2 4.13.0 import.
#   Python 3.14 is required: the wheelhouse's vllm 0.32.0 needs flashinfer_python, which needs
#   nccl_extensions, and nccl_extensions is only built for cp314 (not on PyPI at all).
#   pyarrow and opencv cannot be pip-installed on Alliance clusters; they come from these modules.
#   Not working: arrow/25.0.1 (default stack), StdEnv/2026 + arrow/26.0.0, opencv/4.12 with python/3.14.
#   cuda/13.2: vllm's wheels are built against it, and FlashInfer JIT-compiles kernels with nvcc at startup.
module load python/3.14 gcc arrow/24.0.0 opencv/4.13 cuda/13.2
