"""flotilla/strategy_router.py on small synthetic labels: route order and masks from the labels, "none" items, ties,
threshold rule, held-out never parsed, and an end-to-end train + evaluate of the two cheap routers (fake embeddings)."""
import json
import types

import numpy as np
import pytest

from flotilla import strategy_router as sr

# memory is the cheapest route but exists only on items with a memory: an unmasked router would pick it everywhere
SUMMARY = {"questions": 40, "per_strategy": {
    "fast": {"accuracy": 0.5, "mean_wall_seconds": 10.0, "gpu_seconds_job": 80.0},    # 2.0 GPU-s/q, 0.2 per wall-s
    "deep": {"accuracy": 0.9, "mean_wall_seconds": 20.0, "gpu_seconds_job": 400.0},   # 10.0 GPU-s/q
    "memory": {"accuracy": 0.8, "mean_wall_seconds": 5.0, "gpu_seconds_job": 10.0, "questions": 20}}}  # 0.5 GPU-s/q


def _route(ok, wall=10.0, tok=100):
    return {"correct": ok, "tokens_out": tok, "calls": 1, "wall_seconds": wall, "answer": "x"}


def make_labels(tmp_path, n=40):
    """Items 'a*' (has memory, text says alpha) and 'b*' (no memory, text says beta). fast is right on even items,
    deep and memory (where it exists) on every item except the "none" items 0, 1 (train) and 30 (dev)."""
    rows, items, ids = [], [], []
    for i in range(n):
        mem = i % 2 == 0
        iid = f"{'a' if mem else 'b'}{i:03d}"
        ids.append(iid)
        none = i in (0, 1, 30)
        r = {"id": iid, "source": "srcA" if mem else "srcB", "task_type": "math",
             "fast": _route(not none and i % 4 == 0, wall=10.0 + i), "deep": _route(not none, wall=20.0, tok=500)}
        if mem:
            r["memory"] = _route(not none, wall=5.0, tok=50)
        rows.append(r)
        items.append({"item_id": iid, "task": ("alpha memory question " if mem else "beta plain question ") + str(i)})
    d = tmp_path / "graded"
    d.mkdir()
    with open(d / "per_question.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        f.write('{"id": "h_broken", this line is not JSON and must never be parsed\n')
    split = {"seed": 1, "train": ids[:28], "dev": ids[28:], "held_out": ["h_broken"]}
    (d / "split.json").write_text(json.dumps(split))
    (d / "summary.json").write_text(json.dumps(SUMMARY))
    with open(tmp_path / "items.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
        f.write('{"item_id": "h_broken", "task": broken too\n')
    return str(d), [str(tmp_path / "items.jsonl")]


def test_load_routes_masks_costs_and_held_out_untouched(tmp_path):
    labels, items = make_labels(tmp_path)
    sp, info = sr.load(labels, items, ["train", "dev"])
    assert info["routes"] == ["memory", "fast", "deep"]          # cheapest first by GPU-s per question
    assert info["cost_gpu_s"] == {"memory": 0.5, "fast": 2.0, "deep": 10.0}
    tr = sp["train"]
    assert len(tr) == 28 and len(sp["dev"]) == 12
    a = tr.ids.index("a004")
    b = tr.ids.index("b005")
    assert tr.mask[a].tolist() == [True, True, True] and tr.mask[b].tolist() == [False, True, True]
    assert tr.gpu[a, 1] == pytest.approx(0.2 * 14.0)              # fast: 0.2 GPU-s per wall-second x 14 s
    assert tr.gpu[b, 0] == 0 and tr.correct[b, 0] == 0
    with pytest.raises(SystemExit):
        sr.load(labels, items, ["train", "held_out"])               # no --held-out: refused before reading


def test_label_index_cheapest_correct_and_none():
    correct = np.array([[1, 1, 1], [0, 1, 1], [0, 0, 0], [1, 0, 1]], float)
    mask = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1], [0, 1, 1]], bool)
    assert sr.label_index(correct, mask).tolist() == [0, 1, -1, 2]  # last: route 0 right but unavailable


def test_argmax_and_threshold_rules_respect_masks_and_ties():
    mask = np.array([[0, 1, 1], [1, 1, 1], [1, 1, 1]], bool)
    score = np.array([[9.0, 1.0, 1.0], [2.0, 2.0, 1.0], [0.1, 0.3, 0.2]])
    assert sr.masked_argmax(score, mask).tolist() == [1, 0, 1]      # masked max skipped; tie -> cheaper route
    p = np.array([[0.99, 0.4, 0.8], [0.2, 0.7, 0.9], [0.1, 0.3, 0.2]])
    assert sr.cheapest_above(p, mask, 0.6).tolist() == [2, 1, 1]    # row 3: nothing >= 0.6 -> highest p
    assert sr.cheapest_above(p, mask, 0.0).tolist() == [1, 0, 0]    # tau 0: cheapest available route


