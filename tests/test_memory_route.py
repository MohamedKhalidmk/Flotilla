"""Memory routes (flotilla/memory_route.py): availability, GRAFT documents, cache keys, the memory block, the judge,
and an end-to-end check with a fake Qwen and GRAFT's fake gateway on toy histories (skipped when GRAFT or its
environment is missing; set GRAFT_REPO / GRAFT_PYTHON)."""
import asyncio
import json
import re
import os
from pathlib import Path

import pytest

from flotilla import memory_route as mr
from flotilla import system
from flotilla.trace import Trace

@pytest.fixture(autouse=True)
def _offline_preset(monkeypatch, request):
    """The route configs use guide_b (GRAFT's default since test 06); its T-REx guide file lives on the clusters, so
    offline tests build with plain_c unless a test checks presets itself."""
    if request.node.name != "test_graft_config_is_a_named_preset":
        monkeypatch.setenv("FLOTILLA_GRAFT_PRESET", "plain_c")


KU = mr.SAMPLE_ITEMS[0]  # sessions given out of date order; France (May) is replaced by Canada (September)
POOL = mr.POOL_SAMPLE


# ------------------------------------------------------------------ unit

def test_availability_is_explicit_per_item():
    """Checks that Memory routes are offered only on items with sessions, and that memory on a pool item raises MemoryUnavailable.
    Guards against: a Memory route silently running on a question with no history instead of being marked unavailable."""
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
    """Checks that normalize_item turns a LongMemEval item into a memory task with the lme_judge scorer and removes the answer, answer sessions and meta.
    Guards against: the gold answer or the answer-session IDs leaking into what the model or router sees."""
    it = mr.normalize_item({**KU, "meta": {"has_answer_turns": {"s3": [0]}}})
    assert "meta" not in it and it["task_type"] == "memory" and it["scorer"] == "lme_judge" and it["bench"] == "longmemeval_s"
    assert "answer" not in it and "answer_session_ids" not in it and it["gold"] is None
    assert it["task"].startswith("Current date: 2023/10/01") and KU["question"] in it["task"]
    assert mr.normalize_item(it) is it and mr.normalize_item(POOL) is POOL


def test_sessions_become_dated_chunks_in_date_order():
    """Checks that sessions become dated chunks in date order, and that a long session is cut into numbered parts within the size limit.
    Guards against: chunks out of date order, or the later parts of a long session losing their date."""
    chunks, cmap = mr.sessions_to_chunks(KU)
    assert [c["session_id"] for c in cmap] == ["s1", "s2", "s3"]
    assert all(c.startswith(f"[Chat session {m['session_id']}, date {m['date']}") for c, m in zip(chunks, cmap))
    long = {"sessions": [{"session_id": "x", "date": "2024/01/02 (Tue) 10:00",
                          "turns": [{"role": "user", "content": "word " * 300}] * 6}]}
    chunks, cmap = mr.sessions_to_chunks(long, chunk_tokens=400)
    assert len(chunks) > 1 and all(len(c) <= 400 * 4 + 80 for c in chunks)
    assert all("date 2024/01/02" in c and f"part {i + 1} of {len(chunks)}" in c for i, c in enumerate(chunks))


def test_graph_key_covers_history_and_build_settings_only(tmp_path):
    """Checks that the graph key changes with the history, build settings and LLM label, but not with retrieval settings like max_facts.
    Guards against: a graph built by the fake LLM or from another history being reused for a real run."""
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
    """Checks that GRAFT settings come from named presets with unique G IDs, the env variable overrides them, and Memory configs match their base.
    Guards against: a Memory route changing GRAFT's method outside a named preset, or an unknown preset name being accepted."""
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
    monkeypatch.delenv("FLOTILLA_GRAFT_PRESET")
    # every preset is one GRAFT candidate: a G ID each, no ID twice (a winning GRAFT change is added as a new preset
    # with its G ID before any Memory route uses it; user, 2026-11-22)
    assert set(mr.GRAFT_PRESET_IDS) == set(mr.GRAFT_PRESETS)
    ids = list(mr.GRAFT_PRESET_IDS.values())
    assert all(re.fullmatch(r"G\d+", g) for g in ids) and len(ids) == len(set(ids))
    assert mr.GRAFT_PRESET_IDS["plain_c"] == "G08" and mr.GRAFT_PRESET_IDS["guide_b"] == "G35"
    for route in mr.MEMORY_ROUTES:  # every Memory config names its base route and the guide preset (GRAFT's default)
        mem = json.loads(mr.ROUTE_CONFIG[route].read_text())["extra"]["memory"]
        assert mem["base_route"] == mr.MEMORY_ROUTES[route] and mem["graft_preset"] == "guide_b"
        # the method comes only from the preset: a route may override where GRAFT's LLM runs, nothing else
        assert set(mem.get("graft") or {}) <= mr.MEMORY_RUNTIME_KEYS, (route, mem.get("graft"))
        base = json.loads(mr.ROUTE_CONFIG[mr.MEMORY_ROUTES[route]].read_text())
        conf = json.loads(mr.ROUTE_CONFIG[route].read_text())
        assert {k: conf[k] for k in base if k not in ("name", "notes")} == {k: base[k] for k in base if k not in ("name", "notes")}


