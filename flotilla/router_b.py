"""Router B: our own classifier (ModernBERT-base) trained on which model answers which non-test question
correctly (protocol 4.5, 5). Two heads on one encoder:
  task_type  (softmax over the router's task types)
  p_correct  (one sigmoid per solver model: chance that model answers this question correctly)
Routing: the solver with the highest p_correct; both solvers when they are within MARGIN of each other.

Train:  python -m flotilla.router_b train --pool pool.clean.jsonl --labels qwen=labels_qwen.jsonl phi=labels_phi.jsonl --out DIR
Route:  RouterB(DIR).route(task) -> same fields as router A
"""
import argparse
import json
import random
import time
from pathlib import Path

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer

from flotilla.router_a import DEFAULT_TABLE, LONG_CONTEXT_CHARS

BASE = "answerdotai/ModernBERT-base"
TYPES = ["math", "code", "science_mc", "instruction", "legal", "general"]
MARGIN = 0.10
SEED = 20261119


class Net(nn.Module):
    def __init__(self, base: str, n_models: int):
        super().__init__()
        self.enc = AutoModel.from_pretrained(base)
        h = self.enc.config.hidden_size
        self.type_head = nn.Linear(h, len(TYPES))
        self.correct_head = nn.Linear(h, n_models)

    def forward(self, **batch):
        x = self.enc(**batch).last_hidden_state[:, 0]
        return self.type_head(x), self.correct_head(x)


def load_rows(pool: str, labels: dict[str, str]) -> tuple[list[dict], list[str]]:
    items = {json.loads(l)["id"]: json.loads(l) for l in open(pool)}
    models = list(labels)
    got: dict[str, dict] = {}
    for m, path in labels.items():
        for line in open(path):
            r = json.loads(line)
            if r["id"] in items:
                got.setdefault(r["id"], {})[m] = bool(r["correct"])
    rows = [{"task": items[i]["task"], "type": TYPES.index(items[i]["task_type"]), "correct": [float(v[m]) for m in models], "id": i}
            for i, v in got.items() if all(m in v for m in models)]
    return rows, models


def train(a) -> None:
    labels = dict(kv.split("=", 1) for kv in a.labels)
    rows, models = load_rows(a.pool, labels)
    random.Random(SEED).shuffle(rows)
    n_val = max(50, len(rows) // 10)
    val, tr = rows[:n_val], rows[n_val:]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(BASE)
    net = Net(BASE, len(models)).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
    ce, bce = nn.CrossEntropyLoss(), nn.BCEWithLogitsLoss()

    def batches(rs, bs, shuffle):
        rs = list(rs)
        if shuffle:
            random.shuffle(rs)
        for i in range(0, len(rs), bs):
            b = rs[i:i + bs]
            enc = tok([r["task"] for r in b], truncation=True, max_length=a.max_len, padding=True, return_tensors="pt").to(dev)
            yield b, enc, torch.tensor([r["type"] for r in b], device=dev), torch.tensor([r["correct"] for r in b], device=dev)

    @torch.no_grad()
    def evaluate():
        net.eval()
        ok_type = ok_route = oracle = n = 0
        for b, enc, yt, yc in batches(val, 64, False):
            lt, lc = net(**enc)
            ok_type += (lt.argmax(-1) == yt).sum().item()
            pick = torch.sigmoid(lc).argmax(-1)
            ok_route += yc[torch.arange(len(b)), pick].sum().item()
            oracle += (yc.max(-1).values).sum().item()
            n += len(b)
        net.train()
        return {"type_acc": round(ok_type / n, 4), "routed_acc": round(ok_route / n, 4), "oracle_acc": round(oracle / n, 4),
                **{f"{m}_alone_acc": round(sum(r["correct"][k] for r in val) / n, 4) for k, m in enumerate(models)}}

    t0, log = time.time(), []
    torch.manual_seed(SEED)
    for ep in range(a.epochs):
        for b, enc, yt, yc in batches(tr, a.bs, True):
            lt, lc = net(**enc)
            loss = ce(lt, yt) + bce(lc, yc)
            opt.zero_grad()
            loss.backward()
            opt.step()
        log.append({"epoch": ep + 1, **evaluate()})
        print(json.dumps(log[-1]), flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), out / "router_b.pt")
    tok.save_pretrained(out)
    meta = {"base": BASE, "models": models, "types": TYPES, "margin": MARGIN, "train_items": len(tr), "val_items": len(val),
            "epochs": a.epochs, "lr": a.lr, "max_len": a.max_len, "seconds": round(time.time() - t0, 1), "val_log": log}
    (out / "router_b.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "val_log"}), flush=True)


class RouterB:
    def __init__(self, path: str, table: dict | None = None, device: str | None = None):
        self.meta = json.loads((Path(path) / "router_b.json").read_text())
        self.dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = AutoTokenizer.from_pretrained(path)
        self.net = Net(self.meta["base"], len(self.meta["models"])).to(self.dev).eval()
        self.net.load_state_dict(torch.load(Path(path) / "router_b.pt", map_location=self.dev))
        self.table = table or dict(DEFAULT_TABLE)

    @torch.no_grad()
    def route(self, task: str, has_image: bool = False) -> dict:
        t0 = time.time()
        if has_image or len(task) > LONG_CONTEXT_CHARS:
            ttype = "vision" if has_image else "long_context"
            row = self.table[ttype]
            return {"router": "B:modernbert", "task_type": ttype, "how": "rule", "models": row["models"], "tools": row["tools"],
                    "p_correct": {}, "latency_s": round(time.time() - t0, 4)}
        enc = self.tok([task], truncation=True, max_length=self.meta["max_len"], return_tensors="pt").to(self.dev)
        lt, lc = self.net(**enc)
        ttype = self.meta["types"][int(lt.argmax(-1))]
        p = torch.sigmoid(lc)[0].tolist()
        models = self.meta["models"]
        best = max(range(len(p)), key=lambda k: p[k])
        chosen = [models[k] for k in sorted(range(len(p)), key=lambda k: -p[k]) if p[best] - p[k] <= self.meta["margin"]]
        return {"router": "B:modernbert", "task_type": ttype, "how": "classifier", "models": chosen,
                "tools": self.table.get(ttype, self.table["general"])["tools"],
                "p_correct": {m: round(v, 4) for m, v in zip(models, p)}, "latency_s": round(time.time() - t0, 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--pool", required=True)
    t.add_argument("--labels", nargs="+", required=True, help="model=path/to/labels.jsonl")
    t.add_argument("--out", required=True)
    t.add_argument("--epochs", type=int, default=3)
    t.add_argument("--lr", type=float, default=3e-5)
    t.add_argument("--bs", type=int, default=16)
    t.add_argument("--max-len", type=int, default=1024)
    a = ap.parse_args()
    if a.cmd == "train":
        train(a)


if __name__ == "__main__":
    main()
