"""Write the small real-item samples behind tests/test_formats.py (run once where the datasets are, e.g. a Fir login node).

    source scripts/trillium/modules.sh; PYTHONPATH=. envs/flotilla/bin/python scripts/make_format_samples.py \
        --out tests/data/formats --smalltest $SCRATCH/flotilla/smalltest

For each converter in flotilla.splits (benchmarks) and flotilla.router_data (router pool) it loads the real dataset the
same way the converter does, keeps a few raw rows chosen by a fixed rule (every task type and the variants that matter:
MMLU-Pro with 10 options and with fewer, MMMU multiple choice and open, OCRBench question types, LiveCodeBench stdin and
function problems), and writes them as JSON. Images are shrunk to at most 96 px and stored as PNG base64; LiveCodeBench
keeps the rows with the smallest hidden tests. RULER has no raw dataset (lm-eval generates it): its sample is exported
items with the haystack's middle cut out (marked `trimmed_for_tests`). Nothing here is used by any run.
"""
import argparse
import base64
import io
import json
from pathlib import Path

ROWS = {"gsm8k": 3, "math500": 3, "aime2025": 2, "aime2026": 2, "gpqa": 3, "ifeval": 3,
        "pool_gsm8k": 2, "pool_math": 1, "pool_aime": 2, "pool_ifeval_like": 2}
IMAGE_COLS = ["image"] + [f"image_{k}" for k in range(1, 8)]


