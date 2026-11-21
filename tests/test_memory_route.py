"""Memory routes (flotilla/memory_route.py): availability, GRAFT documents, cache keys, the memory block, the judge,
and an end-to-end check with a fake Qwen and GRAFT's fake gateway on toy histories (skipped when GRAFT or its
environment is missing; set GRAFT_REPO / GRAFT_PYTHON)."""
import asyncio
import json
import os
from pathlib import Path

import pytest

from flotilla import memory_route as mr
from flotilla import system
from flotilla.trace import Trace

KU = mr.SAMPLE_ITEMS[0]  # sessions given out of date order; France (May) is replaced by Canada (September)
POOL = mr.POOL_SAMPLE


# ------------------------------------------------------------------ unit

def test_availability_is_explicit_per_item():
    assert mr.has_memory(KU) and not mr.has_memory(POOL) and not mr.has_memory({**KU, "sessions": []})
    assert mr.available_routes(POOL) == list(mr.BASE_ROUTES)
    assert set(mr.available_routes(KU)) == set(mr.BASE_ROUTES) | set(mr.MEMORY_ROUTES)
    rec = mr.unavailable_record(POOL, "memory")
    assert rec["available"] is False and rec["base_route"] == "fast"
    with pytest.raises(mr.MemoryUnavailable):
        mr.with_memory(POOL, None)
    cfg = mr.load_config("memory")
    tr = Trace(run_id="t", protocol_version="p", prompt_versions={}, benchmark="b", item_id=POOL["item_id"], split="t")
    with pytest.raises(mr.MemoryUnavailable):
        asyncio.run(mr.memory(POOL, None, cfg, tr))


def test_normalize_item_hides_the_answer():
    it = mr.normalize_item({**KU, "meta": {"has_answer_turns": {"s3": [0]}}})
    assert "meta" not in it and it["task_type"] == "memory" and it["scorer"] == "lme_judge" and it["bench"] == "longmemeval_s"
    assert "answer" not in it and "answer_session_ids" not in it and it["gold"] is None
    assert it["task"].startswith("Current date: 2023/10/01") and KU["question"] in it["task"]
    assert mr.normalize_item(it) is it and mr.normalize_item(POOL) is POOL


def test_sessions_become_dated_chunks_in_date_order():
    chunks, cmap = mr.sessions_to_chunks(KU)
    assert [c["session_id"] for c in cmap] == ["s1", "s2", "s3"]
    assert all(c.startswith(f"[Chat session {m['session_id']}, date {m['date']}") for c, m in zip(chunks, cmap))
    long = {"sessions": [{"session_id": "x", "date": "2024/01/02 (Tue) 10:00",
                          "turns": [{"role": "user", "content": "word " * 300}] * 6}]}
    chunks, cmap = mr.sessions_to_chunks(long, chunk_tokens=400)
    assert len(chunks) > 1 and all(len(c) <= 400 * 4 + 80 for c in chunks)
    assert all("date 2024/01/02" in c and f"part {i + 1} of {len(chunks)}" in c for i, c in enumerate(chunks))


def test_graph_key_covers_history_and_build_settings_only(tmp_path):
    repo = mr.graft_repo()
    g = mr.graft_config({})
    k = mr.build_key(KU, g, "local:qwen", repo)
    assert k == mr.build_key(json.loads(json.dumps(KU)), g, "local:qwen", repo)
    assert k != mr.build_key({**KU, "sessions": KU["sessions"][:2]}, g, "local:qwen", repo)
    assert k != mr.build_key(KU, {**g, "writer_max_tokens": 4096}, "local:qwen", repo)
    assert k != mr.build_key(KU, g, "fake", repo)                       # fake graphs never serve real runs
    assert k == mr.build_key(KU, {**g, "max_facts": 20}, "local:qwen", repo)  # retrieval settings: same graph
    assert mr.retrieval_key(KU, k, g) != mr.retrieval_key(KU, k, {**g, "max_facts": 20})


