"""test-04 supervised strategy routers: pick one route per question, straight away, from the question text alone.

    python -m flotilla.strategy_router train    --labels DIR --items GLOB [GLOB ...] --out DIR [--routers label success bge_lr knn]
    python -m flotilla.strategy_router evaluate --labels DIR --items GLOB [GLOB ...] --out DIR [--held-out]
    python -m flotilla.strategy_router dry-run  --labels DIR --items GLOB [GLOB ...] --out DIR [--routers ...]

DIR (--labels) is a graded folder written by flotilla/strategy_labels.py: per_question.jsonl, split.json, summary.json.
--items are the question files (one JSON object per line with "id" or "item_id" and "task"), e.g. the
labelitems_strategy shards; questions are joined to labels by id.

Routes come from the labels, not from this file. An item's available routes are the routes present in its label row
(Memory routes exist only on items that have a memory); every router masks the rest and never picks one of them.

Cost. "Cheapest" orders routes by mean GPU-seconds per question from summary.json (gpu_seconds_job / questions, the
number test-04's table reports). Per-question GPU-seconds for evaluation: the row's own "gpu_seconds" if the labels
carry one, else the route's GPU-seconds per wall-second (summary.json) times the row's wall_seconds, so each route's mean
over all questions equals its table number. Output tokens are the row's tokens_out. summary.json is aggregate job
accounting over the whole run (it also names the best fixed route, as test-04's table does); no per-question
held-out row is read.

Routers (test-04 README, Setup > Routers):
  label    ModernBERT-base classifier over routes; target = cheapest correct available route. Picks the most likely
           available route.
  success  ModernBERT-base, one sigmoid per route = chance the route is right. Picks the cheapest available route with
           p >= tau, tau tuned on dev.
  bge_lr   bge-small CLS embeddings + one logistic regression per route (same rule as success; C and tau tuned on dev).
  knn      bge-small embeddings, cosine k nearest training questions; a route's chance = share of the neighbours (that
           have the route) on which it was right. Same rule as success; k and tau tuned on dev.

Ties. Routes are ordered cheapest first (GPU-seconds; equal costs keep summary.json order). "Cheaper" is judged per
item (2026-11-21): by the row's own per-route gpu_seconds when the labels carry them (LongMemEval's full-history base
routes cost far more than its Memory routes, the pool the other way round), else by that global order; equal per-item
costs fall back to the global order. Every tie between routes goes to the cheaper route: label = cheapest correct
route; argmax ties pick the cheaper route; "cheapest above tau" has no ties by construction; kNN neighbours with equal similarity are taken in training order.
"none" (no route right). label: those items are left out of training (no route is a right answer, so they teach the
classifier nothing about which route works); success / bge_lr / knn: kept, all routes 0, a real signal that the
question is hard. When no available route reaches tau, the router picks the available route with the highest
estimate (cheaper on ties). In evaluation a "none" item is wrong for every router, fixed route and the oracle.

Tuning (dev only). Best fixed route = the keep rule's reference: --best-fixed, else the most accurate route in
summary.json (test-04's table: Vote, 0.967, fixed in the README before any router), among routes available on every
item; its dev accuracy and GPU-seconds are the reference. --tune rule (default) follows test-04's keep
rule: if some setting is more than 1 point + margin better than the reference, take the most accurate (cheaper on
ties); else among settings within (1 point - margin) of it at lower GPU-seconds, take the cheapest; else the most
accurate. --tune accuracy: the most accurate, cheaper on ties. ModernBERT keeps the epoch with the best dev score
(label: routed dev accuracy, success: masked dev BCE).

Held-out is never read unless --held-out is given to evaluate (rows of held-out ids are skipped before parsing).
Seeds: SEED for python, numpy, torch and data order; logged in meta.json with the label-file hashes.
"""
import argparse
import csv
import glob
import hashlib
import json
import pickle
import platform
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SEED = 20261120
MODERNBERT = "answerdotai/ModernBERT-base"
EMBEDDER = "BAAI/bge-small-en-v1.5"
ROUTERS = ["label", "success", "bge_lr", "knn"]
THRESHOLDS = [float(round(x, 2)) for x in np.arange(0.0, 1.0001, 0.01)] + [1.01]  # 1.01: never above, argmax fallback
KS = [1, 3, 5, 10, 20, 50]
CS = [0.1, 1.0, 10.0]
POINT = 0.01
EPS = 1e-9
_ID = re.compile(r'^\{"(?:id|item_id)":\s*"((?:[^"\\]|\\.)*)"')


# ---------------------------------------------------------------- data