def encode(v):
    try:
        from PIL import Image
        if isinstance(v, Image.Image):
            im = v.convert("RGB")
            im.thumbnail((96, 96))
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return {"__png_b64__": base64.b64encode(buf.getvalue()).decode()}
    except ImportError:
        pass
    if isinstance(v, dict):
        return {k: encode(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [encode(x) for x in v]
    return v


def spread(n: int, k: int) -> list[int]:
    return sorted({round(i * (n - 1) / max(1, k - 1)) for i in range(k)}) if n else []


def pick(key: str, ds) -> list[int]:
    """Row indices to keep for one load_dataset call."""
    repo = key.split("|")[0]
    n = len(ds)
    cols = [c for c in ds.column_names if c not in IMAGE_COLS]
    light = ds.select_columns(cols)
    if repo == "lmms-lab/MMMU":
        qt, imgs = light["question_type"], [sum(ds[i][c] is not None for c in IMAGE_COLS[1:]) for i in range(min(n, 120))]
        mc = [i for i in range(len(imgs)) if qt[i] == "multiple-choice"]
        multi = [i for i in mc if imgs[i] > 1][:1]
        return sorted(set(multi + [i for i in mc if i not in multi][:2 - len(multi)]
                          + [i for i in range(n) if qt[i] != "multiple-choice"][:1]))
    if repo == "echo840/OCRBench":
        seen, out = set(), []
        for i, t in enumerate(light["question_type"]):
            if t not in seen:
                seen.add(t)
                out.append(i)
            if len(out) == 3:
                break
        return out
    if repo == "TIGER-Lab/MMLU-Pro":
        from flotilla.router_data import STEM
        stem = [i for i, c in enumerate(light["category"]) if c.lower() in STEM]
        lens = {i: len(light[i]["options"]) for i in stem[:2000]}
        ten = [i for i in lens if lens[i] == 10][:2]
        few = min(lens, key=lambda i: lens[i])
        return sorted(set(ten + [few]))
    if repo == "di-zhang-fdu/AIME_1983_2024":
        years = light["Year"]
        parted = [i for i, p in enumerate(light["Part"]) if p and int(years[i]) <= 2024][:1] if "Part" in cols else []
        return sorted(set(parted + [i for i in range(n) if int(years[i]) <= 2024][:2 - len(parted)]))
    name = {"openai/gsm8k": "gsm8k", "HuggingFaceH4/MATH-500": "math500", "MathArena/aime_2025": "aime2025",
            "MathArena/aime_2026": "aime2026", "Idavidrein/gpqa": "gpqa", "google/IFEval": "ifeval",
            "EleutherAI/hendrycks_math": "pool_math", "allenai/RLVR-IFeval": "pool_ifeval_like"}.get(repo)
    if key.startswith("openai/gsm8k") and key.endswith("|train"):
        name = "pool_gsm8k"
    return spread(n, ROWS.get(name, 2))


# GPQA asks that its examples not be published online, so the committed GPQA sample rows are made up: GPQA's own
# columns (so the loader and the format test see the real shape) with invented questions and empty validator fields.
SYNTHETIC_GPQA = [
    ("A ball is dropped from rest. Ignoring air resistance, how far does it fall in the first 2 seconds (g = 10 m/s^2)?",
     "20 m", "10 m", "40 m", "5 m", "Physics"),
    ("Which gas makes up the largest share of dry air at sea level?", "nitrogen", "oxygen", "argon", "carbon dioxide",
     "Chemistry (general)"),
    ("A gene has two alleles, A and a. Two Aa parents have a child. What is the chance the child is aa?",
     "1/4", "1/2", "3/4", "0", "Genetics"),
]


def synthetic_gpqa(columns: list[str]) -> list[dict]:
    rows = []
    for k, (q, right, w1, w2, w3, sub) in enumerate(SYNTHETIC_GPQA):
        r = {c: "" for c in columns}
        r.update({"Question": q, "Correct Answer": right, "Incorrect Answer 1": w1, "Incorrect Answer 2": w2,
                  "Incorrect Answer 3": w3, "Subdomain": sub, "Record ID": f"recSYNTHETIC{k:05d}",
                  "Explanation": "made-up row for Flotilla's format test, not from GPQA"})
        rows.append(r)
    return rows


def recorder(mod, store: dict):
    real = mod.load_dataset

    def load(repo, config=None, split=None):
        ds = real(repo, config, split)
        key = f"{repo}|{config}|{split}"
        idx = pick(key, ds)
        store[key] = [encode(dict(ds[i])) for i in idx]
        return [dict(ds[i]) for i in idx]
    return load


def lcb_rows(root: Path, window: tuple[str, str] | None, before: str | None) -> list[dict]:
    from flotilla.router_data import _lcb_private
    rows = []
    for f in sorted(root.glob("test*.jsonl")):
        for line in open(f):
            ex = json.loads(line)
            d = ex["contest_date"][:10]
            if (window and window[0] <= d <= window[1]) or (before and d < before):
                ex["_file"] = f.name
                rows.append(ex)
    stdin = lambda ex: all(t.get("testtype") == "stdin" for t in json.loads(ex["public_test_cases"]))
    size = lambda ex: len(ex["private_test_cases"])
    s = sorted((r for r in rows if stdin(r)), key=size)[:1 if window else 2]
    fn = sorted((r for r in rows if not stdin(r)), key=size)[:1] if window else []
    out = s + fn
    for r in out:
        _lcb_private(r["private_test_cases"])  # must decode
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--smalltest", required=True, help="exported dev items (ruler_32k.jsonl, ruler_64k.jsonl)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download
    from flotilla import router_data, splits

    raw = {}
    splits.load_dataset = recorder(splits, raw)
    for name, fn in splits.BENCHES.items():
        if name != "lcb":
            n = sum(1 for _ in fn())
            print(f"{name}: {n} sample items")
    router_data.load_dataset = recorder(router_data, raw)
    for name in ("gsm8k", "math", "aime", "mmlu_pro", "ifeval_like"):
        print(f"pool {name}: {sum(1 for _ in router_data.SOURCES[name]())} sample items")
    root = Path(snapshot_download("livecodebench/code_generation_lite", repo_type="dataset", local_files_only=True))
    raw["lcb|bench"] = lcb_rows(root, splits.LCB_WINDOW, None)
    raw["lcb|pool"] = lcb_rows(root, None, router_data.LCB_TEST_WINDOW_START)
    for key in [k for k in raw if k.startswith("Idavidrein/gpqa|")]:
        raw[key] = synthetic_gpqa(list(raw[key][0]))
    (out / "raw_rows.json").write_text(json.dumps(raw, ensure_ascii=False, indent=0))

    ruler = []
    for bench, want in (("ruler_32k", ("niah_single_1", "ruler_qa_squad", "ruler_cwe")), ("ruler_64k", ("ruler_vt",))):
        for line in open(Path(a.smalltest) / f"{bench}.jsonl"):
            it = json.loads(line)
            if it["ruler_task"] in want and it["ruler_task"] not in {r["ruler_task"] for r in ruler if r["bench"] == bench}:
                t = it["task"]
                it["task"] = t[:1500] + "\n[... haystack cut for the test sample ...]\n" + t[-1500:]
                it["trimmed_for_tests"] = {"chars": len(t)}
                ruler.append(it)
    with open(out / "ruler_items.jsonl", "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in ruler)
    print({k: len(v) for k, v in raw.items()}, "ruler", len(ruler))


if __name__ == "__main__":
    main()
