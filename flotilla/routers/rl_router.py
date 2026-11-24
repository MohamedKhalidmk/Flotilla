"""test-04 router 5: live RL over route steps. Per question it runs route steps in any order, sees the verifier's verdict
and the GPU-seconds so far after each step, and stops when it judges the answer good enough.

    python -m flotilla.routers.rl_router train     --labels DIR --items GLOB [GLOB ...] --out DIR --prior SPEC (--serve configs/servers.json | --server-url URL) --pool POOL.jsonl
    python -m flotilla.routers.rl_router evaluate  --labels DIR --items GLOB [GLOB ...] --out DIR (--serve ... | --server-url ...) --pool POOL.jsonl [--held-out]
    python -m flotilla.routers.rl_router dry-run   --labels DIR --items GLOB [GLOB ...] --out DIR      # fake Qwen, 20 train questions
    python -m flotilla.routers.rl_router priors    --labels DIR --items GLOB [GLOB ...] --router-dir DIR --out FILE [--held-out]
    python -m flotilla.routers.rl_router estimate  --labels DIR --items GLOB [GLOB ...] --out DIR      # GPU-hours from the labels
    python -m flotilla.routers.rl_router exclusions --audit DIR --out FILE                             # wrong-gold id list

Design (test-04 README, Setup > Routers item 5). Actions: the ten routes (flotilla/strategy_labels.ORDER) plus stop.
Each route step is one full run of that route through the normal Flotilla loop (flotilla/core/system.answer: solver, vote,
verifier, one retry; Memory routes through flotilla/memory/memory_route.run_memory_route with the item's GRAFT memory). After a
step the router sees the step's verifier verdict, its answer (agreement with earlier answers) and the GPU-seconds so far.

Masks (per item, per step):
  - a route is offered only if it is in the run (--routes) and available on the item: Memory routes only on items with
    a history (memory_route.route_available); routes the labels never ran are off;
  - a route already run on the item is offered again only if it samples (n_samples > 1 in its config: Vote, Vote+Tools,
    Vote+Memory), at most --max-repeats runs in all; Fast/Tools/Deep/Deep+Tools are greedy (temperature 0), a repeat
    would give the same answer;
  - stop is not offered before the first step (no answer yet); after --max-steps steps, or once the chain has used
    --max-gpu-s GPU-seconds, only stop is left (a forced stop, not a decision); a route whose mean cost (labels) would
    take the chain over --max-gpu-s is masked (at step 0 the cheapest available route stays, so there is always a move).
Final answer (--final-rule): last_accept (default) = the answer of the last step the verifier accepted, else the last
step's answer; last = the last step's answer; vote = system.vote over every step's answer.
Reward: +1 if the final answer is correct, minus --alpha x GPU-seconds of the whole chain (alpha logged everywhere).

Method: a contextual bandit at every decision, with Monte-Carlo targets. Q(s, a) = w_a . psi(s) is linear in frozen state
features psi (the supervised router's per-route success estimates for the question, its pick (first step only), the
task type, routes run so far, the last verdict, answer agreement, steps and GPU-seconds used). Each action's weights
are a Bayesian ridge regression of the reward-to-go (1[final correct] - alpha x GPU-s of this step and later ones; stop:
1[final correct]) on psi, with a Gaussian prior centred on w0: route a's Q starts at p_a(x) - alpha x mean cost(a)
+ bonus x 1[a = supervised pick] at step 0, so the untrained greedy policy is exactly the supervised router's pick;
after an accepted step stop is preferred, after a rejection the route with the best estimate is. Exploration is
Thompson sampling from the posterior (--explore scales it; evaluation is greedy at the posterior mean).
Why: episodes cost real GPU minutes (2.6 to 20 GPU-s per step), horizons are 1-3 steps and the action set has 11
entries; a ridge posterior per action learns from a few hundred chains, reuses every logged decision, starts from the
supervised router with a prior whose strength is one number (--prior-strength), is exact to rebuild from the chain log
(resume = replay the log), and needs no GPU of its own. REINFORCE on a policy head would need far more episodes for the
same variance; full Q-learning gains little over Monte-Carlo targets at horizon 3.

Prior (--prior): file:PRIORS.jsonl (written by `priors` from the best supervised router on dev, or --router NAME),
or route-accuracy (each route's training accuracy on the question's task type; cheapest route with p >= --prior-tau;
no model, used by the dry run and when no router is trained). Routes the prior lacks fall back to route-accuracy.

Costs. A step's GPU-seconds are measured live: every GPU's time is shared equally between the steps in flight
(GpuClock), so the chains' GPU-seconds add up to the job's busy GPU time; the labels' route GPU-seconds were measured
the same way at the job level. In fake mode a step costs its label GPU-seconds (strategy_router's per-question rule).
The GRAFT build of an item's history is charged once, to its first Memory step: build wall seconds x --graft-build-share.

Splits. train uses train questions only; evaluate uses dev, or held-out only with --held-out (held-out label rows
are never parsed otherwise: strategy_router.read_rows). Every chain is logged (chains_<mode>.jsonl: steps, verdicts,
answers, GPU-seconds, tokens, decisions with their features and targets; traces_<mode>.jsonl: the full traces).

Budget and resume: --max-steps, --max-gpu-s (per question), --max-questions (per epoch), --epochs, --stop-after
(seconds; no new chain starts after it). The chain log is the checkpoint: a rerun of the same command replays it,
rebuilds the policy exactly and skips finished (epoch, question) pairs; policy.npz is rewritten after every chain and
policy_epochK.npz after each epoch.

Extra number (user, 2026-11-21): beyond_oracle = questions the RL router answers correctly that every fixed route got
wrong in the labels, not counting questions whose gold answer is wrong (`exclusions` builds the id list from the
always-wrong audit: diagnosis.json, checked against always_wrong.md). Above zero beats the per-question oracle of fixed
routes. In the evaluation table and in beyond_oracle_<split>.md with the chains that solved them.
"""
import argparse
import asyncio
import contextlib
import contextvars
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from flotilla.routers import strategy_router as sr
from flotilla.routers.strategy_labels import ORDER as ROUTES

SEED = 20261121
STOP = "stop"
ACTIONS = list(ROUTES) + [STOP]
NA = len(ACTIONS)
R = len(ROUTES)
TASK_TYPES = ["math", "science_mc", "instruction", "code", "memory", "other"]
MEMORY_ROUTES = ("memory", "memory_deep", "deep_tools_memory", "vote_memory")
# psi layout
F_BIAS, F_P, F_PICK, F_RUNS = 0, 1, 1 + R, 1 + 2 * R
F_STEP, F_ACC, F_REJ, F_AGREE, F_NACC, F_COST, F_MEM, F_TT = (1 + 3 * R + i for i in range(8))
D = F_TT + len(TASK_TYPES)
SIGMA = 0.5                      # reward noise scale of the posterior (rewards are in [-1, 1])
STOP_PRIOR_ACCEPT, STOP_PRIOR_REJECT = 0.95, 0.30   # prior Q(stop) after an accepted / rejected step
CONTINUE_AFTER_ACCEPT, REPEAT_PRIOR = -0.20, -0.30   # prior: continuing after an accept, and each earlier run of a route
STEP = contextvars.ContextVar("rl_step", default=None)   # (item_id, route, repeat) of the step in flight (fake models read it)
_ID = re.compile(r'^\{"(?:id|item_id)":\s*"((?:[^"\\]|\\.)*)"')


# ---------------------------------------------------------------- config

@dataclass
class RLConfig:
    alpha: float = 0.001          # reward penalty per GPU-second
    max_steps: int = 3
    max_gpu_s: float = 60.0
    max_repeats: int = 2          # total runs of one sampled route on one item
    final_rule: str = "last_accept"
    prior_strength: float = 5.0
    sup_bonus: float = 1.0
    explore: float = 0.5
    routes: list = field(default_factory=lambda: list(ROUTES))

    @classmethod
    def from_args(cls, a) -> "RLConfig":
        return cls(**{k: getattr(a, k) for k in cls.__dataclass_fields__ if getattr(a, k, None) is not None})


KEY_FIELDS = ("alpha", "max_steps", "max_gpu_s", "max_repeats", "final_rule", "prior_strength", "sup_bonus", "routes")


# ---------------------------------------------------------------- data

@dataclass
class Data:
    rows: dict        # id -> label row
    ids: dict         # split name -> ids
    items: dict       # id -> run item
    cost: dict        # route -> mean GPU-s per question (summary.json; default for routes it lacks)
    rate: dict        # route -> GPU-s per wall-second (or None)
    held_out: set     # held-out ids (ids only, from split.json)
    labels_dir: str = ""
    hashes: dict = field(default_factory=dict)
    summary_acc: dict = field(default_factory=dict)

    def gpu(self, i: str, r: str) -> float:
        """Label GPU-seconds of route r on item i (strategy_router's rule)."""
        v = self.rows[i].get(r) or {}
        if v.get("gpu_seconds") is not None:
            return float(v["gpu_seconds"])
        if self.rate.get(r) is not None and v.get("wall_seconds") is not None:
            return self.rate[r] * float(v["wall_seconds"])
        return float(self.cost.get(r, 0.0))


def read_items(globs: list[str], wanted: set) -> dict[str, dict]:
    """Run items (item_id or id, task, task_type, ...) for wanted ids only; other lines are not parsed when their id
    comes first (held-out)."""
    out = {}
    files = sorted({p for g in globs for p in __import__("glob").glob(g)})
    if not files:
        raise SystemExit(f"no item files match {globs}")
    for p in files:
        with open(p) as f:
            for line in f:
                m = _ID.match(line)
                if m is not None and json.loads(f'"{m.group(1)}"') not in wanted:
                    continue
                if not line.strip():
                    continue
                r = json.loads(line)
                i = r.get("item_id", r.get("id"))
                if i in wanted and i not in out:
                    out[i] = {**r, "item_id": i}
    return out


