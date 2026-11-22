"""test-01 table: MATH-500 (all 500) per model and build, from runs/run-01/*/summary.json."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import write_table

BUILD = {"bf16": ("BF16", "16-bit reference"), "fp8-ours": ("FP8 (ours)", "8-bit"), "fp8-nvidia": ("FP8 (NVIDIA)", "8-bit"),
         "w4a16-ours": ("W4A16 (ours)", "4-bit"), "w4a16-amd": ("W4A16 (AMD)", "4-bit"), "int4-redhat": ("INT4 (RedHat)", "4-bit")}
IDS = {"qwen-w4a16-ours": ("F01", "S102"), "qwen-fp8-ours": ("F02", "S103"), "qwen-bf16": ("Qwen3.8-27B BF16", "S104"),
       "qwen-int4-redhat": ("RedHat INT4", "S105"), "phi-fp8-ours": ("F03", "S106"), "phi-w4a16-ours": ("F04", "S107"),
       "phi-bf16": ("Phi-4-reasoning-plus BF16", "S108"), "phi-fp8-nvidia": ("NVIDIA FP8", "S109"), "phi-w4a16-amd": ("AMD W4A16", "S110")}  # docs/reference/REGISTRY.md
rows = []
for d in sorted((HERE / "runs" / "run-01").glob("math500-*")):
    s = json.loads((d / "summary.json").read_text())
    model, build = d.name.removeprefix("math500-").split("-", 1)
    rows.append({"candidate": IDS[d.name.removeprefix("math500-")][0], "setup": IDS[d.name.removeprefix("math500-")][1], "model": {"qwen": "Qwen3.8-27B", "phi": "Phi-4-reasoning-plus"}[model], "build": BUILD[build][0],
                 "bits": BUILD[build][1], "accuracy": s["accuracy"], "correct": s["correct"], "n": s["n"],
                 "hit_token_cap": s["truncated"], "max_tokens": s["max_tokens"], "output_tokens": s["tokens_out"],
                 "wall_seconds": s["wall_seconds"], "run": "run-01/" + d.name})
rows.sort(key=lambda r: (r["model"] != "Qwen3.8-27B", ["16-bit reference", "8-bit", "4-bit"].index(r["bits"]), r["build"]))
write_table(HERE, "table", rows, "MATH-500, all 500 questions, greedy, math-verify. Rule 4.1: 4-bit if within 1.0 point of 8-bit.")
print(f"{len(rows)} rows")