@dataclass
class Split:
    name: str
    ids: list
    texts: list
    sources: list
    correct: np.ndarray          # (n, R) 0/1, 0 where unavailable
    mask: np.ndarray             # (n, R) bool, route available on the item
    gpu: np.ndarray              # (n, R) GPU-seconds, 0 where unavailable
    tokens: np.ndarray           # (n, R) output tokens
    routes: list = field(default_factory=list)
    cost: np.ndarray | None = None  # (n, R) per-item cost order: the row's own gpu_seconds, else the route's mean; inf where unavailable

    def __len__(self):
        return len(self.ids)

    def subset(self, idx) -> "Split":
        idx = list(idx)
        return Split(self.name, [self.ids[i] for i in idx], [self.texts[i] for i in idx], [self.sources[i] for i in idx],
                     self.correct[idx], self.mask[idx], self.gpu[idx], self.tokens[idx], self.routes,
                     None if self.cost is None else self.cost[idx])


def route_costs(summary: dict, routes_seen: set) -> tuple[list, dict, dict]:
    """Routes cheapest first, mean GPU-s per question, GPU-s per wall-second (None if unknown)."""
    per = summary["per_strategy"]
    missing = sorted(routes_seen - set(per))
    if missing:
        raise SystemExit(f"routes in the labels but not in summary.json: {missing}")
    cost, rate = {}, {}
    for r in per:
        if r not in routes_seen:
            continue
        s = per[r]
        n = s.get("questions", summary["questions"])
        cost[r] = s["gpu_seconds_per_question"] if "gpu_seconds_per_question" in s else s["gpu_seconds_job"] / n
        wall = s.get("mean_wall_seconds") or 0
        rate[r] = cost[r] / wall if wall > 0 else None
    order = list(per)
    routes = sorted(cost, key=lambda r: (cost[r], order.index(r)))
    return routes, cost, rate


def read_split_ids(labels: Path, names: list[str], held_out_ok: bool) -> dict[str, list]:
    if "held_out" in names and not held_out_ok:
        raise SystemExit("held-out requested without --held-out")
    sp = json.loads((labels / "split.json").read_text())
    return {n: list(sp[n]) for n in names}


def read_rows(labels: Path, wanted: set) -> dict[str, dict]:
    """Label rows for wanted ids only; other ids (held-out) are skipped before their JSON is parsed."""
    rows = {}
    with open(labels / "per_question.jsonl") as f:
        for line in f:
            m = _ID.match(line)
            if m is None:
                raise SystemExit("per_question.jsonl row does not start with its id; cannot skip unread ids safely")
            if json.loads(f'"{m.group(1)}"') in wanted:
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def read_texts(item_globs: list[str], wanted: set) -> dict[str, str]:
    texts = {}
    files = sorted({p for g in item_globs for p in glob.glob(g)})
    if not files:
        raise SystemExit(f"no item files match {item_globs}")
    for p in files:
        with open(p) as f:
            for line in f:
                m = _ID.match(line)
                if m is not None and json.loads(f'"{m.group(1)}"') not in wanted:
                    continue
                r = json.loads(line)
                i = r.get("id", r.get("item_id"))
                if i in wanted and i not in texts:
                    texts[i] = r["task"]
    return texts


def row_routes(row: dict) -> list[str]:
    return [k for k, v in row.items() if isinstance(v, dict) and "correct" in v]


