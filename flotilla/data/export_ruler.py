# Sources: ruler, lm-eval, squad, hotpotqa, paul-graham-essays (docs/reference/REFERENCES.md)
"""RULER items (protocol 1, row 9): lm-eval `ruler` group, 13 tasks, max_seq_lengths 32768 and 65536, 50 per task per length.

lm-eval hard-codes num_samples=500 in every RULER generator and its metadata has no sample-count option, so this script
builds the group exactly as `lm_eval --tasks ruler --metadata '{"max_seq_lengths":[32768,65536]}'` would (same seeds,
same task order, all 500 samples per task per length; generation draws from shared RNG state, so the first 50 are only
reproducible this way) and keeps the first 50 per task per length (per-length sample index 0..49).
Prompts are the exact plain-text contexts lm-eval sends (no chat template), including the task's gen_prefix answer prefix.

Login node (internet), once:  python -m flotilla.data.export_ruler --prefetch
Compute node (offline):       python -m flotilla.data.export_ruler --out $SCRATCH/flotilla
Writes <out>/smalltest/ruler_{32k,64k}.jsonl (dev items), <out>/ruler/ruler_{32k,64k}_full.jsonl (all 650) and
<out>/splits/ruler_{32k,64k}.json.
"""
import argparse
import importlib.metadata
import inspect
import json
import os
import random
from pathlib import Path

SEED = 20261119
TOKENIZER = "Qwen/Qwen3.8-27B"
LENGTHS = {32768: "ruler_32k", 65536: "ruler_64k"}
N_PER_TASK = 50
N_DEV = 33                      # 5% of 13 x 50 = 650
CACHE = Path(os.environ.get("SCRATCH", ".")) / "flotilla" / "cache" / "ruler"
QA_URLS = {"https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json": "squad_dev_v2.0.json",
           "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json": "hotpot_dev_distractor_v1.json"}
os.environ.setdefault("NLTK_DATA", str(CACHE / "nltk_data"))   # $HOME is read-only on compute nodes


def prefetch() -> None:
    """Download everything lm-eval's ruler utils fetch at build time (compute nodes are offline)."""
    import datasets
    import nltk
    import requests
    CACHE.mkdir(parents=True, exist_ok=True)
    for url, name in QA_URLS.items():
        if not (CACHE / name).exists():
            r = requests.get(url, timeout=600)
            r.raise_for_status()
            (CACHE / name).write_bytes(r.content)
        print("have", name, (CACHE / name).stat().st_size, flush=True)
    nltk.download("punkt_tab", download_dir=os.environ["NLTK_DATA"])
    datasets.load_dataset("baber/paul_graham_essays", split="train")
    from transformers import AutoTokenizer
    AutoTokenizer.from_pretrained(TOKENIZER)
    import wonderwords  # noqa: F401  (word lists ship with the package)
    print("prefetch done", flush=True)


def offline_requests() -> None:
    """Serve the two QA JSON downloads from the prefetched files (same bytes lm-eval would download)."""
    import requests

    real_get = requests.get

    class Resp:
        def __init__(self, path):
            self.content = path.read_bytes()
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(self.content)

    def get(url, *a, **k):
        if url in QA_URLS:
            return Resp(CACHE / QA_URLS[url])
        return real_get(url, *a, **k)

    requests.get = get


def ruler_item(bench: str, name: str, k: int, inst, n_tokens: int) -> dict:
    """One lm-eval RULER request as a Flotilla item: the prompt as lm-eval builds it, every reference output as gold."""
    return {"item_id": f"{bench}/{name}/{k}", "bench": bench, "task_type": "long_context", "task": inst.args[0],
            "gold": list(inst.doc["outputs"]), "ruler_task": name, "scorer": "ruler_substring",
            "n_tokens_qwen": n_tokens, "lm_eval_doc_id": inst.doc_id}


