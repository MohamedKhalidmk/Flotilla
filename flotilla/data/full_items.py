"""Cut the full benchmark item files into job-sized chunks for the full runs (Qwen alone).

    python -m flotilla.data.full_items --items-dir $SCRATCH/flotilla/fullitems_all --ruler-dir $SCRATCH/flotilla/ruler \
        --out-dir $SCRATCH/flotilla/fullitems
Groups and chunk sizes come from the small test's measured seconds per question (1 H100, 64 at a time):
math 6.6 s, mixed 20.3 s, vision 4.0 s, RULER 45.9 s; chunks of about 45-90 minutes. Each chunk file is named
full_<group>_KK.jsonl; items keep their own bench field, so scoring is unchanged. Writes chunks.json with the plan.
"""
import argparse
import json
from pathlib import Path

GROUPS = {"math": (["gsm8k", "math500", "aime2025", "aime2026"], 400, 6.6),
          "mixed": (["gpqa", "ifeval", "lcb"], 250, 20.3),
          "vision": (["mmmu", "ocrbench"], 600, 4.0),
          "ruler": (["ruler_32k", "ruler_64k"], 120, 45.9)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items-dir", required=True)
    ap.add_argument("--ruler-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan = {}
    for g, (benches, size, sec) in GROUPS.items():
        items = []
        for b in benches:
            p = Path(a.ruler_dir) / f"{b}_full.jsonl" if b.startswith("ruler") else Path(a.items_dir) / f"{b}.jsonl"
            items += [json.loads(l) for l in open(p)]
        for k in range(0, len(items), size):
            name = f"full_{g}_{k // size:02d}"
            chunk = items[k:k + size]
            with open(out / f"{name}.jsonl", "w") as f:
                f.writelines(json.dumps(it, ensure_ascii=False) + "\n" for it in chunk)
            minutes = len(chunk) * sec / 60
            plan[name] = {"items": len(chunk), "estimated_minutes": round(minutes), "limit_minutes": round(minutes * 1.5 + 10)}
    (out / "chunks.json").write_text(json.dumps(plan, indent=1))
    print(json.dumps({"chunks": len(plan), "items": sum(p["items"] for p in plan.values()),
                      "estimated_gpu_hours": round(sum(p["estimated_minutes"] for p in plan.values()) / 60, 1)}))


if __name__ == "__main__":
    main()