def test_memory_block_is_labelled_and_dated():
    """Checks that the memory block has its header, dates each fact, ends before the question, and says when no facts were recalled.
    Guards against: recalled facts shown without dates, or the memory block placed after the question."""
    mem = {"chunk_map": [{"date": "2023/05/01"}, {"date": "2023/09/02"}],
           "retrieval": {"facts": [{"id": "f:1", "subject": "Alice", "relation": "lives in", "object": "Oslo",
                                    "span": "I moved to Oslo.", "chunk_id": 1, "outdated": False}]}}
    text = mr.memory_task(KU, mem)
    assert text.startswith(mr.MEMORY_HEADER) and "END OF MEMORY" in text
    assert '[M1] 2023/09/02 | Alice | lives in | Oslo | "I moved to Oslo."' in text
    assert text.index("END OF MEMORY") < text.index("Question: ") and text.endswith(mr.MEMORY_RULE)
    assert "(no facts were recalled)" in mr.memory_block({"chunk_map": [], "retrieval": {"facts": []}})


def test_judge_prompts_follow_longmemeval():
    """Checks that judge prompts use LongMemEval's wording for each question type and for abstention, reject unknown types, and that yes or no replies parse.
    Guards against: memory answers judged with a prompt that differs from LongMemEval's, so scores cannot be compared with the paper."""
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
    """Checks that judge_answer marks Canada right and France wrong with thinking off, and makes no judge call when there is no answer.
    Guards against: the judge running with thinking on, or spending a call on a missing answer."""
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
    """Checks that the label grader raises an error when given a memory item.
    Guards against: memory answers silently counted wrong by the label grader instead of being sent to LongMemEval's judge."""
    from flotilla.label_loop import grade
    with pytest.raises(ValueError):
        grade({"task_type": "memory"}, "x")