def test_graft_config_is_a_named_preset(monkeypatch):
    plain = mr.graft_config({})
    assert plain["preset"] == "plain_c" and plain["retrieval"] == "ppr_goat_ppr" and plain["max_facts"] == 50
    assert plain["explainer"] == "goat" and plain["start_graph"] == "empty" and "trex_guide" not in plain
    guided = mr.graft_config({"graft_preset": "guide_b"})
    assert guided["guide_linking"] and guided["guide_planning"] and guided["trex_guide"].endswith("trex_guide.json")
    assert mr.graft_config({"graft_preset": "guide_b", "graft": {"max_facts": 30}})["max_facts"] == 30
    monkeypatch.setenv("FLOTILLA_GRAFT_PRESET", "guide_b")
    assert mr.graft_config({"graft_preset": "plain_c"})["preset"] == "guide_b"
    monkeypatch.setenv("FLOTILLA_GRAFT_PRESET", "nope")
    with pytest.raises(ValueError):
        mr.graft_config({})
    for route in mr.MEMORY_ROUTES:  # every Memory config names its base route and the default preset
        mem = json.loads(mr.ROUTE_CONFIG[route].read_text())["extra"]["memory"]
        assert mem["base_route"] == mr.MEMORY_ROUTES[route] and mem["graft_preset"] == "plain_c"
        base = json.loads(mr.ROUTE_CONFIG[mr.MEMORY_ROUTES[route]].read_text())
        conf = json.loads(mr.ROUTE_CONFIG[route].read_text())
        assert {k: conf[k] for k in base if k not in ("name", "notes")} == {k: base[k] for k in base if k not in ("name", "notes")}


def test_memory_block_is_labelled_and_dated():
    mem = {"chunk_map": [{"date": "2023/05/01"}, {"date": "2023/09/02"}],
           "retrieval": {"facts": [{"id": "f:1", "subject": "Alice", "relation": "lives in", "object": "Oslo",
                                    "span": "I moved to Oslo.", "chunk_id": 1, "outdated": False}]}}
    text = mr.memory_task(KU, mem)
    assert text.startswith(mr.MEMORY_HEADER) and "END OF MEMORY" in text
    assert '[M1] 2023/09/02 | Alice | lives in | Oslo | "I moved to Oslo."' in text
    assert text.index("END OF MEMORY") < text.index("Question: ") and text.endswith(mr.MEMORY_RULE)
    assert "(no facts were recalled)" in mr.memory_block({"chunk_map": [], "retrieval": {"facts": []}})


def test_judge_prompts_follow_longmemeval():
    p = mr.judge_prompt("multi-session", "Q?", "A", "resp")
    assert p.startswith("I will give you a question, a correct answer") and p.endswith("Answer yes or no only.")
    assert "Question: Q?\n\nCorrect Answer: A\n\nModel Response: resp" in p
    assert "off-by-one" in mr.judge_prompt("temporal-reasoning", "Q", "A", "r")
    assert "updated answer" in mr.judge_prompt("knowledge-update", "Q", "A", "r")
    assert "Rubric: A" in mr.judge_prompt("single-session-preference", "Q", "A", "r")
    assert "unanswerable" in mr.judge_prompt("multi-session", "Q", "A", "r", abstention=True)
    with pytest.raises(NotImplementedError):
        mr.judge_prompt("made-up", "Q", "A", "r")
    assert mr.is_abstention({"item_id": "lme-x_abs"}) and mr.is_abstention({"item_id": "x", "abstention": True})
    assert mr.parse_judge("Yes.") and not mr.parse_judge("No") and not mr.parse_judge(None)


def test_judge_answer_with_fake_qwen(monkeypatch):
    fake = mr.FakeQwen()
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    srv = {"url": "fake", "model": "qwen-fake"}
    assert asyncio.run(mr.judge_answer(KU, "It is Canada.", srv))["correct"] is True
    assert asyncio.run(mr.judge_answer(KU, "France", srv))["correct"] is False
    assert asyncio.run(mr.judge_answer(KU, None, srv))["judge_reply"] is None  # no call without an answer
    req = fake.seen[0]
    assert req["kwargs"]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert len(fake.seen) == 2 and req["messages"][0]["role"] == "user"