def load_data(labels: str, items: list[str], names: list[str], held_out_ok: bool = False,
              default_cost: float = 20.0) -> Data:
    lab = Path(labels)
    ids = sr.read_split_ids(lab, names, held_out_ok)       # refuses held_out without the flag
    wanted = {i for v in ids.values() for i in v}
    rows = sr.read_rows(lab, wanted)
    its = read_items(items, wanted)
    lost = sorted(i for i in wanted if i not in rows or i not in its)
    if lost:
        raise SystemExit(f"{len(lost)} split ids lack a label row or an item, e.g. {lost[:5]}")
    summary = json.loads((lab / "summary.json").read_text())
    seen = {r for i in wanted for r in sr.row_routes(rows[i])}
    _, cost, rate = sr.route_costs(summary, seen)
    cost = {r: float(cost.get(r, default_cost)) for r in ROUTES}
    held = set(json.loads((lab / "split.json").read_text()).get("held_out", []))
    hashes = {f: hashlib.sha256((lab / f).read_bytes()).hexdigest()[:16] for f in ("per_question.jsonl", "split.json", "summary.json")}
    acc = {r: v["accuracy"] for r, v in summary["per_strategy"].items() if "accuracy" in v}
    return Data(rows, ids, its, cost, rate, held, str(lab), hashes, acc)


def route_on(row: dict, r: str) -> bool:
    v = row.get(r)
    return isinstance(v, dict) and "correct" in v


def task_type(item: dict) -> str:
    t = item.get("task_type", "other")
    return t if t in TASK_TYPES else "other"


# ---------------------------------------------------------------- exclusions (wrong gold)

def build_exclusions(audit: str | Path, diagnoses=("wrong gold",)) -> list[tuple[str, str]]:
    """(id, diagnosis) for every always-wrong question whose diagnosis is in `diagnoses`, from diagnosis.json; checked
    against the sections of always_wrong.md when it is there."""
    audit = Path(audit)
    diag = json.loads((audit / "diagnosis.json").read_text())
    out = sorted((i, v[0]) for i, v in diag.items() if v[0] in diagnoses)
    md = audit / "always_wrong.md"
    if md.exists():
        sec, by_md = None, {}
        for line in md.read_text().splitlines():
            m = re.match(r"^## (.+?) \(\d+\)\s*$", line)
            if m:
                sec = m.group(1).strip().lower()
            m = re.match(r"^### (\S+) · ", line)
            if m and sec:
                by_md[m.group(1)] = sec
        diff = sorted(i for i in set(by_md) | set(diag) if by_md.get(i) != diag.get(i, [None])[0])
        if diff:
            raise SystemExit(f"diagnosis.json and always_wrong.md disagree on {diff}")
    return out


