# Sources: ngram-leakage, bge-small, gsm8k, math500, matharena, gpqa, ifeval, livecodebench (docs/reference/REFERENCES.md)
"""Leakage check (PROTOCOL.md section 5): flag any training/corpus item that shares a 13-word sequence with,
or has embedding cosine similarity >= 0.95 to, any test item. Flagged items are dropped.

    python -m flotilla.leakage --pool $SCRATCH/flotilla/router/pool.jsonl --report reports/leakage/router_pool.json
Writes <pool>.clean.jsonl next to the pool and a JSON report with counts per source and every flagged pair.
"""
import argparse
import json
import re
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModel, AutoTokenizer

from flotilla.data import load

N = 13
SIM = 0.95
# A 13-gram found in this many different test questions is shared template wording (AIME's "m and n are
# relatively prime positive integers", AtCoder input boilerplate, IFEval constraint templates), not a copy of
# one question; such n-grams are ignored. Protocol clarification 2026-11-19 (see PROTOCOL.md section 5).
TEMPLATE_DF = 2
# Same idea from the other side: a 13-gram shared by this many pool items is template wording too (it matched
# e.g. "your entire response should be in english and in all lowercase letters" in 23 pool items); a copied
# test question would match one pool item, not many.
POOL_TEMPLATE_DF = 3
LCB_WINDOW = ("2024-08-01", "2025-05-01")


def _get(ex: dict, *keys: str) -> str:
    for k in keys:
        if k in ex and ex[k]:
            return str(ex[k])
    raise KeyError(f"none of {keys} in {list(ex)}")


def test_items() -> tuple[dict[str, list[str]], list[str]]:
    sets: dict[str, list[str]] = {}
    missing = []
    sets["gsm8k_test"] = [ex["question"] for ex in load("openai/gsm8k", "main", split="test")]
    sets["math500"] = [ex["problem"] for ex in load("HuggingFaceH4/MATH-500", split="test")]
    # one source per exam: opencompass/AIME2025 duplicates MathArena's AIME 2025 I and would make every
    # AIME 2025 phrase look like a shared template (see TEMPLATE_DF below)
    for name, repo in [("aime2025", "MathArena/aime_2025"), ("aime2026", "MathArena/aime_2026")]:
        try:
            ds = load(repo, split="train")
            sets[name] = [_get(ex, "problem", "question", "Problem") for ex in ds]
        except Exception as e:  # noqa: BLE001
            missing.append(f"{repo}: {type(e).__name__}: {str(e)[:120]}")
    sets["ifeval"] = [ex["prompt"] for ex in load("google/IFEval", split="train")]
    root = Path(snapshot_download("livecodebench/code_generation_lite", repo_type="dataset", local_files_only=True))
    lcb = []
    for f in sorted(root.glob("test*.jsonl")):
        for line in open(f):
            ex = json.loads(line)
            if LCB_WINDOW[0] <= ex["contest_date"][:10] <= LCB_WINDOW[1]:
                lcb.append(ex["question_content"])
    sets["lcb_test_window"] = lcb
    try:
        sets["gpqa_diamond"] = [ex["Question"] for ex in load("Idavidrein/gpqa", "gpqa_diamond", split="train")]
    except Exception as e:  # noqa: BLE001
        missing.append(f"Idavidrein/gpqa: {type(e).__name__} (gated; needs an HF token)")
    return sets, missing


_SPEC = re.compile(r"\n\s*(Input|Output|Constraints|Sample Input|Example 1|Examples?)\s*:?\s*\n", re.I)


def statement(text: str) -> str:
    """For code problems, the n-gram check compares only the problem statement: constraint lines and sample
    I/O numbers repeat across unrelated problems. Other texts are unchanged."""
    m = _SPEC.search(text)
    return text[: m.start()] if m and m.start() > 80 else text


def ngrams(text: str) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9]+", statement(text).lower())
    return {tuple(w[i:i + N]) for i in range(len(w) - N + 1)}