def test_strategy_labels_with_memory_routes(tmp_path, monkeypatch):
    """Checks that strategy labels mark pool items unavailable on Memory routes, grade LongMemEval items from judge verdicts, and count each GRAFT build once.
    Guards against: the GRAFT build cost for one history being counted four times, once per Memory route.

    Pool items have no Memory traces (unavailable, not wrong); LME items are graded by judge verdicts;
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
    """Checks that the four Memory routes share one cached graph per history, see the memory in every prompt, and log build cost apart.
    Guards against: each Memory route rebuilding the same graph, or build tokens being added to the answer's token count."""
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
    """Checks that smalltest.run with a Memory config skips pool items, answers LongMemEval items with memory, and logs the GRAFT build in graft_prepare.json.
    Guards against: real label runs sending pool items to GRAFT or putting the answer into the router record.

    The path real label runs take (serve -> smalltest.run): pool items skipped, LME items answered with memory,
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


def test_cheapest_label_uses_the_rows_own_costs():
    """Checks that cheapest_label picks the right route with the lowest GPU-seconds on that row, uses route order on ties, and gives none if all fail.
    Guards against: a LongMemEval row labelled fast when memory was right and cheaper on that row."""
    from flotilla.strategy_labels import cheapest_label
    lme = {"fast": {"available": True, "correct": True, "gpu_seconds": 300.0},
           "deep": {"available": True, "correct": True, "gpu_seconds": 900.0},
           "memory": {"available": True, "correct": True, "gpu_seconds": 40.0},
           "vote_memory": {"available": True, "correct": False, "gpu_seconds": 10.0}}
    assert cheapest_label(lme) == "memory"                                  # cheaper than Fast on this row; wrong routes ignored
    pool = {"fast": {"available": True, "correct": True, "gpu_seconds": 2.0},
            "deep": {"available": True, "correct": True, "gpu_seconds": 7.0}, "memory": {"available": False}}
    assert cheapest_label(pool) == "fast"
    tie = {"tools": {"available": True, "correct": True, "gpu_seconds": 5.0},
           "fast": {"available": True, "correct": True, "gpu_seconds": 5.0}}
    assert cheapest_label(tie) == "fast"                                    # equal costs: ORDER
    no_cost = {"deep": {"available": True, "correct": True}, "memory": {"available": True, "correct": True}}
    assert cheapest_label(no_cost) == "deep"                                # rows without costs: ORDER
    assert cheapest_label({"fast": {"available": True, "correct": False}}) == "none"


def test_haiku_judge_logs_every_call_with_ids_and_cost(tmp_path):
    """Checks that the Haiku judge sends LongMemEval's prompt with thinking off and max_tokens 10, and logs each call's IDs, hash and cost.
    Guards against: a judge call with no usage log row, or a paid call made when there is no answer.

    protocol-v10 addendum: Haiku judges with LongMemEval's prompt, thinking off, max_tokens 10, no sampling
    parameters; each call is logged with cost, request hash, message ID, request ID and reply hash."""
    from types import SimpleNamespace as NS
    sent = []

    class Raw:
        headers = {"request-id": "req_123"}

        async def parse(self):  # as the real AsyncAnthropic raw response: a coroutine (job 5119538 failed on it)
            return NS(content=[NS(type="text", text="Yes.")], id="msg_1", stop_reason="end_turn",
                      usage=NS(input_tokens=300, output_tokens=2, cache_read_input_tokens=0, cache_creation_input_tokens=0))

    async def create(**params):
        sent.append(params)
        return Raw()

    client = NS(messages=NS(with_raw_response=NS(create=create)))
    j = mr.HaikuJudge(tmp_path / "usage.jsonl", client=client)
    v = asyncio.run(mr.judge_answer_haiku(KU, "She is Canadian now.", j, "fast"))
    assert v["correct"] and v["judge_model"] == "claude-haiku-5-5" and v["judge_reply"] == "Yes."
    p = sent[0]
    assert p["max_tokens"] == 10 and p["thinking"] == {"type": "disabled"} and p["model"] == "claude-haiku-5-5"
    assert not {"temperature", "top_p", "top_k"} & set(p)
    assert p["messages"][0]["content"].startswith("I will give you a question, a correct answer")
    row = json.loads((tmp_path / "usage.jsonl").read_text())
    assert row["request_id"] == "req_123" and row["message_id"] == "msg_1" and row["route"] == "fast"
    assert row["cost_usd"] == pytest.approx((300 * 0.10 + 2 * 0.50) / 1e6) and len(row["request_hash"]) == 16
    none = asyncio.run(mr.judge_answer_haiku(KU, None, j))
    assert none["correct"] is False and len(sent) == 1        # no answer: no call, no cost


def test_merge_keeps_legacy_pool_rows_available(tmp_path):
    """Checks that merging old pool labels treats a route with a verdict as available, keeps the labels, and adds per-row GPU-seconds.
    Guards against: every run-03 pool row being labelled none because it lacks the available field.

    run-03's pool rows predate the "available" field: the merge must treat a route with a verdict as available, so
    pool rows keep their labels and get per-row GPU-seconds (the first run-04-lme merge labelled all 1,450 "none")."""
    from types import SimpleNamespace as NS
    from flotilla import strategy_labels as sl
    pdir = tmp_path / "run-03"
    pdir.mkdir()
    legacy = {"id": "p1", "source": "gsm8k", "task_type": "math", "label": "fast",
              "fast": {"correct": True, "wall_seconds": 10.0, "tokens_out": 5},
              "vote": {"correct": True, "wall_seconds": 40.0, "tokens_out": 50}}
    wrong = {"id": "p2", "source": "gsm8k", "task_type": "math", "label": "none",
             "fast": {"correct": False, "wall_seconds": 10.0}, "vote": {"correct": False, "wall_seconds": 40.0}}
    (pdir / "per_question.jsonl").write_text(json.dumps(legacy) + "\n" + json.dumps(wrong) + "\n")
    per = {"fast": {"questions_available": 2, "mean_wall_seconds": 10.0, "gpu_seconds_job": 20.0, "accuracy": 0.5},
           "vote": {"questions_available": 2, "mean_wall_seconds": 40.0, "gpu_seconds_job": 160.0, "accuracy": 0.5}}
    (pdir / "summary.json").write_text(json.dumps({"questions": 2, "labels": {"fast": 1, "none": 1}, "per_strategy": per}))
    (pdir / "split.json").write_text(json.dumps({"seed": 1, "train": ["p1"], "dev": ["p2"], "held_out": []}))
    msplit = tmp_path / "msplit.json"
    msplit.write_text(json.dumps({"train": ["m1"], "dev": [], "held_out": []}))
    lme = [{"id": "m1", "task_type": "memory", "label": "memory",
            "fast": {"available": True, "correct": False, "wall_seconds": 10.0},
            "memory": {"available": True, "correct": True, "wall_seconds": 5.0}}]
    lsum = {"questions": 1, "labels": {"memory": 1}, "per_strategy": {
        "fast": {"questions_available": 1, "mean_wall_seconds": 10.0, "gpu_seconds_job": 10.0},
        "memory": {"questions_available": 1, "mean_wall_seconds": 5.0, "gpu_seconds_job": 5.0}}}
    out = tmp_path / "run-04"
    out.mkdir()
    a = NS(pool_labels=str(pdir), memory_split=str(msplit), build_runs=[], graft_cache=None)
    s = sl.merge_pool_labels(a, out, lme, lsum, {})
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(out / "per_question.jsonl")}
    assert rows["p1"]["label"] == "fast" and rows["p2"]["label"] == "none" and rows["m1"]["label"] == "memory"
    assert rows["p1"]["fast"]["available"] and rows["p1"]["fast"]["gpu_seconds"] == 10.0
    assert rows["p1"]["memory"] == {"available": False}
    assert s["labels"] == {"fast": 1, "none": 1, "memory": 1} and s["best_any_strategy"] == round(2 / 3, 4)
    assert s["per_strategy"]["fast"]["questions"] == 3 and s["per_strategy"]["memory"]["questions"] == 1


def test_writer_v2_and_thinking_change_the_graph_key():
    """Checks that the writer prompt and LLM thinking change the graph build key, while user_node and log_writer_replies do not.
    Guards against: a G41 or G42 run reusing a G35 graph built with another writer prompt or without thinking.

    G41/G42 graphs never reuse G35's: the writer prompt is a build key, thinking is in the LLM label."""
    srv = {"s": {"url": "http://x/v1", "model": "qwen_w4a16"}}
    plain = mr.llm_for({"graft": {"llm_mode": "local"}}, srv, ["s"])
    think = mr.llm_for({"graft": {"llm_mode": "local", "llm_thinking": True}}, srv, ["s"])
    assert not plain["thinking"] and think["thinking"] and think["label"] == "local:qwen_w4a16:thinking"
    it = {"item_id": "x", "sessions": [{"session_id": "a", "date": "2023/05/20", "turns": []}]}
    repo = mr.graft_repo()
    base = mr.graft_config({"graft_preset": "guide_b"})
    v2 = mr.graft_config({"graft_preset": "guide_b", "graft": {"writer_prompt": "chat_v2"}})
    k0 = mr.build_key(it, base, plain["label"], repo)
    assert k0 != mr.build_key(it, v2, plain["label"], repo) and k0 != mr.build_key(it, base, think["label"], repo)
    assert k0 == mr.build_key(it, {**base, "user_node": True, "log_writer_replies": True}, plain["label"], repo)