def write_exclusions(path: str | Path, rows: list[tuple[str, str]], source: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(f"# ids excluded from the beyond-oracle count (from {source})\n"
                          + "".join(f"{i}\t{d}\n" for i, d in rows))


def read_exclusions(path: str | Path | None) -> set:
    if not path:
        return set()
    return {l.split("\t")[0].strip() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")}


def audit_golds(audit: str | Path) -> dict[str, str]:
    """Gold answers of the always-wrong questions, from the headings of always_wrong.md (dry runs only)."""
    md = Path(audit) / "always_wrong.md"
    if not md.exists():
        return {}
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^### (\S+) · \S+ · gold: (.*)$", md.read_text(), re.M)}


# ---------------------------------------------------------------- priors (the supervised router)

class Prior:
    """p[route] (chance the route is right on the question) and the supervised pick, per item id."""

    def __init__(self, name: str, table: dict, fallback: "Prior | None" = None):
        self.name, self.table, self.fallback = name, table, fallback

    def get(self, i: str, item: dict) -> tuple[np.ndarray, str | None]:
        p = np.zeros(R)
        rec = self.table.get(i)
        fb = self.fallback.get(i, item) if self.fallback else (np.zeros(R), None)
        for k, r in enumerate(ROUTES):
            if rec is not None and r in rec["p"]:
                p[k] = float(rec["p"][r])
            else:
                p[k] = fb[0][k]
        return p, (rec["pick"] if rec is not None else fb[1])


def route_accuracy_prior(data: Data, train_ids: list[str], tau: float = 0.95) -> Prior:
    """Each route's training accuracy on the item's task type (Laplace), pick = cheapest route with p >= tau, else the
    most likely. Uses training rows only."""
    cnt = defaultdict(lambda: [0, 0])
    for i in train_ids:
        row, tt = data.rows[i], task_type(data.items[i])
        for r in ROUTES:
            if route_on(row, r):
                for key in (tt, "*"):
                    cnt[(key, r)][0] += bool(row[r]["correct"])
                    cnt[(key, r)][1] += 1
    order = sorted(ROUTES, key=lambda r: (data.cost[r], ROUTES.index(r)))

    class _P(Prior):
        def get(self, i, item):
            tt = task_type(item)
            p = np.zeros(R)
            for k, r in enumerate(ROUTES):
                c, n = cnt[(tt, r)] if cnt[(tt, r)][1] else cnt[("*", r)]
                p[k] = (c + 1) / (n + 2) if n else 0.5
            avail = [r for r in order if (i not in data.rows or route_on(data.rows[i], r)) and
                     (r not in MEMORY_ROUTES or bool(item.get("sessions")))]
            pick = next((r for r in avail if p[ROUTES.index(r)] >= tau), None)
            if pick is None and avail:
                pick = max(avail, key=lambda r: (p[ROUTES.index(r)], -order.index(r)))
            return p, pick
    return _P("route-accuracy", {})


def read_prior_file(path: str) -> dict:
    out = {}
    for line in open(path):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def make_prior(spec: str, data: Data, train_ids: list[str], tau: float) -> Prior:
    fb = route_accuracy_prior(data, train_ids, tau)
    if spec == "route-accuracy":
        return fb
    if spec.startswith("file:"):
        t = read_prior_file(spec[5:])
        return Prior(f"file:{Path(spec[5:]).name}:{next(iter(t.values()))['router'] if t else '?'}", t, fb)
    raise SystemExit(f"--prior {spec}: use file:PRIORS.jsonl or route-accuracy")


def best_supervised(router_dir: Path, ref: dict) -> str:
    """The best supervised router on dev (meta.json 'dev'): keep-rule passes first ('more than 1 point better' before
    'within 1 point, less compute'), then accuracy, then lower GPU-seconds."""
    cands = []
    for n in sr.ROUTERS:
        p = router_dir / n / "meta.json"
        if p.exists():
            d = json.loads(p.read_text())["dev"]
            rule = sr.keep_rule(d, ref)
            cands.append(((rule.startswith("keep (more"), rule.startswith("keep"), d["accuracy"], -d["gpu_seconds"]), n))
    if not cands:
        raise SystemExit(f"no trained router under {router_dir}")
    return max(cands)[1]


def router_probs(name: str, d: Path, sp, train, out: Path, device: str | None) -> tuple[np.ndarray, np.ndarray]:
    """Per-route probabilities and picks of a trained supervised router (strategy_router's own models and rules).
    label router: its softmax over routes (a class probability, a weaker prior than the success estimates)."""
    meta = json.loads((d / "meta.json").read_text())
    if meta["routes"] != sp.routes:
        raise SystemExit(f"{name}: trained on routes {meta['routes']}, labels now have {sp.routes}")
    if name in ("label", "success"):
        import torch
        from transformers import AutoTokenizer
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        net = sr._mb_net(meta["base"], len(sp.routes)).to(dev)
        net.load_state_dict(torch.load(d / "model.pt", map_location=dev))
        z = sr.mb_scores(net, AutoTokenizer.from_pretrained(d), sp.texts, dev, meta["max_len"])
        if name == "label":
            zm = np.where(sp.mask, z, -np.inf)
            e = np.exp(zm - zm.max(1, keepdims=True))
            return e / e.sum(1, keepdims=True), sr.masked_argmax(z, sp.mask, sp.cost)
        p = 1 / (1 + np.exp(-z))
        return p, sr.cheapest_above(p, sp.mask, meta["params"]["tau"], sp.cost)
    x = sr.cached_embed(out, sp, device)
    if name == "bge_lr":
        import pickle

        class _U(pickle.Unpickler):  # strategy_router pickles LRRouter as __main__.LRRouter (it runs with -m)
            def find_class(self, module, name):
                return sr.LRRouter if name == "LRRouter" else super().find_class(module, name)
        with open(d / "model.pkl", "rb") as f:
            m = _U(f).load()
        p = m.proba(x, len(sp.routes))
    else:
        z = np.load(d / "knn.npz")
        if list(z["ids"]) != train.ids:
            raise SystemExit("knn: saved training questions differ from the current train split")
        p = sr.knn_proba(x, z["x"], train, meta["params"]["k"])
    return p, sr.cheapest_above(p, sp.mask, meta["params"]["tau"], sp.cost)


def cmd_priors(a) -> None:
    names = ["train", "dev"] + (["held_out"] if a.held_out else [])
    sp, info = sr.load(a.labels, a.items, names, held_out_ok=a.held_out)
    rd = Path(a.router_dir)
    bf = sr.best_fixed(sp["train"], info["summary_accuracy"])
    ref = sr.evaluate(np.full(len(sp["dev"]), bf), sp["dev"])
    name = a.router or best_supervised(rd, ref)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w") as f:
        for n in names:
            p, pick = router_probs(name, rd / name, sp[n], sp["train"], rd, a.device)
            for k, i in enumerate(sp[n].ids):
                f.write(json.dumps({"id": i, "split": n, "router": name, "pick": sp[n].routes[int(pick[k])],
                                    "p": {r: round(float(p[k, j]), 5) for j, r in enumerate(sp[n].routes) if sp[n].mask[k, j]}}) + "\n")
    print(f"[rl_router] priors from router {name} ({rd}) for {names} -> {a.out}", flush=True)


# ---------------------------------------------------------------- state, masks, policy

@dataclass
class State:
    item: dict
    p: np.ndarray
    pick: str | None
    offered: set                  # routes in the run and available on the item
    steps: list = field(default_factory=list)
    runs: Counter = field(default_factory=Counter)
    cost: float = 0.0

    @property
    def t(self) -> int:
        return len(self.steps)


def sampled_routes() -> set:
    """Routes whose config samples (n_samples > 1): the only ones a chain may run again."""
    from flotilla.memory.memory_route import ROUTE_CONFIG
    out = set()
    for r in ROUTES:
        p = ROUTE_CONFIG.get(r)
        if p is not None and p.exists() and json.loads(p.read_text()).get("n_samples", 1) > 1:
            out.add(r)
    return out


def offered_routes(item: dict, row: dict | None, cfg: RLConfig) -> set:
    from flotilla.memory.memory_route import route_available
    return {r for r in cfg.routes if route_available(item, r) and (row is None or route_on(row, r) or r in MEMORY_ROUTES
                                                                     and bool(item.get("sessions")))}


def _norm(a: str | None) -> str | None:
    return None if a is None else re.sub(r"\s+", " ", a.strip().strip(".").lower())


class Policy:
    def __init__(self, cfg: RLConfig, cost: dict, sampled: set):
        self.cfg, self.cost, self.sampled = cfg, cost, sampled
        self.scale = max(cost[r] for r in ROUTES) or 1.0
        self.w0 = np.zeros((NA, D))
        for k, r in enumerate(ROUTES):
            self.w0[k, F_BIAS] = -cfg.alpha * cost[r]
            self.w0[k, F_P + k] = 1.0
            self.w0[k, F_PICK + k] = cfg.sup_bonus
            self.w0[k, F_RUNS + k] = REPEAT_PRIOR
            self.w0[k, F_ACC] = CONTINUE_AFTER_ACCEPT
        self.w0[NA - 1, F_ACC], self.w0[NA - 1, F_REJ] = STOP_PRIOR_ACCEPT, STOP_PRIOR_REJECT
        lam = cfg.prior_strength
        self.A = np.stack([lam * np.eye(D) for _ in range(NA)])
        self.b = lam * self.w0.copy()
        self.updates = 0
        self._w = None

    # -- masks
    def mask(self, st: State) -> tuple[np.ndarray, str | None]:
        """Allowed actions and, when only stop is left, why (a forced stop is not a decision)."""
        c = self.cfg
        m = np.zeros(NA, bool)
        if st.t >= c.max_steps:
            m[-1] = True
            return m, "max_steps"
        if st.t > 0 and st.cost >= c.max_gpu_s:
            m[-1] = True
            return m, "max_gpu_s"
        cand = [r for r in ROUTES if r in st.offered and
                (st.runs[r] == 0 or (r in self.sampled and st.runs[r] < c.max_repeats))]
        fits = [r for r in cand if st.cost + self.cost[r] <= c.max_gpu_s]
        if st.t == 0 and not fits and cand:
            fits = [min(cand, key=lambda r: self.cost[r])]
        for r in fits:
            m[ROUTES.index(r)] = True
        if st.t > 0:
            m[-1] = True
        if m[:-1].any():
            return m, None
        return m, ("no_route" if st.t > 0 else "no_route_available")

    # -- features
    def features(self, st: State) -> np.ndarray:
        psi = np.zeros(D)
        psi[F_BIAS] = 1.0
        for k, r in enumerate(ROUTES):
            if r in st.offered:
                psi[F_P + k] = st.p[k]
            psi[F_RUNS + k] = st.runs[r]
        if st.t == 0 and st.pick in ROUTES and st.pick in st.offered:
            psi[F_PICK + ROUTES.index(st.pick)] = 1.0
        psi[F_STEP] = st.t / max(self.cfg.max_steps, 1)
        if st.steps:
            v = st.steps[-1]["verdict"]
            psi[F_ACC] = float(v == "accept")
            psi[F_REJ] = float(v in ("reject", "error"))
            last = _norm(st.steps[-1]["answer"])
            psi[F_AGREE] = float(last is not None and any(_norm(s["answer"]) == last for s in st.steps[:-1]))
            psi[F_NACC] = sum(s["verdict"] == "accept" for s in st.steps) / st.t
        psi[F_COST] = st.cost / self.scale
        psi[F_MEM] = float(bool(st.item.get("sessions")))
        psi[F_TT + TASK_TYPES.index(task_type(st.item))] = 1.0
        return psi

    # -- values
    def weights(self) -> np.ndarray:
        if self._w is None:
            self._w = np.stack([np.linalg.solve(self.A[a], self.b[a]) for a in range(NA)])
        return self._w

    def q(self, psi: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
        w = self.weights()
        if rng is None or self.cfg.explore <= 0:
            return w @ psi
        out = np.empty(NA)
        for a in range(NA):  # Thompson: w_a ~ N(mean, (explore * SIGMA)^2 A_a^-1)
            cov = np.linalg.inv(self.A[a])
            L = np.linalg.cholesky((cov + cov.T) / 2)
            out[a] = (w[a] + self.cfg.explore * SIGMA * L @ rng.standard_normal(D)) @ psi
        return out

    def act(self, psi: np.ndarray, allowed: np.ndarray, rng=None) -> tuple[int, np.ndarray]:
        q = self.q(psi, rng)
        qm = np.where(allowed, q, -np.inf)
        return int(qm.argmax()), q          # argmax takes the first max: routes cheapest-order, stop last

    def update(self, psi, a: int, target: float) -> None:
        psi = np.asarray(psi, float)
        self.A[a] += np.outer(psi, psi)
        self.b[a] += target * psi
        self.updates += 1
        self._w = None

    def save(self, path: Path, extra: dict | None = None) -> None:
        tmp = path.with_name(path.name + ".tmp.npz")
        np.savez(tmp, A=self.A, b=self.b, w0=self.w0, updates=self.updates,
                 meta=json.dumps({"cfg": self.cfg.__dict__, "cost": self.cost, "sampled": sorted(self.sampled),
                                  "actions": ACTIONS, "D": D, **(extra or {})}))
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path) -> "Policy":
        z = np.load(path)
        meta = json.loads(str(z["meta"]))
        if meta["actions"] != ACTIONS or meta["D"] != D:
            raise SystemExit(f"{path}: saved with another action set or feature layout")
        p = cls(RLConfig(**meta["cfg"]), meta["cost"], set(meta["sampled"]))
        p.A, p.b, p.w0, p.updates = z["A"], z["b"], z["w0"], int(z["updates"])
        return p


# ---------------------------------------------------------------- GPU clock

class GpuClock:
    """Shares the serving GPUs' time equally between the steps in flight: a step's GPU-seconds = integral of
    gpus / (steps in flight) over its life. Idle time (no step in flight) is counted apart."""

    def __init__(self, gpus: float = 1.0):
        self.gpus, self.active, self.t, self.idle = gpus, {}, time.monotonic(), 0.0

    def _tick(self):
        now = time.monotonic()
        dt, self.t = now - self.t, now
        if self.active:
            share = dt * self.gpus / len(self.active)
            for k in self.active:
                self.active[k] += share
        else:
            self.idle += dt * self.gpus

    def start(self, key) -> None:
        self._tick()
        self.active[key] = 0.0

    def stop(self, key) -> float:
        self._tick()
        return self.active.pop(key)


# ---------------------------------------------------------------- runners: one route step on one item

def route_config(route: str, servers: dict | None):
    """SystemConfig of a route; servers (name -> {url, model}) replace only url/model, keeping the route's own server
    fields (request: enable_thinking, native_tools). memory_route.load_config(route, servers) would replace the whole
    server entry and drop the route's request fields."""
    from flotilla.memory.memory_route import ROUTE_CONFIG
    from flotilla.core.system import SystemConfig
    conf = json.loads(ROUTE_CONFIG[route].read_text())
    if servers:
        conf["servers"] = {n: {**s, **{k: v for k, v in servers.get(n, next(iter(servers.values()))).items()
                                       if k in ("url", "model")}} for n, s in conf["servers"].items()}
    return SystemConfig(**{k: v for k, v in conf.items() if k not in ("name", "notes")})


class LoopRunner:
    """Runs a route step through the Flotilla loop (system.answer / memory_route.run_memory_route). replicas: one
    servers map per vLLM replica; each step goes to the replica with the fewest steps in flight."""

    def __init__(self, replicas: list[dict] | None = None, memory: dict | None = None, clock: GpuClock | None = None,
                 cost_override=None, run_id: str = "rl", split: str = "train", graft_build_share: float = 1 / 16,
                 tokens_override=None):
        self.replicas = replicas or [None]
        self.cfgs = [{r: route_config(r, srv) for r in ROUTES} for srv in self.replicas]
        self.load = [0] * len(self.replicas)
        self.memory = memory or {}
        self.clock = clock or GpuClock(len(self.replicas))
        self.cost_override, self.run_id, self.split, self.share = cost_override, run_id, split, graft_build_share
        self.tokens_override = tokens_override     # fake runs: the label's output tokens (the fake's own are logged too)

    def sampled(self) -> set:
        return {r for r in ROUTES if self.cfgs[0][r].n_samples > 1}

    async def run_step(self, item: dict, route: str, repeat: int, charge_build: bool = False) -> dict:
        from flotilla.memory import memory_route
        from flotilla.core import system
        from flotilla.core.trace import Trace
        k = min(range(len(self.replicas)), key=lambda j: self.load[j])
        cfg = self.cfgs[k][route]
        self.load[k] += 1
        tr = Trace(run_id=self.run_id, protocol_version=cfg.protocol_version,
                   prompt_versions={"solver": cfg.prompt_version, "verifier": cfg.verifier_version},
                   benchmark=item.get("bench", item.get("source", "?")), item_id=item["item_id"], split=self.split)
        key, err = object(), None
        token = STEP.set((item["item_id"], route, repeat))
        self.clock.start(key)
        try:
            if route in MEMORY_ROUTES:
                tr.prompt_versions["memory_block"] = memory_route.MEMORY_BLOCK_VERSION
                await memory_route.run_memory_route(route, memory_route.normalize_item(item),
                                                    self.memory.get(item["item_id"]), cfg, tr)
            else:
                rt = {"router": "rl", "route": route, "task_type": item.get("task_type", "general"), "models": cfg.solvers}
                await system.answer(item, rt, cfg, tr)
        except Exception as e:  # noqa: BLE001 - a failed step is logged with its error; the chain goes on
            err = f"{type(e).__name__}: {e}"[:300]
        finally:
            gpu = self.clock.stop(key)
            STEP.reset(token)
            self.load[k] -= 1
        d = tr.finish()
        if self.cost_override is not None:
            gpu = float(self.cost_override(item["item_id"], route))
        build = 0.0
        if charge_build and route in MEMORY_ROUTES:
            b = (self.memory.get(item["item_id"]) or {}).get("build") or {}
            build = float(b.get("wall_seconds") or 0.0) * self.share
        v = d.get("verifier") or {}
        att = v.get("attempts") or []
        samples = [s for m in d["models"] for s in m["samples"]]
        tok_out = sum(s["tokens_out"] for s in samples)
        extra = {}
        if self.tokens_override is not None:
            extra = {"tokens_out_loop": tok_out, "tokens_total_loop": d["tokens_total"]}
            tok_out = int(self.tokens_override(item["item_id"], route))
        return {**extra, "route": route, "repeat": repeat, "replica": k, "answer": d["final_answer"],
                "verdict": "error" if err else v.get("verdict", "none"), "first_verdict": att[0]["verdict"] if att else None,
                "retried": len(att) > 1, "gpu_seconds": round(gpu + build, 4), "graft_build_gpu_seconds": round(build, 4),
                "tokens_in": sum(s["tokens_in"] for s in samples), "tokens_out": tok_out,
                "tokens_total": d["tokens_total"] if self.tokens_override is None else tok_out, "model_calls": len(d.get("call_log") or []), "samples": len(samples),
                "wall_seconds": d["wall_seconds"], "error": err, "trace": d}


class ReplayRunner:
    """A step = the label's answer for (item, route) and its label GPU-seconds; verdict from system.verify on that
    answer. No model call; used by `estimate` (and the optional --warm-start-epochs)."""

    def __init__(self, data: Data):
        self.data, self._v = data, {}

    def sampled(self) -> set:
        return sampled_routes()

    async def run_step(self, item: dict, route: str, repeat: int, charge_build: bool = False) -> dict:
        from flotilla.core import system
        i = item["item_id"]
        v = self.data.rows[i].get(route) or {}
        ans = v.get("answer") or None
        if (i, route) not in self._v:
            self._v[(i, route)] = system.verify(item.get("task", ""), item.get("task_type", "general"), ans,
                                                item.get("options"), item.get("public_tests"))["verdict"]
        return {"route": route, "repeat": repeat, "replica": 0, "answer": ans, "verdict": self._v[(i, route)],
                "first_verdict": None, "retried": None, "gpu_seconds": round(self.data.gpu(i, route), 4),
                "graft_build_gpu_seconds": 0.0, "tokens_in": 0, "tokens_out": int(v.get("tokens_out") or 0),
                "tokens_total": int(v.get("tokens_out") or 0), "model_calls": v.get("calls"), "samples": None,
                "wall_seconds": v.get("wall_seconds"), "error": None, "trace": None}


# ---------------------------------------------------------------- graders

class PoolGrader:
    """Pool questions: the router-label graders (label_loop.grade) with the pool's gold; LongMemEval questions:
    LongMemEval's judge prompt on Qwen (memory_route.judge_answer). Cached per (id, answer)."""

    def __init__(self, pool: dict, lme: dict, judge_srv: dict | None):
        self.pool, self.lme, self.judge, self.cache = pool, lme, judge_srv, {}

    async def grade(self, item: dict, answer: str | None) -> bool:
        if answer is None:
            return False
        i = item["item_id"]
        if (i, answer) not in self.cache:
            if i in self.lme:
                from flotilla.memory.memory_route import judge_answer
                ok = (await judge_answer(self.lme[i], answer, self.judge))["correct"]
            elif i in self.pool:
                from flotilla.routers.label_loop import grade
                ok = await asyncio.to_thread(grade, self.pool[i], answer)
            else:
                raise SystemExit(f"{i}: no gold (not in --pool or --memory-items)")
            self.cache[(i, answer)] = bool(ok)
        return self.cache[(i, answer)]


class LabelGrader:
    """Fake runs: an answer is right if it equals (stripped) an answer the labels mark correct for the item, or the
    gold given for it (always-wrong audit golds)."""

    def __init__(self, rows: dict, golds: dict | None = None):
        self.ok = defaultdict(set)
        for i, row in rows.items():
            for r in ROUTES:
                if route_on(row, r) and row[r]["correct"] and row[r].get("answer"):
                    self.ok[i].add(row[r]["answer"].strip())
        for i, g in (golds or {}).items():
            self.ok[i].add(str(g).strip())

    async def grade(self, item: dict, answer: str | None) -> bool:
        return answer is not None and answer.strip() in self.ok[item["item_id"]]


# ---------------------------------------------------------------- fake Qwen that replays answers

def infer_route(messages: list[dict], temperature: float, kw: dict) -> str:
    """Which route sent this request, from what the loop put in it: thinking off (chat_template_kwargs), tool schemas,
    sampling temperature, and the GRAFT memory block."""
    think = ((kw.get("extra_body") or {}).get("chat_template_kwargs") or {}).get("enable_thinking", True)
    tools, samp = "tools" in kw, temperature > 0
    text = " ".join(m["content"] if isinstance(m["content"], str) else "" for m in messages if m["role"] == "user")
    base = {(False, False, False): "fast", (False, True, False): "tools", (True, False, False): "deep",
            (True, True, False): "deep_tools", (True, False, True): "vote", (True, True, True): "vote_tools"}.get(
        (bool(think), tools, samp), f"unknown(think={think},tools={tools},sampled={samp})")
    if "MEMORY (" in text:
        return {"fast": "memory", "deep": "memory_deep", "vote": "vote_memory", "deep_tools": "deep_tools_memory"}.get(base, base + "+memory")
    return base


def _fake_class():
    from flotilla.memory.memory_route import FakeQwen

    class ReplayQwen(FakeQwen):
        """memory_route.FakeQwen whose solver calls answer from a table: answers[(item_id, route)] is a string or a list
        indexed by the route's run number on the item (the last entry repeats). The step comes from STEP; the route
        the request itself implies is checked against it (mismatches kept in .mismatch). Calls outside a step (judge)
        go to FakeQwen."""

        def __init__(self, answers: dict):
            super().__init__()
            self.answers, self.mismatch, self.calls = answers, [], Counter()

        async def create(self, model, messages, temperature=0.0, max_tokens=None, **kw):
            step = STEP.get()
            last = messages[-1]["content"]
            if step is None or (isinstance(last, str) and last.startswith("I will give you")):
                return await super().create(model, messages, temperature, max_tokens, **kw)
            i, route, k = step
            self.seen.append({"model": model, "messages": messages, "kwargs": kw, "step": step, "temperature": temperature})
            self.calls[(i, route)] += 1
            got = infer_route(messages, temperature, kw)
            if got != route:
                self.mismatch.append((i, route, got))
            a = self.answers.get((i, route))
            if isinstance(a, list):
                a = a[min(k, len(a) - 1)] if a else None
            content = json.dumps({"final_answer": a if a is not None else "I do not know", "confidence": 0.9, "sources": []})
            from types import SimpleNamespace as NS
            msg = NS(content=content, tool_calls=None, reasoning_content="")
            n_in = sum(len(m["content"]) if isinstance(m["content"], str) else 0 for m in messages) // 4
            return NS(id="fake", choices=[NS(message=msg, finish_reason="stop")],
                      usage=NS(prompt_tokens=max(1, n_in), completion_tokens=max(1, len(content) // 4)))
    return ReplayQwen


def replay_qwen(answers: dict):
    return _fake_class()(answers)


# ---------------------------------------------------------------- one chain

def item_rng(seed: int, epoch: int, item_id: str) -> np.random.Generator:
    return np.random.default_rng([seed, epoch, int(hashlib.sha256(item_id.encode()).hexdigest()[:12], 16)])


def final_answer(steps: list[dict], rule: str, ttype: str) -> tuple[str | None, int | None]:
    if not steps:
        return None, None
    if rule == "last":
        return steps[-1]["answer"], len(steps) - 1
    if rule == "vote":
        from flotilla.core.system import vote
        answers = [s["answer"] for s in steps]
        w = vote(ttype, answers)["winner"]
        if w is not None:
            k = max(j for j, s in enumerate(steps) if s["answer"] == w)
            return w, k
    acc = [j for j, s in enumerate(steps) if s["verdict"] == "accept" and s["answer"] is not None]
    k = acc[-1] if acc else len(steps) - 1
    return steps[k]["answer"], k


@dataclass
class Ctx:
    data: Data
    prior: Prior
    cfg: RLConfig
    seed: int
    allow_held_out: bool = False


async def run_chain(item: dict, ctx: Ctx, policy: Policy, runner, grader, epoch: int, greedy: bool,
                    mode: str, trace_sink=None) -> dict:
    i = item["item_id"]
    if i in ctx.data.held_out and not ctx.allow_held_out:
        raise SystemExit(f"{i} is a held-out question; held-out runs only with evaluate --held-out")
    p, pick = ctx.prior.get(i, item)
    st = State(item, p, pick, offered_routes(item, ctx.data.rows.get(i), ctx.cfg))
    rng = None if greedy else item_rng(ctx.seed, epoch, i)
    decisions, stop_reason, mem_charged = [], None, False
    while True:
        allowed, forced = policy.mask(st)
        if forced is not None:
            stop_reason = forced
            break
        psi = policy.features(st)
        a, q = policy.act(psi, allowed, rng)
        decisions.append({"t": st.t, "action": ACTIONS[a], "a": a, "psi": [round(float(x), 6) for x in psi],
                          "allowed": [ACTIONS[j] for j in np.where(allowed)[0]],
                          "q": {ACTIONS[j]: round(float(q[j]), 4) for j in np.where(allowed)[0]}})
        if ACTIONS[a] == STOP:
            stop_reason = "policy"
            break
        route = ACTIONS[a]
        charge = route in MEMORY_ROUTES and not mem_charged
        mem_charged |= charge
        res = await runner.run_step(item, route, st.runs[route], charge_build=charge)
        res["correct"] = await grader.grade(item, res["answer"])
        tr = res.pop("trace")
        if trace_sink is not None and tr is not None:
            trace_sink({"mode": mode, "epoch": epoch, "item_id": i, "step": st.t, "route": route, "trace": tr})
        st.steps.append(res)
        st.runs[route] += 1
        st.cost += res["gpu_seconds"]
    fa, k = final_answer(st.steps, ctx.cfg.final_rule, task_type(item))
    correct = bool(fa is not None and await grader.grade(item, fa))
    gpu = sum(s["gpu_seconds"] for s in st.steps)
    reward = float(correct) - ctx.cfg.alpha * gpu
    for d in decisions:  # reward-to-go: the outcome minus the GPU-seconds of this step and the later ones
        d["target"] = round(float(correct) - (0.0 if d["action"] == STOP else
                                              ctx.cfg.alpha * sum(s["gpu_seconds"] for s in st.steps[d["t"]:])), 6)
    return {"mode": mode, "epoch": epoch, "item_id": i, "source": ctx.data.rows.get(i, {}).get("source", item.get("source")),
            "task_type": item.get("task_type"), "alpha": ctx.cfg.alpha, "prior": {"router": ctx.prior.name, "pick": pick},
            "greedy": greedy, "steps": st.steps, "stop_reason": stop_reason, "final_answer": fa, "final_from_step": k,
            "correct": correct, "gpu_seconds": round(gpu, 4), "tokens_total": sum(s["tokens_total"] or 0 for s in st.steps),
            "tokens_out": sum(s["tokens_out"] or 0 for s in st.steps), "n_steps": len(st.steps),
            "reward": round(reward, 6), "decisions": decisions}


# ---------------------------------------------------------------- logs, resume

def read_jsonl(path: Path) -> list[dict]:
    """Rows of a chain log; a cut-off last line (job killed mid-write) is dropped."""
    out = []
    if path.exists():
        for line in open(path):
            try:
                out.append(json.loads(line))
            except ValueError:
                break
    return out


def repair_log(path: Path) -> int:
    """Drops a cut-off tail (a job killed mid-write) so new chains are appended after the last whole line."""
    if not path.exists():
        return 0
    lines = path.read_text().splitlines(keepends=True)
    good = []
    for line in lines:
        try:
            json.loads(line)
        except ValueError:
            break
        if not line.endswith("\n"):
            line += "\n"
        good.append(line)
    if len(good) < len(lines) or (lines and not lines[-1].endswith("\n")):
        path.write_text("".join(good))
    return len(lines) - len(good)


def apply_chain(policy: Policy, chain: dict) -> None:
    for d in chain["decisions"]:
        policy.update(d["psi"], ACTIONS.index(d["action"]), d["target"])


def check_config(out: Path, cfg: RLConfig, extra: dict, name: str = "rl_config.json") -> None:
    p = out / name
    new = {"cfg": cfg.__dict__, **extra}
    if p.exists():
        old = json.loads(p.read_text())
        diff = [k for k in KEY_FIELDS if old["cfg"].get(k) != cfg.__dict__.get(k)]
        diff += [k for k in ("prior", "labels_hashes", "seed") if old.get(k) != extra.get(k)]
        if diff:
            raise SystemExit(f"{p} differs from this run in {diff}: resume with the same settings or use a new --out")
        return
    p.write_text(json.dumps(new, indent=1))


async def run_many(items: list[dict], ctx: Ctx, policy: Policy, runner, grader, out: Path, log_name: str, epoch: int,
                   greedy: bool, mode: str, concurrency: int, deadline: float | None, learn: bool, on_done=None) -> int:
    """Runs chains concurrently; each finished chain is appended to the log (and learnt from) at once."""
    sem = asyncio.Semaphore(concurrency)
    for p in (out / f"chains_{log_name}.jsonl", out / f"traces_{log_name}.jsonl"):
        if repair_log(p):
            print(f"[rl_router] {p.name}: dropped a cut-off last line", flush=True)
    logf = open(out / f"chains_{log_name}.jsonl", "a")
    trf = open(out / f"traces_{log_name}.jsonl", "a")
    sink = lambda d: (trf.write(json.dumps(d, ensure_ascii=False) + "\n"), trf.flush())  # noqa: E731
    n = 0

    async def one(it):
        nonlocal n
        async with sem:
            if deadline is not None and time.time() > deadline:
                return
            ch = await run_chain(it, ctx, policy, runner, grader, epoch, greedy, mode, sink)
            if learn:
                apply_chain(policy, ch)
            logf.write(json.dumps(ch, ensure_ascii=False) + "\n")
            logf.flush()
            n += 1
            if on_done:
                on_done(ch)
            print(f"[{mode} e{epoch}] {ch['item_id']}: {' > '.join(s['route'] + '(' + s['verdict'][0] + ')' for s in ch['steps'])}"
                  f" stop={ch['stop_reason']} correct={ch['correct']} gpu_s={ch['gpu_seconds']:.1f} r={ch['reward']:.3f}", flush=True)
    try:
        await asyncio.gather(*[one(it) for it in items])
    finally:
        logf.close()
        trf.close()
    return n


# ---------------------------------------------------------------- environments (live vLLM or fake)

@contextlib.contextmanager
def served(a, out: Path):
    """Replica server maps. --serve SERVERS.json starts --replicas vLLM servers of --server-name on this node (one GPU
    each, flotilla.core.serve's ports and health check); --server-url uses a running server; --fake none."""
    if getattr(a, "fake", False):
        yield [None]
        return
    if a.server_url:
        yield [{a.server_name: {"url": a.server_url, "model": a.server_model or a.server_name}}]
        return
    if not a.serve:
        raise SystemExit("live runs need --serve configs/servers.json or --server-url")
    from flotilla.core.serve import free_port, wait_healthy
    spec = json.loads(Path(a.serve).read_text())[a.server_name]
    vllm = str(Path(sys.executable).parent / "vllm")
    procs, reps = [], []
    try:
        for k in range(a.replicas):
            port = free_port()
            gpus = ",".join(str(g) for g in range(k * spec["gpus"], (k + 1) * spec["gpus"]))
            cmd = [vllm, "serve", spec["model"], "--served-model-name", a.server_name, "--port", str(port),
                   "--tensor-parallel-size", str(spec["gpus"]), "--seed", "20261119"] + spec.get("args", [])
            log = open(out / f"server-{a.server_name}-{k}.log", "a")
            print(f"[rl_router] replica {k}: GPUs {gpus}, port {port}", flush=True)
            procs.append((subprocess.Popen(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": gpus}, stdout=log,
                                           stderr=subprocess.STDOUT), port))
            reps.append({a.server_name: {"url": f"http://127.0.0.1:{port}/v1", "model": a.server_name}})
        for p, port in procs:
            wait_healthy(port, p, a.startup_timeout)
        yield reps
    finally:
        for p, _ in procs:
            p.terminate()
        for p, _ in procs:
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()


def read_pool(path: str | None, wanted: set) -> dict:
    out = {}
    if path:
        for line in open(path):
            m = _ID.match(line)
            if m is not None and json.loads(f'"{m.group(1)}"') not in wanted:
                continue
            r = json.loads(line)
            i = r.get("id", r.get("item_id"))
            if i in wanted:
                out[i] = r
    return out


def live_env(a, data: Data, ids: list[str], replicas: list[dict], out: Path, split: str):
    from flotilla.memory import memory_route
    wanted = set(ids)
    pool = read_pool(a.pool, wanted)
    lme = read_pool(a.memory_items, wanted) if a.memory_items else {}
    miss = sorted(i for i in ids if i not in pool and i not in lme)
    if miss:
        raise SystemExit(f"{len(miss)} questions have no gold in --pool/--memory-items, e.g. {miss[:5]}")
    memory = {}
    mem_items = [data.items[i] for i in ids if data.items[i].get("sessions")]
    if mem_items and any(r in MEMORY_ROUTES for r in a.routes):
        cfg = route_config("memory", replicas[0])
        mem_conf = cfg.extra["memory"]
        memory = memory_route.prepare([memory_route.normalize_item(it) for it in mem_items], mem_conf,
                                      memory_route.llm_for(mem_conf, cfg.servers, cfg.solvers),
                                      a.graft_cache or memory_route.default_cache(out), a.build_workers)
    runner = LoopRunner(replicas, memory, GpuClock(len(replicas) * a.gpus_per_replica), run_id=out.name, split=split,
                        graft_build_share=a.graft_build_share)
    srv = next(iter(replicas[0].values()))
    return runner, PoolGrader(pool, lme, srv)


def fake_env(data: Data, answers: dict, golds: dict, split: str):
    """Fake Qwen through the real loop; label answers, label GPU-seconds and output tokens, label grading."""
    from flotilla.core import system
    fake = replay_qwen(answers)
    system.client_for = lambda srv: fake
    runner = LoopRunner([None], {}, GpuClock(1), cost_override=data.gpu, run_id="dry-run", split=split,
                        tokens_override=lambda i, r: (data.rows[i].get(r) or {}).get("tokens_out") or 0)
    return runner, LabelGrader(data.rows, golds), fake


# ---------------------------------------------------------------- train / evaluate

def ordered_ids(ids: list[str], seed: int, epoch: int, cap: int) -> list[str]:
    o = sorted(ids)
    random.Random(f"{seed}-{epoch}").shuffle(o)
    return o[:cap] if cap else o


def prior_spec(a) -> str:
    return a.prior


async def train_async(a, data: Data, ids: list[str], runner, grader, out: Path, cfg: RLConfig, prior: Prior) -> Policy:
    policy = Policy(cfg, data.cost, runner.sampled())
    ctx = Ctx(data, prior, cfg, a.seed)
    deadline = time.time() + a.stop_after if a.stop_after else None
    # optional zero-GPU warm start: chains replayed from the labels (real Qwen answers from the labelling runs)
    for n in ("warm", "train"):
        repair_log(out / f"chains_{n}.jsonl")
    warm = read_jsonl(out / "chains_warm.jsonl")
    for ch in warm:
        apply_chain(policy, ch)
    wdone = {(c["epoch"], c["item_id"]) for c in warm}
    for ep in range(a.warm_start_epochs):
        todo = [data.items[i] for i in ordered_ids(ids, a.seed, -1 - ep, 0) if (-1 - ep, i) not in wdone]
        await run_many(todo, ctx, policy, ReplayRunner(data), LabelGrader(data.rows), out, "warm", -1 - ep, False,
                       "warm", 64, None, True)
    chains = read_jsonl(out / "chains_train.jsonl")
    for ch in chains:
        apply_chain(policy, ch)
    done = {(c["epoch"], c["item_id"]) for c in chains}
    if chains:
        print(f"[rl_router] resumed: {len(chains)} chains replayed, {policy.updates} updates", flush=True)
    for ep in range(a.epochs):
        todo = [data.items[i] for i in ordered_ids(ids, a.seed, ep, a.max_questions) if (ep, i) not in done]
        save = lambda ch: policy.save(out / "policy.npz", {"epoch": ep})  # noqa: E731
        await run_many(todo, ctx, policy, runner, grader, out, "train", ep, False, "train", a.concurrency, deadline, True, save)
        left = [i for i in ordered_ids(ids, a.seed, ep, a.max_questions)
                if (ep, i) not in {(c["epoch"], c["item_id"]) for c in read_jsonl(out / "chains_train.jsonl")}]
        if left:
            print(f"[rl_router] stopped in epoch {ep} with {len(left)} questions left (--stop-after); rerun to resume", flush=True)
            policy.save(out / "policy.npz", {"epoch": ep, "complete": False})
            return policy
        policy.save(out / f"policy_epoch{ep}.npz", {"epoch": ep, "complete": True})
    policy.save(out / "policy.npz", {"epochs": a.epochs, "complete": True})
    return policy


def cmd_train(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = load_data(a.labels, a.items, ["train"])
    ids = list(data.ids["train"])
    if a.ids:
        bad = [i for i in a.ids if i not in set(ids)]
        if bad:
            raise SystemExit(f"--ids must be train questions; not in train: {bad[:5]}" +
                             (" (held-out)" if any(i in data.held_out for i in bad) else ""))
        ids = [i for i in ids if i in set(a.ids)]
    cfg = RLConfig.from_args(a)
    prior = make_prior(a.prior, data, data.ids["train"], a.prior_tau)
    check_config(out, cfg, {"prior": a.prior, "labels_hashes": data.hashes, "seed": a.seed,
                            "labels": data.labels_dir, "questions": len(ids)})
    with served(a, out) as reps:
        runner, grader = live_env(a, data, ids, reps, out, "train")
        t0 = time.time()
        asyncio.run(train_async(a, data, ids, runner, grader, out, cfg, prior))
        job_s = time.time() - t0
    summarize_log(out, "train", job_s, runner.clock)


def summarize_log(out: Path, name: str, job_s: float, clock: GpuClock) -> None:
    ch = read_jsonl(out / f"chains_{name}.jsonl")
    acc = Path(out / "compute.jsonl")
    with open(acc, "a") as f:
        f.write(json.dumps({"log": name, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "job_seconds": round(job_s, 1),
                            "gpus": clock.gpus, "gpu_seconds_job": round(job_s * clock.gpus, 1),
                            "gpu_seconds_idle": round(clock.idle, 1), "chains_total": len(ch),
                            "chain_gpu_seconds_total": round(sum(c["gpu_seconds"] for c in ch), 1)}) + "\n")


async def eval_async(items, ctx, policy, runner, grader, out, name, concurrency, deadline):
    done = {c["item_id"] for c in read_jsonl(out / f"chains_{name}.jsonl")}
    todo = [it for it in items if it["item_id"] not in done]
    await run_many(todo, ctx, policy, runner, grader, out, name, 0, True, "eval", concurrency, deadline, False)


def cmd_evaluate(a) -> None:
    out = Path(a.out)
    split = "held_out" if a.held_out else "dev"
    data = load_data(a.labels, a.items, ["train", split], held_out_ok=a.held_out)
    policy = Policy.load(Path(a.policy) if a.policy else out / "policy.npz")
    for k in ("max_steps", "max_gpu_s"):          # evaluation may tighten the budget; nothing else changes
        if getattr(a, k, None) is not None:
            setattr(policy.cfg, k, getattr(a, k))
    conf = json.loads((out / "rl_config.json").read_text()) if (out / "rl_config.json").exists() else {}
    prior = make_prior(a.prior or conf.get("prior", "route-accuracy"), data, data.ids["train"], a.prior_tau)
    ids = list(data.ids[split])
    ctx = Ctx(data, prior, policy.cfg, a.seed, allow_held_out=a.held_out)
    with served(a, out) as reps:
        a.routes = policy.cfg.routes
        runner, grader = live_env(a, data, ids, reps, out, split)
        t0 = time.time()
        asyncio.run(eval_async([data.items[i] for i in ids], ctx, policy, runner, grader, out, f"eval_{split}",
                               a.concurrency, time.time() + a.stop_after if a.stop_after else None))
        summarize_log(out, f"eval_{split}", time.time() - t0, runner.clock)
    exclude = a.exclude or (str(out / "excluded_wrong_gold.txt") if (out / "excluded_wrong_gold.txt").exists() else None)
    if exclude is None:
        print("[rl_router] WARNING: no --exclude list: beyond_oracle counts wrong-gold questions too", flush=True)
    report(out, data, ids, split, read_jsonl(out / f"chains_eval_{split}.jsonl"), prior, policy.cfg,
           read_exclusions(exclude), exclude, dry=False)


# ---------------------------------------------------------------- evaluation table and beyond-oracle report

def beyond_oracle(chains: list[dict], rows: dict, excluded: set) -> dict:
    """Questions the RL chain got right that every fixed route got wrong in the labels (every available route
    correct=False), split into counted and excluded (wrong gold)."""
    counted, skipped = [], []
    for c in chains:
        row = rows.get(c["item_id"])
        if row is None or not c["correct"]:
            continue
        routes = [r for r in ROUTES if route_on(row, r)]
        if routes and not any(row[r]["correct"] for r in routes):
            (skipped if c["item_id"] in excluded else counted).append(c)
    return {"count": len(counted), "excluded_solved": len(skipped), "questions": counted, "excluded": skipped}


def _route_stats(data: Data, ids: list[str], r: str) -> dict | None:
    if not all(route_on(data.rows[i], r) for i in ids):
        return None
    return {"accuracy": float(np.mean([data.rows[i][r]["correct"] for i in ids])),
            "gpu_seconds": float(np.mean([data.gpu(i, r) for i in ids])),
            "output_tokens": float(np.mean([data.rows[i][r].get("tokens_out") or 0 for i in ids]))}


def report(out: Path, data: Data, ids: list[str], split: str, chains: list[dict], prior: Prior, cfg: RLConfig,
           excluded: set, exclude_file: str | None, dry: bool, stem: str | None = None, title: str = "") -> list[dict]:
    by = {c["item_id"]: c for c in chains}
    run = [by[i] for i in ids if i in by]
    full = [r for r in ROUTES if all(route_on(data.rows[i], r) for i in ids)]
    stats = {r: _route_stats(data, ids, r) for r in full}
    ref_route = max(full, key=lambda r: (data.summary_acc.get(r, stats[r]["accuracy"]), -ROUTES.index(r)))
    ref = stats[ref_route]
    bo = beyond_oracle(run, data.rows, excluded)
    head = "DRY RUN, NOT A RESULT: fake Qwen replaying the labels' answers through the real loop. " if dry else ""

    def row(name, kind, res, steps="", picked="", bo_n="", bo_x="", rule=True):
        return {"row": name, "kind": kind, "split": split, "questions": res["questions"],
                "accuracy": round(res["accuracy"], 4), "gpu_seconds_per_question": round(res["gpu_seconds"], 2),
                "output_tokens_per_question": round(res["output_tokens"]), "mean_steps": steps,
                "points_vs_best_fixed": round(100 * (res["accuracy"] - ref["accuracy"]), 1),
                "gpu_vs_best_fixed": round(res["gpu_seconds"] / ref["gpu_seconds"], 3) if ref["gpu_seconds"] else None,
                "keep_rule": sr.keep_rule(res, ref) if rule else "", "beyond_oracle": bo_n,
                "solved_but_wrong_gold": bo_x, "picked": picked}

    rows = []
    if run:
        res = {"questions": len(run), "accuracy": float(np.mean([c["correct"] for c in run])),
               "gpu_seconds": float(np.mean([c["gpu_seconds"] for c in run])),
               "output_tokens": float(np.mean([c["tokens_out"] for c in run]))}
        chains_c = Counter(" > ".join(s["route"] for s in c["steps"]) for c in run)
        rows.append(row("rl", f"RL router (live chains, alpha={cfg.alpha})", res,
                        round(float(np.mean([c["n_steps"] for c in run])), 2),
                        "; ".join(f"{k}:{v}" for k, v in chains_c.most_common(8)), bo["count"], bo["excluded_solved"]))
    picks = [prior.get(i, data.items[i])[1] for i in ids]
    if all(p is not None and route_on(data.rows[i], p) for i, p in zip(ids, picks)):
        res = {"questions": len(ids), "accuracy": float(np.mean([data.rows[i][p]["correct"] for i, p in zip(ids, picks)])),
               "gpu_seconds": float(np.mean([data.gpu(i, p) for i, p in zip(ids, picks)])),
               "output_tokens": float(np.mean([data.rows[i][p].get("tokens_out") or 0 for i, p in zip(ids, picks)]))}
        rows.append(row(f"start: {prior.name}", "supervised pick, one route (labels)", res, 1,
                        " ".join(f"{k}:{v}" for k, v in sorted(Counter(picks).items()))))
    for r in full:
        rows.append(row(r + (" (best fixed)" if r == ref_route else ""), "fixed route (labels)", {"questions": len(ids), **stats[r]},
                        1, rule=False))
    # oracle: per question, the cheapest route right on it among the routes available on it (cheapest = mean cost)
    by_cost = sorted(ROUTES, key=lambda r: (data.cost[r], ROUTES.index(r)))
    avail = {i: [r for r in by_cost if route_on(data.rows[i], r)] for i in ids}
    orc = [next((r for r in avail[i] if data.rows[i][r]["correct"]), None) for i in ids]
    res = {"questions": len(ids), "accuracy": float(np.mean([o is not None for o in orc])),
           "gpu_seconds": float(np.mean([data.gpu(i, o or avail[i][0]) for i, o in zip(ids, orc)])),
           "output_tokens": float(np.mean([data.rows[i][o or avail[i][0]].get("tokens_out") or 0 for i, o in zip(ids, orc)]))}
    rows.append(row("oracle", "cheapest correct fixed route, known only after trying all (labels)", res, rule=False))
    stem = stem or f"table_{split}" + ("_dryrun" if dry else "")
    note = (f"{head}{title}test-04 router 5 (RL, flotilla/routers/rl_router.py) on {split} ({len(ids)} questions; {len(run)} chains "
            f"run). Reward = 1[correct] - alpha x GPU-s, alpha = {cfg.alpha}; max steps {cfg.max_steps}, max GPU-s "
            f"{cfg.max_gpu_s}, final rule {cfg.final_rule}. Prior: {prior.name}. Fixed routes and the oracle from the "
            f"labels ({data.labels_dir}, {data.hashes.get('per_question.jsonl')}); the RL row from its own chains (new "
            f"runs, GPU-s shared live). beyond_oracle = questions the RL router got right that every fixed route got "
            f"wrong, wrong-gold questions excluded ({len(excluded)} ids from {exclude_file}); solved_but_wrong_gold = "
            f"such questions it got right but whose gold is wrong (not counted). Keep rule vs the best fixed route.")
    sr.write_table(out, stem, rows, note)
    write_beyond_report(out / f"beyond_oracle_{split}{'_dryrun' if dry else ''}.md", bo, data, cfg, split, head, exclude_file)
    (out / f"{stem}.json").write_text(json.dumps(sr._jsonable({"split": split, "dry_run": dry, "rows": rows,
                                                               "beyond_oracle_ids": [c["item_id"] for c in bo["questions"]],
                                                               "excluded_solved_ids": [c["item_id"] for c in bo["excluded"]]}), indent=1))
    print((out / f"{stem}.md").read_text(), flush=True)
    return rows


def _cell(s, n=60):
    s = "" if s is None else str(s).replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def chain_md(c: dict) -> list[str]:
    md = ["| step | route | run | answer | verdict | correct | GPU-s | tokens out |", "|---|---|---|---|---|---|---|---|"]
    for t, s in enumerate(c["steps"]):
        md.append(f"| {t + 1} | {s['route']} | {s['repeat'] + 1} | {_cell(s['answer'])} | {s['verdict']} | {s['correct']} | "
                  f"{s['gpu_seconds']:.1f} | {s['tokens_out']} |")
    md.append(f"\nStop: {c['stop_reason']}. Final answer (step {None if c['final_from_step'] is None else c['final_from_step'] + 1}): "
              f"{_cell(c['final_answer'], 200)}; correct {c['correct']}; {c['gpu_seconds']:.1f} GPU-s; reward {c['reward']:.4f}.")
    return md


def write_beyond_report(path: Path, bo: dict, data: Data, cfg: RLConfig, split: str, head: str, exclude_file) -> None:
    md = [f"# Beyond the oracle of fixed routes ({split})", "",
          (f"**{head.strip()}**\n" if head else "") +
          f"Questions the RL router answered correctly that every fixed route got wrong in the labels, wrong-gold "
          f"questions excluded (list: `{exclude_file}`). alpha = {cfg.alpha}.", "",
          f"**Count: {bo['count']}** ({'beats' if bo['count'] > 0 else 'does not beat'} the per-question oracle of fixed "
          f"routes). Solved but excluded (wrong gold): {bo['excluded_solved']}.", ""]
    for title, lst in (("Counted", bo["questions"]), ("Excluded: wrong gold", bo["excluded"])):
        md += [f"## {title} ({len(lst)})", ""]
        for c in lst:
            row = data.rows[c["item_id"]]
            md += [f"### {c['item_id']} · {row.get('source')} · {row.get('task_type')}", "",
                   "Fixed routes in the labels (all wrong): " +
                   "; ".join(f"{r}: {_cell(row[r].get('answer'), 40)}" for r in ROUTES if route_on(row, r)), "",
                   "Chain that solved it:", ""] + chain_md(c) + [""]
    path.write_text("\n".join(md) + "\n")


# ---------------------------------------------------------------- dry run (fake Qwen, real loop, 20 train questions)

def dry_answers(data: Data, ids: list[str], golds: dict, lucky: float, max_repeats: int, seed: int) -> dict:
    """answers[(id, route)] for ReplayQwen: the label's answer; on a sampled route's later runs, for always-wrong
    questions, the audit gold with probability `lucky` (a fake 'lucky sample', so the beyond-oracle path runs)."""
    samp = sampled_routes()
    out = {}
    for i in ids:
        row = data.rows[i]
        none = not any(row[r]["correct"] for r in ROUTES if route_on(row, r))
        for r in ROUTES:
            if not route_on(row, r):
                continue
            a = row[r].get("answer") or None
            if r in samp:
                rng = random.Random(f"{seed}-{i}-{r}")
                out[(i, r)] = [a] + [golds[i] if none and i in golds and rng.random() < lucky else a
                                     for _ in range(max_repeats - 1)]
            else:
                out[(i, r)] = a
    return out


def cmd_dry_run(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    audit = Path(a.audit) if a.audit else Path(a.labels).parent / "audit"
    excl_path = out / "excluded_wrong_gold.txt"
    write_exclusions(excl_path, build_exclusions(audit, tuple(a.exclude_diagnoses)), str(audit / "diagnosis.json"))
    excluded = read_exclusions(excl_path)
    data = load_data(a.labels, a.items, ["train"])
    train = data.ids["train"]
    diag = json.loads((audit / "diagnosis.json").read_text())
    rng = random.Random(a.seed)
    aw = sorted(i for i in train if i in diag)
    pick_aw = sorted(rng.sample([i for i in aw if diag[i][0] == "wrong gold"], a.include_always_wrong // 2) +
                     rng.sample([i for i in aw if diag[i][0] != "wrong gold"], a.include_always_wrong - a.include_always_wrong // 2))
    rest = rng.sample(sorted(set(train) - set(aw)), a.n - len(pick_aw))
    ids = sorted(pick_aw + rest)
    (out / "dry_run_ids.json").write_text(json.dumps({"ids": ids, "always_wrong_included": pick_aw, "seed": a.seed}, indent=1))
    a.max_questions, a.stop_after = 0, None
    cfg = RLConfig.from_args(a)
    prior = make_prior(a.prior, data, train, a.prior_tau)
    golds = audit_golds(audit)
    answers = dry_answers(data, ids, golds, a.fake_lucky, cfg.max_repeats, a.seed)
    check_config(out, cfg, {"prior": a.prior, "labels_hashes": data.hashes, "seed": a.seed, "labels": data.labels_dir,
                            "questions": len(ids), "dry_run": True})
    runner, grader, fake = fake_env(data, answers, golds, "train")
    sub = Data({i: data.rows[i] for i in ids}, {"train": ids}, data.items, data.cost, data.rate, data.held_out,
               data.labels_dir, data.hashes, data.summary_acc)
    policy = asyncio.run(train_async(a, sub, ids, runner, grader, out, cfg, prior))
    ctx = Ctx(sub, prior, cfg, a.seed)
    asyncio.run(eval_async([data.items[i] for i in ids], ctx, policy, runner, grader, out, "eval_train_dryrun",
                           a.concurrency, None))
    if fake.mismatch:
        raise SystemExit(f"the loop sent another route's settings than the step's route: {fake.mismatch[:5]}")
    chains = read_jsonl(out / "chains_eval_train_dryrun.jsonl")
    report(out, sub, ids, "train", chains, prior, cfg, excluded, str(excl_path), dry=True,
           title=f"Trained {a.epochs} epochs on these {len(ids)} train questions and evaluated greedily on the same "
                 f"questions ({len(pick_aw)} always-wrong ones drawn on purpose; fake lucky samples p={a.fake_lucky}). ")
    tr = read_jsonl(out / "chains_train.jsonl")
    bo_tr = beyond_oracle(tr, data.rows, excluded)
    write_beyond_report(out / "beyond_oracle_train_chains_dryrun.md", bo_tr, sub, cfg, "train chains while learning",
                        "DRY RUN, NOT A RESULT: exploring training chains, fake Qwen. ", str(excl_path))
    print(f"[dry-run] {len(tr)} training chains, {len(chains)} evaluation chains; route settings checked on "
          f"{len(fake.seen)} fake calls, 0 mismatches; beyond-oracle in training chains {bo_tr['count']} "
          f"(+{bo_tr['excluded_solved']} wrong gold)", flush=True)


# ---------------------------------------------------------------- estimate (labels only)

def cmd_estimate(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = load_data(a.labels, a.items, ["train", "dev"])
    cfg = RLConfig.from_args(a)
    prior = make_prior(a.prior, data, data.ids["train"], a.prior_tau)
    ctx = Ctx(data, prior, cfg, a.seed)
    runner, grader = ReplayRunner(data), LabelGrader(data.rows)
    res = {}
    for name, split, greedy in (("train_exploring", "train", False), ("dev_greedy", "dev", True)):
        policy = Policy(cfg, data.cost, sampled_routes())
        chains = asyncio.run(_collect([data.items[i] for i in data.ids[split]], ctx, policy, runner, grader, greedy))
        g = np.array([c["gpu_seconds"] for c in chains])
        res[name] = {"questions": len(chains), "gpu_s_per_question": round(float(g.mean()), 2),
                     "steps_per_question": round(float(np.mean([c["n_steps"] for c in chains])), 2),
                     "accuracy_replayed": round(float(np.mean([c["correct"] for c in chains])), 4),
                     "first_steps": dict(Counter(c["steps"][0]["route"] for c in chains).most_common()),
                     "chains": dict(Counter(" > ".join(s["route"] for s in c["steps"]) for c in chains).most_common(10))}
    n_tr = len(data.ids["train"]) if not a.max_questions else min(a.max_questions, len(data.ids["train"]))
    train_gs = res["train_exploring"]["gpu_s_per_question"] * n_tr * a.epochs
    dev_gs = res["dev_greedy"]["gpu_s_per_question"] * len(data.ids["dev"])
    startup_h = a.startup_minutes / 60
    est = {"alpha": cfg.alpha, "epochs": a.epochs, "train_questions_per_epoch": n_tr, "prior": prior.name,
           "label_gpu_s_per_route": {r: round(c, 2) for r, c in data.cost.items() if r in data.summary_acc},
           "simulation": res, "train_gpu_hours": round(train_gs / 3600, 2), "dev_eval_gpu_hours": round(dev_gs / 3600, 2),
           "note": ("GPU-seconds per step = the labels' per-question GPU-seconds (job GPU time spread by wall time, about "
                    "18% high: run-03 reran 263 questions). The exploring policy is the untrained prior with Thompson "
                    "sampling; learning changes the chains, so this is a first-epoch rate. Wall hours on k GPUs (k vLLM "
                    "replicas) = GPU-hours / k, since the labels' GPU-s already include batching at concurrency 64."),
           "wall_hours": {f"{k}_gpus": round((train_gs + dev_gs) / 3600 / k + startup_h, 2) for k in (1, 4)},
           "gpu_hours_total_incl_startup": {f"{k}_gpus": round((train_gs + dev_gs) / 3600 + startup_h * k, 2) for k in (1, 4)}}
    (out / "estimate.json").write_text(json.dumps(est, indent=1))
    print(json.dumps(est, indent=1), flush=True)


async def _collect(items, ctx, policy, runner, grader, greedy):
    return [await run_chain(it, ctx, policy, runner, grader, 0, greedy, "estimate") for it in items]


# ---------------------------------------------------------------- CLI

def cmd_exclusions(a) -> None:
    rows = build_exclusions(a.audit, tuple(a.exclude_diagnoses))
    write_exclusions(a.out, rows, str(Path(a.audit) / "diagnosis.json"))
    print(f"[rl_router] {len(rows)} ids ({', '.join(a.exclude_diagnoses)}) -> {a.out}", flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("train", "evaluate", "dry-run", "priors", "estimate", "exclusions"):
        p = sub.add_parser(c)
        if c == "exclusions":
            p.add_argument("--audit", required=True, help="always-wrong audit folder: diagnosis.json, always_wrong.md")
            p.add_argument("--out", required=True)
            p.add_argument("--exclude-diagnoses", nargs="+", default=["wrong gold"])
            continue
        p.add_argument("--labels", required=True, help="graded folder: per_question.jsonl, split.json, summary.json")
        p.add_argument("--items", nargs="+", required=True, help="run item files/globs (item_id, task, task_type, ...)")
        p.add_argument("--out", required=True)
        p.add_argument("--seed", type=int, default=SEED)
        if c == "priors":
            p.add_argument("--router-dir", required=True, help="strategy_router output folder")
            p.add_argument("--router", choices=sr.ROUTERS, help="default: the best on dev")
            p.add_argument("--device", default=None)
            p.add_argument("--held-out", action="store_true")
            continue
        p.add_argument("--prior", default=None if c == "evaluate" else "route-accuracy",
                       help="file:PRIORS.jsonl (from `priors`) or route-accuracy")
        p.add_argument("--prior-tau", type=float, default=0.95)
        p.add_argument("--alpha", type=float, default=None if c == "evaluate" else 0.001, help="reward penalty per GPU-second")
        p.add_argument("--max-steps", type=int, default=None if c == "evaluate" else 3)
        p.add_argument("--max-gpu-s", type=float, default=None if c == "evaluate" else 60.0, help="per question")
        if c != "evaluate":
            p.add_argument("--max-repeats", type=int, default=2, help="runs of one sampled route on one item, in all")
            p.add_argument("--final-rule", choices=["last_accept", "last", "vote"], default="last_accept")
            p.add_argument("--prior-strength", type=float, default=5.0)
            p.add_argument("--sup-bonus", type=float, default=1.0)
            p.add_argument("--explore", type=float, default=0.5, help="Thompson sampling scale (0 = greedy)")
            p.add_argument("--routes", nargs="+", default=list(ROUTES), choices=ROUTES)
            p.add_argument("--epochs", type=int, default=2 if c != "dry-run" else 2)
            p.add_argument("--max-questions", type=int, default=0, help="per epoch (0 = all)")
        p.add_argument("--concurrency", type=int, default=64)
        p.add_argument("--stop-after", type=float, default=None, help="seconds; no new chain starts after this")
        if c == "estimate":
            p.add_argument("--startup-minutes", type=float, default=10.0, help="vLLM start per job")
            continue
        if c == "dry-run":
            p.add_argument("--n", type=int, default=20)
            p.add_argument("--include-always-wrong", type=int, default=4)
            p.add_argument("--fake-lucky", type=float, default=0.5)
            p.add_argument("--audit", default=None, help="default: <labels>/../audit")
            p.add_argument("--exclude-diagnoses", nargs="+", default=["wrong gold"])
            p.add_argument("--warm-start-epochs", type=int, default=0)
            continue
        p.add_argument("--exclude", default=None,
                       help="excluded ids for beyond_oracle (`exclusions` output; default <out>/excluded_wrong_gold.txt)")
        p.add_argument("--serve", help="servers.json: start vLLM replicas on this node")
        p.add_argument("--server-name", default="qwen_w4a16")
        p.add_argument("--replicas", type=int, default=1)
        p.add_argument("--gpus-per-replica", type=int, default=1)
        p.add_argument("--startup-timeout", type=int, default=3600)
        p.add_argument("--server-url", help="a running OpenAI-compatible server instead of --serve")
        p.add_argument("--server-model", default=None)
        p.add_argument("--pool", help="pool questions with gold (label_loop.grade)")
        p.add_argument("--memory-items", help="LongMemEval items with answers (judge)")
        p.add_argument("--graft-cache", default=None)
        p.add_argument("--build-workers", type=int, default=16)
        p.add_argument("--graft-build-share", type=float, default=1 / 16, help="GPU-s per wall-s of a GRAFT build")
        if c == "train":
            p.add_argument("--ids", nargs="*", help="only these train questions")
            p.add_argument("--warm-start-epochs", type=int, default=0, help="replay epochs on the labels before live runs")
        else:
            p.add_argument("--held-out", action="store_true", help="evaluate on held-out (once, at the end); dev otherwise")
            p.add_argument("--policy", default=None, help="default: <out>/policy.npz")
    a = ap.parse_args(argv)
    t0 = time.time()
    {"train": cmd_train, "evaluate": cmd_evaluate, "dry-run": cmd_dry_run, "priors": cmd_priors,
     "estimate": cmd_estimate, "exclusions": cmd_exclusions}[a.cmd](a)
    print(f"[rl_router] {a.cmd} done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
