"""test-01 table: MATH-500 (all 500) per model and build, from runs/run-01/*/summary.json."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import write_table

BUILD = {"bf16": ("BF16", "16-bit reference"), "fp8-ours": ("FP8 (ours)", "8-bit"), "fp8-nvidia": ("FP8 (NVIDIA)", "8-bit"),
         "w4a16-ours": ("W4A16 (ours)", "4-bit"), "w4a16-amd": ("W4A16 (AMD)", "4-bit"), "int4-redhat": ("INT4 (RedHat)", "4-bit")}
rows = []
for d in sorted((HERE / "runs" / "run-01").glob("math500-*")):
    s = json.loads((d / "summary.json").read_text())
    model, build = d.name.removeprefix("math500-").split("-", 1)
    rows.append({"model": {"qwen": "Qwen3.8-27B", "phi": "Phi-4-reasoning-plus"}[model], "build": BUILD[build][0],
                 "bits": BUILD[build][1], "accuracy": s["accuracy"], "correct": s["correct"], "n": s["n"],
                 "hit_token_cap": s["truncated"], "max_tokens": s["max_tokens"], "output_tokens": s["tokens_out"],
                 "wall_seconds": s["wall_seconds"], "run": "run-01/" + d.name})
rows.sort(key=lambda r: (r["model"] != "Qwen3.8-27B", ["16-bit reference", "8-bit", "4-bit"].index(r["bits"]), r["build"]))
write_table(HERE, "table", rows, "MATH-500, all 500 questions, greedy, math-verify. Rule 4.1: 4-bit if within 1.0 point of 8-bit.")
print(f"{len(rows)} rows")