def test_grade_refuses_memory_items():
    from flotilla.label_loop import grade
    with pytest.raises(ValueError):
        grade({"task_type": "memory"}, "x")


def test_strategy_labels_with_memory_routes(tmp_path, monkeypatch):
    """Pool items have no Memory traces (unavailable, not wrong); LME items are graded by judge verdicts;
    the GRAFT build is counted once per history."""
    from flotilla import strategy_labels
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps({"id": "p1", "source": "gsm8k", "task_type": "science_mc", "gold": "B", "task": "q"}) + "\n")
    lme = tmp_path / "lme.jsonl"
    lme.write_text(json.dumps(KU) + "\n")
    build = {"llm_calls": 100, "input_tokens": 150000, "output_tokens": 20000, "llm_seconds": 300, "wall_seconds": 310}

    def trace(i, ans, mem=False):
        return {"item_id": i, "final_answer": ans, "calls": 1, "wall_seconds": 1.0,
                "models": [{"samples": [{"tokens_out": 5}]}], **({"retrieval": {"graft_build": build}} if mem else {})}
    runs, verdicts = [], []
    for s in strategy_labels.ORDER:
        d = tmp_path / s
        d.mkdir()
        rows = [] if s in strategy_labels.MEMORY_ROUTES else [trace("p1", "B" if s == "deep" else "A")]
        rows.append(trace(KU["item_id"], "Canada" if s == "memory_deep" else "France", s in strategy_labels.MEMORY_ROUTES))
        verdicts.append({"item_id": KU["item_id"], "route": s, "correct": s == "memory_deep"})
        (d / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        runs.append(f"{s}={d}")
    vpath = tmp_path / "verdicts.jsonl"
    vpath.write_text("".join(json.dumps(v) + "\n" for v in verdicts))
    out = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["x", "--pool", str(pool), "--runs", *runs, "--out", str(out), "--memory-items",
                                     str(lme), "--verdicts", str(vpath), "--workers", "1"])
    strategy_labels.main()
    rows = {r["id"]: r for r in map(json.loads, open(out / "per_question.jsonl"))}
    assert rows["p1"]["label"] == "deep" and rows["p1"]["memory"] == {"available": False}
    assert rows[KU["item_id"]]["label"] == "memory_deep" and rows[KU["item_id"]]["graft_build"]["llm_calls"] == 100
    s = json.loads((out / "summary.json").read_text())
    assert s["per_strategy"]["memory"]["questions_available"] == 1 and s["per_strategy"]["fast"]["questions_available"] == 2
    assert s["graft_build"]["histories"] == 1 and s["graft_build"]["llm_calls"] == 100  # once, not four times


# ------------------------------------------------------------------ end to end: fake Qwen + GRAFT's fake gateway

REPO = mr.graft_repo()
HAVE_GRAFT = (REPO / "my_method" / "agent.py").exists() and Path(mr.graft_python(REPO)).exists() and \
    (REPO / mr.FAKE_GRAFT["gnn_checkpoint"]).exists()