def load(labels: str, items: list[str], names: list[str], held_out_ok: bool = False) -> tuple[dict, dict]:
    """Splits by name plus info {routes, cost, rate, hashes}. Routes = every route seen in the loaded rows."""
    lab = Path(labels)
    ids = read_split_ids(lab, names, held_out_ok)
    wanted = {i for v in ids.values() for i in v}
    rows = read_rows(lab, wanted)
    texts = {i: rows[i]["task"] for i in rows if "task" in rows[i]}
    need = wanted - set(texts)
    if need:
        texts.update(read_texts(items, need))
    lost = sorted(i for i in wanted if i not in rows or i not in texts)
    if lost:
        raise SystemExit(f"{len(lost)} split ids lack a label row or question text, e.g. {lost[:5]}")
    summary = json.loads((lab / "summary.json").read_text())
    seen = {r for i in wanted for r in row_routes(rows[i])}
    routes, cost, rate = route_costs(summary, seen)
    out = {}
    for n, idl in ids.items():
        R, N = len(routes), len(idl)
        c, m, g, t = np.zeros((N, R)), np.zeros((N, R), bool), np.zeros((N, R)), np.zeros((N, R))
        oc = np.full((N, R), np.inf)  # cost order per item (see Ties in the module docstring)
        for a, i in enumerate(idl):
            row = rows[i]
            for b, r in enumerate(routes):
                v = row.get(r)
                if not (isinstance(v, dict) and "correct" in v):
                    continue
                m[a, b], c[a, b], t[a, b] = True, float(bool(v["correct"])), float(v.get("tokens_out") or 0)
                oc[a, b] = float(v["gpu_seconds"]) if v.get("gpu_seconds") is not None else cost[r]
                if v.get("gpu_seconds") is not None:
                    g[a, b] = float(v["gpu_seconds"])
                elif rate[r] is not None and v.get("wall_seconds") is not None:
                    g[a, b] = rate[r] * float(v["wall_seconds"])
                else:
                    g[a, b] = cost[r]
        empty = np.where(~m.any(1))[0]
        if len(empty):
            raise SystemExit(f"{len(empty)} {n} items have no route, e.g. {idl[empty[0]]}")
        out[n] = Split(n, idl, [texts[i] for i in idl], [rows[i]["source"] for i in idl], c, m, g, t, routes, oc)
    hashes = {f: hashlib.sha256((lab / f).read_bytes()).hexdigest()[:16] for f in ("per_question.jsonl", "split.json", "summary.json")}
    acc = {r: v["accuracy"] for r, v in summary["per_strategy"].items() if "accuracy" in v}
    return out, {"summary_accuracy": acc, "routes": routes, "cost_gpu_s": {r: round(cost[r], 3) for r in routes}, "gpu_s_per_wall_s": rate,
                 "label_hashes": hashes, "labels_dir": str(lab)}


# ---------------------------------------------------------------- shared rules

def _cheapest(ok: np.ndarray, cost: np.ndarray | None) -> np.ndarray:
    """Per item, the cheapest route among ok: by the item's own cost row when given (equal costs: the global order,
    i.e. the lower column), else the first ok column (routes are globally cheapest first). Items with no ok route: 0."""
    if cost is None:
        return ok.argmax(1)
    return np.where(ok, cost, np.inf).argmin(1)


def label_index(correct: np.ndarray, mask: np.ndarray, cost: np.ndarray | None = None) -> np.ndarray:
    """Cheapest correct available route per item (per-item costs when given, else routes cheapest first), -1 for "none"."""
    ok = (correct > 0.5) & mask
    return np.where(ok.any(1), _cheapest(ok, cost), -1)


def masked_argmax(score: np.ndarray, mask: np.ndarray, cost: np.ndarray | None = None) -> np.ndarray:
    """Highest score among available routes; ties go to the cheaper route (the item's own costs when given)."""
    z = np.where(mask, score, -np.inf)
    if cost is None:
        return z.argmax(1)
    return _cheapest(mask & (z >= z.max(1, keepdims=True)), cost)


def cheapest_above(p: np.ndarray, mask: np.ndarray, tau: float, cost: np.ndarray | None = None) -> np.ndarray:
    """Cheapest available route with p >= tau (the item's own costs when given); if none reaches tau, the available
    route with the highest p."""
    ok = (p >= tau - EPS) & mask
    return np.where(ok.any(1), _cheapest(ok, cost), masked_argmax(p, mask, cost))


def evaluate(picks: np.ndarray, sp: Split) -> dict:
    n = len(sp)
    picks = np.asarray(picks, int)
    assert picks.shape == (n,)
    if not sp.mask[np.arange(n), picks].all():
        raise AssertionError("a router picked an unavailable route")
    ar = np.arange(n)
    right = sp.correct[ar, picks]
    by_src = defaultdict(list)
    for a, s in enumerate(sp.sources):
        by_src[s].append(a)
    return {"questions": n, "accuracy": float(right.mean()), "gpu_seconds": float(sp.gpu[ar, picks].mean()),
            "output_tokens": float(sp.tokens[ar, picks].mean()),
            "picked": {sp.routes[k]: int(v) for k, v in sorted(Counter(picks.tolist()).items())},
            "by_source": {s: {"questions": len(ix), "accuracy": float(right[ix].mean()),
                              "picked": {sp.routes[k]: int(v) for k, v in sorted(Counter(picks[ix].tolist()).items())}}
                          for s, ix in sorted(by_src.items())}}


