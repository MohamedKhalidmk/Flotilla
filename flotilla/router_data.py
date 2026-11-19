"""Router B training pool (protocol 5): non-test questions with gold answers, from sources disjoint from the
test sets by split, year or release date. A leakage check (flotilla.leakage) runs before training and
drops anything flagged.

    python -m flotilla.router_data --out $SCRATCH/flotilla/router/pool.jsonl
Each line: {id, source, task_type, task, gold, options?, tests?}
"""
import argparse
import base64
import json
import pickle
import random
import re
import zlib
from pathlib import Path

from flotilla.data import load as load_dataset
from huggingface_hub import snapshot_download

SEED = 20261119
CAPS = {"gsm8k": 800, "math": 1200, "aime": 10_000, "mmlu_pro": 800, "ifeval_like": 800, "lcb": 600}
LCB_TEST_WINDOW_START = "2024-08-01"   # protocol 1.3: test window 2024-08-01 .. 2025-05-01; train strictly before
STEM = {"math", "physics", "chemistry", "biology", "engineering", "computer science"}


def boxed(sol: str) -> str | None:
    i = sol.rfind("\\boxed")
    if i < 0:
        return None
    j, depth = sol.find("{", i), 0
    for k in range(j, len(sol)):
        depth += sol[k] == "{"
        depth -= sol[k] == "}"
        if depth == 0:
            return sol[j + 1:k]
    return None


def gsm8k():
    for i, ex in enumerate(load_dataset("openai/gsm8k", "main", split="train")):
        yield {"id": f"gsm8k-train-{i}", "source": "gsm8k", "task_type": "math", "task": ex["question"],
               "gold": ex["answer"].split("####")[-1].strip().replace(",", "")}


def math_train():
    subjects = ["algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory", "prealgebra", "precalculus"]
    for s in subjects:
        for i, ex in enumerate(load_dataset("EleutherAI/hendrycks_math", s, split="train")):
            g = boxed(ex["solution"])
            if g:
                yield {"id": f"math-train-{s}-{i}", "source": "math", "task_type": "math", "task": ex["problem"], "gold": g, "level": ex.get("level")}


def aime_pre2025():
    for ex in load_dataset("di-zhang-fdu/AIME_1983_2024", split="train"):
        if int(ex["Year"]) <= 2024:
            yield {"id": f"aime-{ex['Year']}-{ex.get('Part', '')}-{ex['Problem Number']}", "source": "aime", "task_type": "math",
                   "task": ex["Question"], "gold": str(ex["Answer"]).strip()}


def mmlu_pro_stem():
    for ex in load_dataset("TIGER-Lab/MMLU-Pro", split="test"):
        if ex["category"].lower() in STEM:
            yield {"id": f"mmlupro-{ex['question_id']}", "source": "mmlu_pro", "task_type": "science_mc",
                   "task": ex["question"] + "\n\n" + "\n".join(f"{chr(65 + k)}. {o}" for k, o in enumerate(ex["options"])),
                   "options": ex["options"], "gold": ex["answer"]}


def ifeval_like():
    for i, ex in enumerate(load_dataset("allenai/RLVR-IFeval", split="train")):
        msgs = ex["messages"]
        task = msgs[-1]["content"] if isinstance(msgs, list) else str(msgs)
        yield {"id": f"rlvrif-{i}", "source": "ifeval_like", "task_type": "instruction", "task": task, "gold": None,
               "constraint": ex.get("constraint")}


def _lcb_private(raw: str) -> list[dict]:
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return json.loads(pickle.loads(zlib.decompress(base64.b64decode(raw.encode("utf-8")))))


def lcb_before_window():
    root = Path(snapshot_download("livecodebench/code_generation_lite", repo_type="dataset"))
    for f in sorted(root.glob("test*.jsonl")):
        for line in open(f):
            ex = json.loads(line)
            if ex["contest_date"][:10] >= LCB_TEST_WINDOW_START:
                continue
            public = json.loads(ex["public_test_cases"])
            if not public or any(t.get("testtype") != "stdin" for t in public):
                continue  # stdin/stdout problems only (our sandbox grader)
            tests = public + [t for t in _lcb_private(ex["private_test_cases"]) if t.get("testtype") == "stdin"]
            yield {"id": f"lcb-{ex['question_id']}", "source": "lcb", "task_type": "code", "contest_date": ex["contest_date"][:10],
                   "task": ex["question_content"] + "\n\nRead from standard input and write to standard output.",
                   "gold": None, "public_tests": public, "tests": tests[:20]}


SOURCES = {"gsm8k": gsm8k, "math": math_train, "aime": aime_pre2025, "mmlu_pro": mmlu_pro_stem,
           "ifeval_like": ifeval_like, "lcb": lcb_before_window}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(SEED)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with open(out, "w") as f:
        for name, fn in SOURCES.items():
            try:
                items = list(fn())
            except Exception as e:  # noqa: BLE001 - report and continue with the other sources
                print(f"source {name} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
                continue
            rng.shuffle(items)
            items = items[: CAPS[name]]
            counts[name] = len(items)
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
    (out.parent / "pool_counts.json").write_text(json.dumps(counts, indent=2))
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