def test_evaluate_refuses_unavailable_and_counts(tmp_path):
    labels, items = make_labels(tmp_path)
    dev = sr.load(labels, items, ["train", "dev"])[0]["dev"]
    with pytest.raises(AssertionError):
        sr.evaluate(np.zeros(len(dev), int), dev)                    # memory on items without a memory
    r = sr.evaluate(np.full(len(dev), 2), dev)
    assert r["accuracy"] == pytest.approx(11 / 12) and r["picked"] == {"deep": 12}
    assert set(r["by_source"]) == {"srcA", "srcB"} and r["output_tokens"] == 500


def test_best_fixed_oracle_keep_rule_and_choice(tmp_path):
    labels, items = make_labels(tmp_path)
    sp = sr.load(labels, items, ["train", "dev"])[0]
    assert sr.best_fixed(sp["train"]) == 2                          # train accuracy: deep; memory is not on every item
    assert sr.best_fixed(sp["train"], {"memory": 0.99, "fast": 0.95, "deep": 0.9}) == 1   # summary: fast
    assert sr.best_fixed(sp["train"], {"fast": 0.5}, override="deep") == 2
    with pytest.raises(SystemExit):
        sr.best_fixed(sp["train"], None, override="memory")
    dev = sp["dev"]
    o = sr.oracle_picks(dev)
    assert dev.mask[np.arange(len(dev)), o].all()
    lab = sr.label_index(dev.correct, dev.mask)
    assert (o[lab >= 0] == lab[lab >= 0]).all()
    ref = {"accuracy": 0.90, "gpu_seconds": 10.0}
    assert sr.keep_rule({"accuracy": 0.895, "gpu_seconds": 3.0}, ref).startswith("keep (within")
    assert sr.keep_rule({"accuracy": 0.92, "gpu_seconds": 30.0}, ref).startswith("keep (more")
    assert sr.keep_rule({"accuracy": 0.88, "gpu_seconds": 1.0}, ref) == "drop"
    cands = [{"params": {"tau": t}, "accuracy": a, "gpu_seconds": g}
             for t, a, g in [(0.1, 0.85, 2.0), (0.5, 0.897, 4.0), (0.7, 0.899, 6.0), (0.9, 0.90, 9.0)]]
    assert sr.choose(cands, ref, "rule", 0.005)["params"]["tau"] == 0.5   # cheapest within 0.5 point
    assert sr.choose(cands, ref, "accuracy", 0.005)["params"]["tau"] == 0.9


def test_lr_and_knn_never_pick_masked_routes(tmp_path):
    labels, items = make_labels(tmp_path)
    sp = sr.load(labels, items, ["train", "dev"])[0]
    tr, dev = sp["train"], sp["dev"]
    feat = lambda s: np.array([[1.0, 0.0] if t.startswith("alpha") else [0.0, 1.0] for t in s.texts])
    xt, xd = feat(tr), feat(dev)
    p = sr.LRRouter(1.0).fit(xt, tr).proba(xd, 3)
    for tau in (0.0, 0.5, 0.9, 1.01):
        pk = sr.cheapest_above(p, dev.mask, tau)
        assert dev.mask[np.arange(len(dev)), pk].all()
    pk = sr.cheapest_above(sr.knn_proba(xd, xt, tr, 5), dev.mask, 0.6)
    assert dev.mask[np.arange(len(dev)), pk].all()
    mem = np.array([t.startswith("alpha") for t in dev.texts])
    assert (pk[mem] == 0).all() and (pk[~mem] == 2).all()          # memory where it exists, else deep (fast is never right on b*)


def test_knn_none_neighbour_and_missing_route_prior():
    train = types.SimpleNamespace(correct=np.array([[0, 0], [1, 1], [0, 1]], float),
                                  mask=np.array([[1, 1], [0, 1], [0, 1]], bool), routes=["m", "d"])
    x, xt = np.array([[1.0, 0.0]]), np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]])
    p = sr.knn_proba(x, xt, train, 1)                               # neighbour 0 is a "none" item: zeros
    assert p.tolist() == [[0.0, 0.0]]
    p = sr.knn_proba(np.array([[0.0, 1.0]]), xt, train, 1)          # neighbour lacks route m -> m's train accuracy
    assert p[0, 0] == pytest.approx(0.0) and p[0, 1] == 1.0