def best_fixed(train: Split, summary_acc: dict | None = None, override: str | None = None) -> int:
    """The keep rule's reference route, among routes available on every training item: --best-fixed if given; else the
    highest accuracy in summary.json (the run's own table, fixed in the test-04 README before any router: Vote, 0.967);
    else the highest training accuracy. Cheaper on ties."""
    full = [int(r) for r in np.where(train.mask.all(0))[0]]
    if not full:
        raise SystemExit("no route is available on every training item")
    if override:
        if override not in train.routes or train.routes.index(override) not in full:
            raise SystemExit(f"--best-fixed {override}: not a route available on every item")
        return train.routes.index(override)
    if summary_acc and all(train.routes[r] in summary_acc for r in full):
        return max(full, key=lambda r: (summary_acc[train.routes[r]], -r))
    return max(full, key=lambda r: (train.correct[:, r].mean(), -r))


def oracle_picks(sp: Split) -> np.ndarray:
    lab = label_index(sp.correct, sp.mask, sp.cost)
    return np.where(lab >= 0, lab, _cheapest(sp.mask, sp.cost))  # "none": the cheapest available route (wrong anyway)


def keep_rule(res: dict, ref: dict) -> str:
    d = res["accuracy"] - ref["accuracy"]
    if d > POINT + EPS:
        return "keep (more than 1 point better)"
    if d >= -POINT - EPS and res["gpu_seconds"] < ref["gpu_seconds"]:
        return "keep (within 1 point, less compute)"
    return "drop"


def choose(cands: list[dict], ref: dict, mode: str, margin: float) -> dict:
    """cands: [{params, accuracy, gpu_seconds, ...}] on dev. See the module docstring (Tuning)."""
    most_acc = min(cands, key=lambda c: (-c["accuracy"], c["gpu_seconds"]))
    if mode == "accuracy":
        return most_acc
    better = [c for c in cands if c["accuracy"] > ref["accuracy"] + POINT + margin + EPS]
    if better:
        return most_acc
    cheaper = [c for c in cands if c["accuracy"] >= ref["accuracy"] - POINT + margin - EPS and c["gpu_seconds"] < ref["gpu_seconds"]]
    if cheaper:
        return min(cheaper, key=lambda c: (c["gpu_seconds"], -c["accuracy"]))
    return most_acc


def tune_tau(p: np.ndarray, dev: Split, ref: dict, mode: str, margin: float, extra: dict | None = None) -> tuple[dict, list]:
    cands = []
    for tau in THRESHOLDS:
        r = evaluate(cheapest_above(p, dev.mask, tau, dev.cost), dev)
        cands.append({"params": {**(extra or {}), "tau": tau}, "accuracy": r["accuracy"], "gpu_seconds": r["gpu_seconds"]})
    return choose(cands, ref, mode, margin), cands


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


# ---------------------------------------------------------------- bge-small embeddings (routers 3, 4)

def embed(texts: list[str], device: str | None = None, bs: int = 64, max_len: int = 512) -> np.ndarray:
    import torch
    from transformers import AutoModel, AutoTokenizer
    dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(EMBEDDER)
    model = AutoModel.from_pretrained(EMBEDDER).to(dev).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], truncation=True, max_length=max_len, padding=True, return_tensors="pt").to(dev)
            cls = model(**enc).last_hidden_state[:, 0]  # bge: CLS vector, L2-normalised
            out.append(torch.nn.functional.normalize(cls, dim=-1).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, 384), np.float32)


def cached_embed(out: Path, sp: Split, device: str | None) -> np.ndarray:
    key = hashlib.sha256(("\n".join(sp.ids) + EMBEDDER).encode()).hexdigest()[:12]
    p = out / "embeddings" / f"{sp.name}-{key}.npy"
    if p.exists():
        return np.load(p)
    x = embed(sp.texts, device)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.save(p, x)
    return x


class LRRouter:
    """Router 3: per-route logistic regression on frozen bge-small embeddings."""

    def __init__(self, C: float = 1.0, seed: int = SEED):
        self.C, self.seed, self.heads, self.const = C, seed, {}, {}

    def fit(self, x: np.ndarray, sp: Split) -> "LRRouter":
        from sklearn.linear_model import LogisticRegression
        for r in range(len(sp.routes)):
            m = sp.mask[:, r]
            y = sp.correct[m, r].astype(int)
            if m.sum() == 0:
                self.const[r] = 0.0
            elif len(set(y.tolist())) < 2:
                self.const[r] = float(y[0])
            else:
                self.heads[r] = LogisticRegression(C=self.C, max_iter=5000, random_state=self.seed).fit(x[m], y)
        return self

    def proba(self, x: np.ndarray, n_routes: int) -> np.ndarray:
        p = np.zeros((len(x), n_routes))
        for r in range(n_routes):
            p[:, r] = self.heads[r].predict_proba(x)[:, 1] if r in self.heads else self.const.get(r, 0.0)
        return p