@torch.no_grad()
def embed(texts: list[str], tok, model, device: str, bs: int = 64) -> torch.Tensor:
    out = []
    for i in range(0, len(texts), bs):
        b = tok(texts[i:i + bs], padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
        cls = model(**b).last_hidden_state[:, 0]
        out.append(torch.nn.functional.normalize(cls, dim=-1).float().cpu())
    return torch.cat(out)


def extra_targets(specs: list[str]) -> dict[str, list[str]]:
    """NAME=JSONL pairs -> {NAME: [each line's "task" (or "text"), non-empty]}: sets checked like the test sets (the chat
    guide's source is checked against LongMemEval this way, 2026-11-22)."""
    out = {}
    for spec in specs:
        name, path = spec.split("=", 1)
        out[name] = [t for t in (json.loads(l).get("task") or json.loads(l).get("text") or "" for l in open(path)) if t.strip()]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--embedder", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--extra-targets", nargs="*", default=[], metavar="NAME=JSONL",
                    help="more sets to check against besides the test sets, e.g. longmemeval=units.jsonl (each line's task)")
    a = ap.parse_args()

    pool = [json.loads(l) for l in open(a.pool)]
    sets, missing = test_items()
    sets.update(extra_targets(a.extra_targets))
    test_texts, test_src = [], []
    gram_index: dict[tuple[str, ...], int] = {}
    gram_df: dict[tuple[str, ...], int] = {}
    for name, items in sets.items():
        for t in items:
            idx = len(test_texts)
            test_texts.append(t)
            test_src.append(name)
            for g in ngrams(t):
                gram_index.setdefault(g, idx)
                gram_df[g] = gram_df.get(g, 0) + 1
    strict_index = dict(gram_index)
    templates = {g for g, df in gram_df.items() if df >= TEMPLATE_DF}
    pool_df: dict[tuple[str, ...], int] = {}
    for p in pool:
        for g in ngrams(p["task"]):
            if g in gram_index:
                pool_df[g] = pool_df.get(g, 0) + 1
    templates |= {g for g, df in pool_df.items() if df >= POOL_TEMPLATE_DF}
    gram_index = {g: i for g, i in gram_index.items() if g not in templates}
    strict_flagged = sum(1 for p in pool if any(g in strict_index for g in ngrams(p["task"])))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(a.embedder)
    model = AutoModel.from_pretrained(a.embedder).to(device).eval()
    te = embed(test_texts, tok, model, device)
    pe = embed([p["task"] for p in pool], tok, model, device)

    flagged = []
    for i, p in enumerate(pool):
        hit = next((gram_index[g] for g in ngrams(p["task"]) if g in gram_index), None)
        sims = pe[i] @ te.T
        j = int(sims.argmax())
        if hit is not None or float(sims[j]) >= SIM:
            k = hit if hit is not None else j
            flagged.append({"pool_id": p["id"], "source": p["source"], "test_set": test_src[k], "reason": "13-gram" if hit is not None else "embedding",
                            "similarity": round(float(sims[k]), 4), "pool_text": p["task"][:300], "test_text": test_texts[k][:300]})
    bad = {f["pool_id"] for f in flagged}
    clean = Path(a.pool).with_suffix(".clean.jsonl")
    with open(clean, "w") as f:
        for p in pool:
            if p["id"] not in bad:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    per_source: dict[str, dict[str, int]] = {}
    for p in pool:
        s = per_source.setdefault(p["source"], {"items": 0, "flagged": 0})
        s["items"] += 1
        s["flagged"] += p["id"] in bad
    report = {"method": f"{N}-gram overlap (ignoring template n-grams found in >= {TEMPLATE_DF} test questions or >= {POOL_TEMPLATE_DF} pool items: {len(templates)}) "
                        f"or {a.embedder} cosine >= {SIM}",
              "strict_13gram_flagged_without_template_filter": strict_flagged,
              "test_sets": {k: len(v) for k, v in sets.items()},
              "test_sets_missing": missing, "pool_items": len(pool), "flagged": len(flagged), "kept": len(pool) - len(bad),
              "per_source": per_source, "flagged_items": flagged}
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "flagged_items"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