def build(lengths):
    """Return {task_name: [Instance]} built as lm_eval.simple_evaluate builds them."""
    import numpy as np
    from lm_eval import utils as lu
    from lm_eval.tasks import TaskManager, get_task_dict
    random.seed(getattr(lu, "DEFAULT_RANDOM_SEED", 0))           # simple_evaluate's seeding, same order
    np.random.seed(getattr(lu, "DEFAULT_OTHER_SEED", 1234))
    try:
        from lm_eval.utils import set_torch_seed
        set_torch_seed(getattr(lu, "DEFAULT_OTHER_SEED", 1234))
    except ImportError:
        import torch
        torch.manual_seed(getattr(lu, "DEFAULT_OTHER_SEED", 1234))
    tm = TaskManager(metadata={"pretrained": TOKENIZER, "max_seq_lengths": list(lengths)})
    td = get_task_dict(["ruler"], tm)

    def leaves(d):
        for k, v in d.items():
            if isinstance(v, dict):
                yield from leaves(v)
            else:
                yield v
    out = {}
    for task in leaves(td):
        sig = inspect.signature(task.build_all_requests).parameters
        kw = {k: v for k, v in dict(limit=None, rank=0, world_size=1, apply_chat_template=False,
                                    cache_requests=False, rewrite_requests_cache=False).items() if k in sig}
        task.build_all_requests(**kw)
        out[task.config.task] = task.instances
        print(f"built {task.config.task}: {len(task.instances)} requests", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefetch", action="store_true")
    ap.add_argument("--out", default=str(Path(os.environ.get("SCRATCH", ".")) / "flotilla"))
    ap.add_argument("--lengths", type=int, nargs="*", default=list(LENGTHS))   # override only for smoke tests
    a = ap.parse_args()
    if a.prefetch:
        prefetch()
        return
    offline_requests()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    version = importlib.metadata.version("lm_eval")
    insts = build(a.lengths)
    out = Path(a.out)
    for d in ("smalltest", "ruler", "splits"):
        (out / d).mkdir(parents=True, exist_ok=True)
    for L in a.lengths:
        bench = LENGTHS.get(L, f"ruler_{L // 1024}k")
        items = []
        for name, inst_list in insts.items():
            kept = [i for i in inst_list if i.doc["max_length"] == L][:N_PER_TASK]   # first 50 of 500, generation order
            assert len(kept) == N_PER_TASK, (name, L, len(kept))
            for k, inst in enumerate(kept):
                assert inst.doc.get("index", k) == k, (name, L, k, inst.doc.get("index"))
                items.append(ruler_item(bench, name, k, inst, len(tok(inst.args[0]).input_ids)))
        ids = [it["item_id"] for it in items]
        assert len(ids) == len(set(ids)) == 13 * N_PER_TASK, len(ids)
        dev = set(random.Random(f"{SEED}-{bench}").sample(ids, N_DEV))   # same draw rule as flotilla.data.splits
        (out / "splits" / f"{bench}.json").write_text(json.dumps({
            "bench": bench, "seed": SEED, "n_total": len(ids), "n_dev": len(dev),
            "dev": [i for i in ids if i in dev], "test": [i for i in ids if i not in dev],
            "source": f"lm_eval {version} ruler, tokenizer {TOKENIZER}", "created": "2026-11-19"}, indent=1))
        with open(out / "ruler" / f"{bench}_full.jsonl", "w") as f_all, open(out / "smalltest" / f"{bench}.jsonl", "w") as f_dev:
            for it in items:
                line = json.dumps(it, ensure_ascii=False) + "\n"
                f_all.write(line)
                if it["item_id"] in dev:
                    f_dev.write(line)
        dv = [it for it in items if it["item_id"] in dev]
        print(f"{bench}: total {len(items)}, dev {len(dv)}, mean tokens all "
              f"{sum(i['n_tokens_qwen'] for i in items) / len(items):.0f}, dev {sum(i['n_tokens_qwen'] for i in dv) / len(dv):.0f}, "
              f"max {max(i['n_tokens_qwen'] for i in items)}", flush=True)


if __name__ == "__main__":
    main()