LRRouter.__module__ = "flotilla.strategy_router"  # pickles load from any module, also when run with -m


def knn_proba(x: np.ndarray, xt: np.ndarray, train: Split, k: int) -> np.ndarray:
    """Share of the k nearest training questions (cosine) on which each route was right, over neighbours that have
    the route; a route none of the k neighbours has falls back to its training accuracy."""
    sim = x @ xt.T
    nn = np.argsort(-sim, axis=1, kind="stable")[:, :k]
    c, m = train.correct[nn], train.mask[nn]               # (n, k, R)
    cnt = m.sum(1)
    prior = np.array([train.correct[train.mask[:, r], r].mean() if train.mask[:, r].any() else 0.0
                      for r in range(len(train.routes))])
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(cnt > 0, (c * m).sum(1) / np.maximum(cnt, 1), prior[None, :])
    return p


# ---------------------------------------------------------------- ModernBERT (routers 1, 2)

def _mb_net(base: str, n_routes: int):
    import torch
    from torch import nn
    from transformers import AutoModel

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = AutoModel.from_pretrained(base)
            self.head = nn.Linear(self.enc.config.hidden_size, n_routes)

        def forward(self, **batch):
            return self.head(self.enc(**batch).last_hidden_state[:, 0]).float()

    return Net()


def mb_scores(net, tok, texts: list[str], dev: str, max_len: int, bs: int = 64) -> np.ndarray:
    import torch
    net.eval()
    out = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev == "cuda"):
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], truncation=True, max_length=max_len, padding=True, return_tensors="pt").to(dev)
            out.append(net(**enc).float().cpu().numpy())
    net.train()
    return np.concatenate(out)


def train_modernbert(kind: str, train: Split, dev_sp: Split, a, log) -> tuple:
    """kind: label (masked softmax over routes, "none" items dropped) or success (masked per-route BCE).
    Keeps the epoch with the best dev score. Returns (net, tok, dev_scores, epoch log, timing)."""
    import torch
    from transformers import AutoTokenizer, get_linear_schedule_with_warmup
    set_seed(a.seed)
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    R = len(train.routes)
    lab = label_index(train.correct, train.mask, train.cost)
    idx = [i for i in range(len(train)) if kind == "success" or lab[i] >= 0]
    rng = random.Random(a.seed)
    if a.max_train and a.max_train < len(idx):
        idx = sorted(rng.sample(idx, a.max_train))
    tok = AutoTokenizer.from_pretrained(a.base)
    net = _mb_net(a.base, R).to(dev)
    steps_per_epoch = (len(idx) + a.bs - 1) // a.bs
    total = min(steps_per_epoch * a.epochs, a.max_steps or 10 ** 9)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * total), total)
    weight = None
    if kind == "label" and a.balanced:
        cnt = np.bincount(lab[idx], minlength=R).astype(float)
        weight = torch.tensor(np.where(cnt > 0, len(idx) / (R * np.maximum(cnt, 1)), 0.0), dtype=torch.float32, device=dev)
    mask_t = torch.tensor(train.mask, device=dev)
    corr_t = torch.tensor(train.correct, dtype=torch.float32, device=dev)
    lab_t = torch.tensor(lab, device=dev)
    best, epochs, step, t_train, t_eval = None, [], 0, 0.0, 0.0
    for ep in range(a.epochs):
        order = list(idx)
        rng.shuffle(order)
        t0 = time.time()
        for i in range(0, len(order), a.bs):
            if step >= total:
                break
            b = order[i:i + a.bs]
            enc = tok([train.texts[j] for j in b], truncation=True, max_length=a.max_len, padding=True, return_tensors="pt").to(dev)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev == "cuda"):
                z = net(**enc)
            m = mask_t[b]
            if kind == "label":
                loss = torch.nn.functional.cross_entropy(z.masked_fill(~m, -1e4), lab_t[b], weight=weight)
            else:
                l = torch.nn.functional.binary_cross_entropy_with_logits(z, corr_t[b], reduction="none")
                loss = (l * m).sum() / m.sum()
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            sched.step()
            step += 1
        if dev == "cuda":
            torch.cuda.synchronize()
        t_train += time.time() - t0
        t0 = time.time()
        z = mb_scores(net, tok, dev_sp.texts, dev, a.max_len)
        t_eval += time.time() - t0
        if kind == "label":
            r = evaluate(masked_argmax(z, dev_sp.mask, dev_sp.cost), dev_sp)
            score = (r["accuracy"], -r["gpu_seconds"])
            rec = {"epoch": ep + 1, "steps": step, "loss": round(float(loss), 4), "dev_accuracy": round(r["accuracy"], 4),
                   "dev_gpu_seconds": round(r["gpu_seconds"], 2)}
        else:
            p = 1 / (1 + np.exp(-z))
            bce = -(dev_sp.correct * np.log(np.clip(p, 1e-7, 1)) + (1 - dev_sp.correct) * np.log(np.clip(1 - p, 1e-7, 1)))
            dbce = float((bce * dev_sp.mask).sum() / dev_sp.mask.sum())
            score = (-dbce,)
            rec = {"epoch": ep + 1, "steps": step, "loss": round(float(loss), 4), "dev_bce": round(dbce, 4)}
        epochs.append(rec)
        log(f"[{kind}] {json.dumps(rec)}")
        if best is None or score > best[0]:
            best = (score, ep + 1, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}, z)
        if step >= total:
            break
    net.load_state_dict(best[2])
    timing = {"train_seconds": round(t_train, 1), "dev_eval_seconds": round(t_eval, 1), "steps": step,
              "seconds_per_step": round(t_train / max(step, 1), 3), "train_items": len(idx), "best_epoch": best[1],
              "device": dev}
    return net, tok, best[3], epochs, timing