@pytest.mark.skipif(not HAVE_GRAFT, reason="GRAFT repo, its venv or its offline GNN checkpoint not found")
def test_four_routes_share_one_graph_and_see_the_memory(tmp_path, monkeypatch):
    fake = mr.FakeQwen()
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    bridge_calls = []
    real_bridge = mr.run_bridge
    monkeypatch.setattr(mr, "run_bridge", lambda spec, repo: (bridge_calls.append(len(spec["jobs"])), real_bridge(spec, repo))[1])
    llm = {"mode": "fake", "model": "qwen-fake", "label": "fake"}
    items = [KU, mr.SAMPLE_ITEMS[1], POOL]
    cache = tmp_path / "cache"
    records = {}
    for route in mr.MEMORY_ROUTES:  # each route prepares on its own, as four separate route runs would
        cfg = mr.load_config(route)
        mem_conf = cfg.extra["memory"]
        prepared = mr.prepare(items, mem_conf, llm, cache)
        assert POOL["item_id"] not in prepared                      # no history: never sent to GRAFT
        for it in items[:2]:
            it = mr.normalize_item(it)
            n_before = len(fake.seen)
            tr = Trace(run_id="t", protocol_version="p", prompt_versions={}, benchmark=it["bench"], item_id=it["item_id"], split="t")
            asyncio.run(mr.ROUTE_FUNCS[route](it, prepared[it["item_id"]], cfg, tr))
            d = tr.finish()
            records[(route, it["item_id"])] = d
            prompts = [r["messages"][-1]["content"] for r in fake.seen[n_before:]]
            assert prompts and all(p.startswith(mr.MEMORY_HEADER) and "END OF MEMORY" in p for p in prompts)
            assert len(prompts) == (5 if route == "vote_memory" else 1)
    assert bridge_calls == [2]  # GRAFT ran once (two histories); the other three routes read the cache
    graphs = sorted((cache / "graphs").glob("*.json"))
    assert len([g for g in graphs if not g.name.endswith(".build.json")]) == 2
    ku = {r: records[(r, KU["item_id"])] for r in mr.MEMORY_ROUTES}
    assert len({d["retrieval"]["graph_key"] for d in ku.values()}) == 1
    assert ku["memory"]["retrieval"]["graft_build"]["built_in_this_run"] is True
    assert all(ku[r]["retrieval"]["graft_build"]["cache_hit"] for r in ("memory_deep", "vote_memory", "deep_tools_memory"))
    assert all(d["final_answer"] == "Canada" for d in ku.values())  # the newer session's fact won
    # build cost is logged apart from answering: the trace's model tokens do not include it
    b = ku["memory"]["retrieval"]["graft_build"]
    assert b["llm_calls"] >= 3 and b["input_tokens"] > 0 and b["wall_seconds"] is not None
    assert ku["memory"]["tokens_total"] == sum(s["tokens_in"] + s["tokens_out"] for m in ku["memory"]["models"] for s in m["samples"])
    assert all(d["retrieval"]["graft_build"]["llm_calls"] == b["llm_calls"] for d in ku.values())
    rec = mr.label_record("vote_memory", ku["vote_memory"], True)
    assert rec["samples"] == 5 and rec["memory"]["facts"] >= 1 and rec["graft_build"]["llm_calls"] == b["llm_calls"]


@pytest.mark.skipif(not HAVE_GRAFT, reason="GRAFT repo, its venv or its offline GNN checkpoint not found")
def test_smalltest_run_with_a_memory_config(tmp_path, monkeypatch):
    """The path real label runs take (serve -> smalltest.run): pool items skipped, LME items answered with memory,
    build logged in graft_prepare.json apart from the traces."""
    import argparse
    from flotilla import smalltest
    fake = mr.FakeQwen()
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    monkeypatch.setenv("FLOTILLA_GRAFT_LLM", "fake")
    monkeypatch.setenv("FLOTILLA_GRAFT_CACHE", str(tmp_path / "cache"))
    items = tmp_path / "items"
    items.mkdir()
    (items / "mixed.jsonl").write_text("".join(json.dumps(x) + "\n" for x in [*mr.SAMPLE_ITEMS[:2], POOL]))
    out = tmp_path / "run"
    args = argparse.Namespace(config=str(mr.ROUTE_CONFIG["memory_deep"]), items_dir=str(items), out=str(out),
                              benches=None, ids=None, rpm=0, max_calls=10**9, concurrency=4)
    asyncio.run(smalltest.run(args))
    rows = [json.loads(l) for l in open(out / "trace.jsonl")]
    assert sorted(r["item_id"] for r in rows) == sorted(x["item_id"] for x in mr.SAMPLE_ITEMS[:2])
    assert all(r["retrieval"]["source"] == "graft" and r["router"]["route"] == "deep+memory" for r in rows)
    assert {r["item_id"]: r["final_answer"] for r in rows} == {"lme-toy-ku": "Canada", "lme-toy-ssu": "Carla Diaz"}
    assert all("answer" not in json.dumps(r["router"]) for r in rows)
    prep = json.loads((out / "graft_prepare.json").read_text())
    assert prep["skipped_no_history"] == 1 and prep["built"] == 2 and prep["build_llm_calls"] > 0