def test_ask_for_more_adds_pool_facts_within_the_limits(monkeypatch):
    """Checks that with ask_more on, a NEED MORE MEMORIES reply adds the next pool batch and asks again, up to the ask limit.
    Guards against: G40 on LongMemEval silently answering with only the first facts, or asking forever past the limits."""
    from types import SimpleNamespace as NS
    from flotilla import system
    facts = [{"id": f"f:{i}", "subject": "user", "relation": "r", "object": f"o{i}", "chunk_id": 0} for i in range(12)]
    mem = {"chunk_map": [{"date": "2023/05/01"}], "retrieval": {"facts": facts[:2], "pool": facts[2:]}}
    shown = []

    async def answer(run_item, rt, cfg, trace):
        shown.append(run_item["task"].count("[M"))
        trace.final_answer = "NEED MORE MEMORIES" if len(shown) < 9 else "o7"
        trace.models.append({"name": "q", "samples": [{"text": trace.final_answer}]})
        return trace
    monkeypatch.setattr(system, "answer", answer)
    tr = NS(retrieval={}, models=[], final_answer=None)
    item = {**KU, "item_id": "lme-1"}
    cfg = NS(solvers=["q"], extra={"memory": {"base_route": "fast", "graft_preset": "guide_b",
                                              "graft": {"ask_more": True, "ask_batch": 4, "ask_max": 3, "ask_cap": 200}}})
    out = asyncio.run(mr.run_memory_route("memory", item, mem, cfg, tr))
    assert shown == [2, 6, 10, 12] and out.retrieval["asks"] == 3 and out.retrieval["added"] == [4, 4, 2]
    assert out.retrieval["still_asking"] and "NEED MORE MEMORIES" in mr.ASK_RULE
    shown.clear()
    cfg.extra["memory"]["graft"]["ask_cap"] = 5     # the cap stops the asking
    out = asyncio.run(mr.run_memory_route("memory", item, mem, cfg, NS(retrieval={}, models=[], final_answer=None)))
    assert shown == [2, 5] and out.retrieval["facts_final"] == 5
    assert mr.wants_more("thinking...\nNEED MORE MEMORIES.") and not mr.wants_more("I need more memories to be sure, but: Paris")
