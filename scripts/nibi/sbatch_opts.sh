#!/usr/bin/env bash
# Nibi (def-sylu -> def-sylu_gpu): H100 80 GB nodes with 8 GPUs, 112 cores, 2 TB RAM. Unlike Trillium, a job gets only
# what it asks for, so CPUs and memory are requested per GPU. Same code path (/project/def-sylu/khaledmk/flotilla),
# same modules (scripts/trillium/modules.sh), same job script.
#   G=4; export FLOTILLA_SBATCH="$(bash scripts/nibi/sbatch_opts.sh $G)"; bash scripts/trillium/submit_smalltest.sh cmda_local $G 6
#   sbatch $(bash scripts/nibi/sbatch_opts.sh 1) --gpus-per-node=h100:1 ... scripts/trillium/job.sbatch python -m ...
G=${1:?gpus}
echo "--account=def-sylu --cpus-per-task=$((12 * G)) --mem=$((220 * G))G"
