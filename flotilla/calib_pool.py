# Sources: ultrachat (docs/reference/REFERENCES.md)
"""Write the W4A16 calibration text (flotilla/quantize.py: HuggingFaceH4/ultrachat_200k train_sft[:512]) as a
leakage-check pool: one row per message, {id, source, task}, so the 13-gram and embedding checks see every turn.

    python -m flotilla.calib_pool --samples 512 --out $SCRATCH/flotilla/router/calib_pool.jsonl
"""
import argparse
import json

from flotilla.data import load as load_dataset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=512)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ds = load_dataset("HuggingFaceH4/ultrachat_200k", split=f"train_sft[:{a.samples}]")  # same rows quantize.py used
    n = 0
    with open(a.out, "w") as f:
        for i, ex in enumerate(ds):
            for j, m in enumerate(ex["messages"]):
                f.write(json.dumps({"id": f"calib-{i}-{j}", "source": f"ultrachat_calib_{m['role']}", "task": m["content"]}) + "\n")
                n += 1
    print(f"{len(ds)} conversations, {n} messages -> {a.out}")


if __name__ == "__main__":
    main()
