# Sources: bge-small, scikit-learn (docs/reference/REFERENCES.md)
"""Router B baseline: frozen question embeddings (bge-small) + logistic regression, one model per head.

Same data, labels and held-out 10% as router_b.py (ModernBERT-base fine-tune), so the two compare directly:
    python -m flotilla.router_b_lite --pool pool.clean.jsonl --labels qwen=labels_qwen.jsonl gptoss=labels_gptoss.jsonl \
        --out DIR
Heads: task type (multinomial) and, per solver model, P(correct). Routing picks the model with the highest P(correct).
Reports the same numbers as router_b's evaluate(): type accuracy, routed accuracy, each model alone, perfect router.
"""
import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from transformers import AutoModel, AutoTokenizer

from flotilla.router_b import TYPES, load_rows, split

EMBEDDER = "BAAI/bge-small-en-v1.5"


@torch.no_grad()
def embed(texts: list[str], bs: int = 64, max_len: int = 512) -> np.ndarray:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(EMBEDDER)
    model = AutoModel.from_pretrained(EMBEDDER).to(dev).eval()
    out = []
    for i in range(0, len(texts), bs):
        enc = tok(texts[i:i + bs], truncation=True, max_length=max_len, padding=True, return_tensors="pt").to(dev)
        cls = model(**enc).last_hidden_state[:, 0]  # bge uses the CLS vector, L2-normalised
        out.append(torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
    return np.concatenate(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--labels", nargs="+", required=True, help="model=path/to/labels.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--C", type=float, default=1.0)
    a = ap.parse_args()
    t0 = time.time()
    rows, models = load_rows(a.pool, dict(kv.split("=", 1) for kv in a.labels))
    val, tr = split(rows)
    xt, xv = embed([r["task"] for r in tr]), embed([r["task"] for r in val])
    type_clf = LogisticRegression(C=a.C, max_iter=2000).fit(xt, [r["type"] for r in tr])
    heads = []
    for k in range(len(models)):
        y = [int(r["correct"][k]) for r in tr]
        heads.append(LogisticRegression(C=a.C, max_iter=2000, class_weight="balanced").fit(xt, y) if len(set(y)) > 1 else None)
    p = np.stack([h.predict_proba(xv)[:, 1] if h is not None else np.full(len(val), float(tr[0]["correct"][k]))
                  for k, h in enumerate(heads)], axis=1)
    pick = p.argmax(1)
    yc = np.array([r["correct"] for r in val])
    n = len(val)
    res = {"type_acc": round(float((type_clf.predict(xv) == np.array([r["type"] for r in val])).mean()), 4),
           "routed_acc": round(float(yc[np.arange(n), pick].mean()), 4), "oracle_acc": round(float(yc.max(1).mean()), 4),
           **{f"{m}_alone_acc": round(float(yc[:, k].mean()), 4) for k, m in enumerate(models)},
           "picked": {m: int((pick == k).sum()) for k, m in enumerate(models)}}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "router_lite.pkl", "wb") as f:
        pickle.dump({"embedder": EMBEDDER, "models": models, "types": TYPES, "type_clf": type_clf, "heads": heads}, f)
    meta = {"embedder": EMBEDDER, "models": models, "train_items": len(tr), "val_items": n, "C": a.C,
            "seconds": round(time.time() - t0, 1), "val": res}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
