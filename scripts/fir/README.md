# Fir

Fir runs the same Slurm submit scripts as Nibi (`scripts/nibi/`, account def-sylu_gpu via `sbatch_opts.sh`) and the
same job script (`scripts/trillium/job.sbatch`, which finds the code under `~/projects/def-sylu` on Fir). Caches go to
node-local disk (`$SLURM_TMPDIR`). GRAFT's Fir jobs live in the GRAFT repo (`scripts/fir/`).