# ---------------------------------------------------------------- train / evaluate / tables

def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def _env() -> dict:
    v = {"python": platform.python_version(), "numpy": np.__version__}
    for m in ("torch", "transformers", "sklearn"):
        try:
            v[m] = __import__(m).__version__
        except ImportError:
            pass
    return v


def train_routers(a, log=print) -> dict:
    """Fit on train, tune on dev; save each router under out/<router>/ with meta.json. Never loads held-out."""
    set_seed(a.seed)
    sp, info = load(a.labels, a.items, ["train", "dev"])
    train, dev_sp = sp["train"], sp["dev"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bf = best_fixed(train, info["summary_accuracy"], a.best_fixed)
    ref = evaluate(np.full(len(dev_sp), bf), dev_sp)
    log(f"routes (cheapest first): {info['routes']}  cost GPU-s/q: {info['cost_gpu_s']}")
    log(f"train {len(train)}  dev {len(dev_sp)}  best fixed route: {train.routes[bf]} (dev acc {ref['accuracy']:.4f}, "
        f"GPU-s {ref['gpu_seconds']:.2f})")
    common = {"seed": a.seed, "routes": info["routes"], "cost_gpu_s": info["cost_gpu_s"], "label_hashes": info["label_hashes"],
              "labels_dir": info["labels_dir"], "train_items": len(train), "dev_items": len(dev_sp), "tune": a.tune,
              "margin": a.margin, "best_fixed_route": train.routes[bf], "env": _env(), "dry_run": bool(a.dry_run),
              "args": {k: v for k, v in vars(a).items() if k != "func"}}
    done = {}
    x_tr = x_dev = None
    for name in a.routers:
        t0 = time.time()
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        meta = {**common, "router": name}
        if name in ("label", "success"):
            net, tok, z, epochs, timing = train_modernbert(name, train, dev_sp, a, log)
            meta.update({"base": a.base, "epochs": a.epochs, "lr": a.lr, "bs": a.bs, "max_len": a.max_len,
                         "max_train": a.max_train, "max_steps": a.max_steps, "balanced": a.balanced,
                         "epoch_log": epochs, "timing": timing})
            if name == "label":
                picks = masked_argmax(z, dev_sp.mask, dev_sp.cost)
                meta["params"] = {}
            else:
                p = 1 / (1 + np.exp(-z))
                pick, cands = tune_tau(p, dev_sp, ref, a.tune, a.margin)
                meta.update({"params": pick["params"], "tuning": cands})
                picks = cheapest_above(p, dev_sp.mask, pick["params"]["tau"], dev_sp.cost)
            import torch
            torch.save(net.state_dict(), d / "model.pt")
            tok.save_pretrained(d)
            del net
        else:
            if x_tr is None:
                x_tr, x_dev = cached_embed(out, train, a.device), cached_embed(out, dev_sp, a.device)
            if name == "bge_lr":
                cands, models = [], {}
                for C in CS:
                    models[C] = LRRouter(C, a.seed).fit(x_tr, train)
                    _, cs = tune_tau(models[C].proba(x_dev, len(train.routes)), dev_sp, ref, a.tune, a.margin, {"C": C})
                    cands += cs
                pick = choose(cands, ref, a.tune, a.margin)
                C, tau = pick["params"]["C"], pick["params"]["tau"]
                with open(d / "model.pkl", "wb") as f:
                    pickle.dump(models[C], f)
                picks = cheapest_above(models[C].proba(x_dev, len(train.routes)), dev_sp.mask, tau, dev_sp.cost)
                meta.update({"embedder": EMBEDDER, "params": pick["params"], "tuning": cands})
            else:
                cands = []
                for k in KS:
                    if k > len(train):
                        continue
                    _, cs = tune_tau(knn_proba(x_dev, x_tr, train, k), dev_sp, ref, a.tune, a.margin, {"k": k})
                    cands += cs
                pick = choose(cands, ref, a.tune, a.margin)
                k, tau = pick["params"]["k"], pick["params"]["tau"]
                np.savez(d / "knn.npz", x=x_tr, correct=train.correct, mask=train.mask, routes=np.array(train.routes),
                         ids=np.array(train.ids))
                picks = cheapest_above(knn_proba(x_dev, x_tr, train, k), dev_sp.mask, tau, dev_sp.cost)
                meta.update({"embedder": EMBEDDER, "params": pick["params"], "tuning": cands})
        res = evaluate(picks, dev_sp)
        meta.update({"dev": res, "seconds": round(time.time() - t0, 1)})
        (d / "meta.json").write_text(json.dumps(_jsonable(meta), indent=1))
        log(f"[{name}] params {meta['params']}  dev acc {res['accuracy']:.4f}  GPU-s {res['gpu_seconds']:.2f}  "
            f"picked {res['picked']}  ({meta['seconds']} s)")
        done[name] = meta
    return done


def predict(name: str, d: Path, sp: Split, train: Split, out: Path, device: str | None) -> np.ndarray:
    meta = json.loads((d / "meta.json").read_text())
    if meta["routes"] != sp.routes:
        raise SystemExit(f"{name}: trained on routes {meta['routes']}, labels now have {sp.routes}")
    if name in ("label", "success"):
        import torch
        from transformers import AutoTokenizer
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        net = _mb_net(meta["base"], len(sp.routes)).to(dev)
        net.load_state_dict(torch.load(d / "model.pt", map_location=dev))
        z = mb_scores(net, AutoTokenizer.from_pretrained(d), sp.texts, dev, meta["max_len"])
        if name == "label":
            return masked_argmax(z, sp.mask, sp.cost)
        return cheapest_above(1 / (1 + np.exp(-z)), sp.mask, meta["params"]["tau"], sp.cost)
    x = cached_embed(out, sp, device)
    if name == "bge_lr":
        with open(d / "model.pkl", "rb") as f:
            m = pickle.load(f)
        return cheapest_above(m.proba(x, len(sp.routes)), sp.mask, meta["params"]["tau"], sp.cost)
    z = np.load(d / "knn.npz")
    if list(z["ids"]) != train.ids:
        raise SystemExit("knn: saved training questions differ from the current train split")
    return cheapest_above(knn_proba(x, z["x"], train, meta["params"]["k"]), sp.mask, meta["params"]["tau"], sp.cost)


def _fmt(v):
    if v is None or v == "":
        return ""
    if isinstance(v, float):
        return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else f"{v:.0f}"
    return str(v)


def write_table(out: Path, stem: str, rows: list[dict], note: str) -> None:
    cols = list(rows[0])
    with open(out / f"{stem}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + \
         ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for r in rows]
    (out / f"{stem}.md").write_text(note + "\n\n" + "\n".join(md) + "\n")


def evaluate_routers(a, log=print) -> list[dict]:
    split = "held_out" if a.held_out else "dev"
    sp, info = load(a.labels, a.items, ["train", split], held_out_ok=a.held_out)
    train, ev = sp["train"], sp[split]
    out = Path(a.out)
    bf = best_fixed(train, info["summary_accuracy"], a.best_fixed)
    ref = evaluate(np.full(len(ev), bf), ev)
    results, rows = {}, []
    names = [n for n in a.routers if (out / n / "meta.json").exists()]
    if not names:
        raise SystemExit(f"no trained routers under {out}")
    dry = any(json.loads((out / n / "meta.json").read_text()).get("dry_run") for n in names)

    def row(name, kind, res, params=""):
        return {"row": name, "kind": kind, "split": split, "questions": res["questions"], "accuracy": round(res["accuracy"], 4),
                "gpu_seconds_per_question": round(res["gpu_seconds"], 2), "output_tokens_per_question": round(res["output_tokens"]),
                "points_vs_best_fixed": round(100 * (res["accuracy"] - ref["accuracy"]), 1),
                "gpu_vs_best_fixed": round(res["gpu_seconds"] / ref["gpu_seconds"], 3) if ref["gpu_seconds"] else None,
                "picked": " ".join(f"{k}:{v}" for k, v in res["picked"].items()), "params": params,
                "keep_rule": keep_rule(res, ref) if kind == "router" else ""}

    for n in names:
        meta = json.loads((out / n / "meta.json").read_text())
        res = evaluate(predict(n, out / n, ev, train, out, a.device), ev)
        results[n] = res
        rows.append(row(n, "router", res, " ".join(f"{k}={v}" for k, v in meta["params"].items())))
    for r, route in enumerate(ev.routes):
        if ev.mask[:, r].all():
            res = evaluate(np.full(len(ev), r), ev)
            results[f"fixed:{route}"] = res
            rows.append(row(route + (" (best fixed)" if r == bf else ""), "fixed route", res))
    res = evaluate(oracle_picks(ev), ev)
    results["oracle"] = res
    rows.append(row("oracle", "cheapest correct route, known only after trying all", res))
    head = ("DRY RUN, NOT A RESULT: ModernBERT trained a few steps on a few dozen questions; only shows the code path. "
            if dry else "")
    note = (f"{head}test-04 supervised routers on {split} ({len(ev)} questions), trained on train ({len(train)}), tuned on dev "
            f"(flotilla/strategy_router.py, seed {a.seed}). Best fixed route (keep-rule reference): {train.routes[bf]}. "
            f"GPU-seconds per question from the labels (route job GPU-s spread by wall time). Keep rule: within 1 point of "
            f"the best fixed route at lower compute, or more than 1 point better. Labels {info['labels_dir']} "
            f"({info['label_hashes']['per_question.jsonl']}).")
    stem = f"table_{split}" + ("_dryrun" if dry else "")
    write_table(out, stem, rows, note)
    src_rows = []
    for n, res in results.items():
        for s, v in res["by_source"].items():
            src_rows.append({"row": n, "source": s, "questions": v["questions"], "accuracy": round(v["accuracy"], 4),
                             "picked": " ".join(f"{k}:{c}" for k, c in v["picked"].items())})
    write_table(out, stem + "_by_source", src_rows, head + f"Picks and accuracy per benchmark source ({split}).")
    (out / f"{stem}.json").write_text(json.dumps(_jsonable({"split": split, "seed": a.seed, "dry_run": dry, "routes": ev.routes,
                                                            "best_fixed": train.routes[bf], "results": results}), indent=1))
    log((out / f"{stem}.md").read_text())
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("train", "evaluate", "dry-run"):
        p = sub.add_parser(c)
        p.add_argument("--labels", required=True, help="graded folder: per_question.jsonl, split.json, summary.json")
        p.add_argument("--items", nargs="+", required=True, help="question files/globs (id or item_id, task)")
        p.add_argument("--out", required=True)
        p.add_argument("--routers", nargs="+", default=ROUTERS, choices=ROUTERS)
        p.add_argument("--seed", type=int, default=SEED)
        p.add_argument("--device", default=None)
        p.add_argument("--best-fixed", default=None, help="keep-rule reference route (default: best in summary.json)")
        if c == "evaluate":
            p.add_argument("--held-out", action="store_true", help="evaluate on held-out (once, at the end); dev otherwise")
            continue
        p.add_argument("--tune", choices=["rule", "accuracy"], default="rule")
        p.add_argument("--margin", type=float, default=0.005, help="safety margin in accuracy for --tune rule")
        p.add_argument("--base", default=MODERNBERT)
        p.add_argument("--epochs", type=int, default=3 if c == "train" else 2)
        p.add_argument("--lr", type=float, default=3e-5)
        p.add_argument("--bs", type=int, default=16)
        p.add_argument("--max-len", type=int, default=1024)
        p.add_argument("--max-train", type=int, default=0 if c == "train" else 48, help="ModernBERT: cap training questions (0 = all)")
        p.add_argument("--max-steps", type=int, default=0 if c == "train" else 6, help="ModernBERT: cap optimiser steps (0 = none)")
        p.add_argument("--balanced", action="store_true", help="label router: class-balanced cross-entropy")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.cmd in ("train", "dry-run"):
        a.dry_run = a.cmd == "dry-run"
        train_routers(a)
        a.held_out = False
        evaluate_routers(a)
    else:
        evaluate_routers(a)
    print(f"[strategy_router] {a.cmd} done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