def test_train_and_evaluate_cheap_routers_end_to_end(tmp_path, monkeypatch):
    labels, items = make_labels(tmp_path)
    monkeypatch.setattr(sr, "embed", lambda texts, device=None: np.array(
        [[1.0, 0.0] if t.startswith("alpha") else [0.0, 1.0] for t in texts], np.float32))
    out = tmp_path / "out"
    sr.main(["train", "--labels", labels, "--items", *items, "--out", str(out), "--routers", "bge_lr", "knn"])
    for name in ("bge_lr", "knn"):
        meta = json.loads((out / name / "meta.json").read_text())
        assert meta["seed"] == sr.SEED and meta["routes"] == ["memory", "fast", "deep"] and not meta["dry_run"]
        assert "tau" in meta["params"] and meta["label_hashes"]["split.json"]
    res = json.loads((out / "table_dev.json").read_text())
    assert set(res["results"]) >= {"bge_lr", "knn", "fixed:fast", "fixed:deep", "oracle"}
    assert "fixed:memory" not in res["results"]                     # not available everywhere: no fixed row
    assert res["results"]["knn"]["gpu_seconds"] < res["results"]["fixed:deep"]["gpu_seconds"]
    md = (out / "table_dev.md").read_text()
    assert "deep (best fixed)" in md and "keep_rule" in md
    assert (out / "table_dev_by_source.csv").exists()
    assert not (out / "table_held_out.md").exists()


def test_per_item_costs_pick_the_cheaper_route_on_each_row():
    """2026-11-21: 'cheapest' is per item when the labels carry per-row gpu_seconds. Columns are the global order
    (fast cheapest on average, then deep, then memory); row 0 is LongMemEval-like (full-history fast costs 300 GPU-s,
    memory 40), row 1 is pool-like (fast 2, memory unavailable)."""
    correct = np.array([[1, 1, 1], [1, 1, 0]], float)
    mask = np.array([[1, 1, 1], [1, 1, 0]], bool)
    cost = np.array([[300.0, 900.0, 40.0], [2.0, 10.0, np.inf]])
    assert sr.label_index(correct, mask).tolist() == [0, 0]                 # global order: fast everywhere
    assert sr.label_index(correct, mask, cost).tolist() == [2, 0]           # per row: memory on the LongMemEval row
    p = np.array([[0.9, 0.9, 0.7], [0.8, 0.9, 0.0]])
    assert sr.cheapest_above(p, mask, 0.6, cost).tolist() == [2, 0]
    assert sr.cheapest_above(p, mask, 0.85, cost).tolist() == [0, 1]       # memory below tau: fast is the cheaper left
    assert sr.masked_argmax(p, mask, cost).tolist() == [0, 1]               # row 0: fast and deep tie at 0.9 -> fast (300 < 900)
    tie = np.array([[5.0, 5.0, 5.0], [5.0, 5.0, np.inf]])
    assert sr.label_index(correct, mask, tie).tolist() == [0, 0]            # equal costs: the global order


def test_load_reads_row_costs_and_task_text(tmp_path):
    labels, items = make_labels(tmp_path)
    d = tmp_path / "graded"
    rows = [json.loads(l) for l in open(d / "per_question.jsonl") if not l.startswith('{"id": "h_broken"')]
    for r in rows:  # merged labels: every available route has its own gpu_seconds; LongMemEval-like rows carry their question
        for k in ("fast", "deep", "memory"):
            if k in r:
                r[k]["gpu_seconds"] = {"fast": 300.0, "deep": 900.0, "memory": 40.0}[k] if r["id"].startswith("a") else \
                    {"fast": 2.0, "deep": 10.0}[k]
        if r["id"].startswith("a"):
            r["task"] = "Current date: 2023/05/01\nQuestion: where did I park?"
    with open(d / "per_question.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    sp, info = sr.load(labels, items, ["train", "dev"])
    tr = sp["train"]
    a, b = tr.ids.index("a004"), tr.ids.index("b005")
    assert tr.texts[a].endswith("where did I park?") and tr.texts[b].startswith("beta")
    m, f_, dp = (info["routes"].index(x) for x in ("memory", "fast", "deep"))
    assert tr.cost[a, m] == 40.0 and tr.cost[a, f_] == 300.0 and np.isinf(tr.cost[b, m])
    lab = sr.label_index(tr.correct, tr.mask, tr.cost)
    assert lab[a] == m and lab[b] == dp                                     # b005: fast wrong (odd item), deep right
    assert sr.oracle_picks(tr)[a] == m
