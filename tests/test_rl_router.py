"""flotilla/routers/rl_router.py with fake models only: masks, stop, the supervised start, reward with the time penalty, chain
logging through the real Flotilla loop (memory_route.FakeQwen subclass), resume, held-out refusal, and the
beyond-oracle count with wrong-gold exclusion."""
import asyncio
import json

import numpy as np
import pytest

from flotilla.routers import rl_router as rl
from flotilla.core import system

ROUTES6 = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools"]
COST = {"fast": 2.0, "tools": 4.0, "deep": 8.0, "deep_tools": 12.0, "vote": 16.0, "vote_tools": 20.0}
GOLD = "42"
TRAIN = [f"q{i:02d}" for i in range(12)]
DEV = [f"q{i:02d}" for i in range(12, 16)]
NONE_MODEL, NONE_WRONG_GOLD = "q13", "q14"    # dev questions every fixed route gets wrong


def _cell(ok, ans=None):
    return {"correct": ok, "tokens_out": 100, "calls": 1, "wall_seconds": 10.0, "answer": ans if ans is not None else (GOLD if ok else "7")}


def make_fixture(tmp_path):
    """Six-route labels on 16 math questions (gold 42): fast right on even ids, every other route right everywhere,
    except q13 and q14 where every route answered 7. Held-out = one broken line that must never be parsed."""
    rows, items, pool = [], [], []
    for i, q in enumerate(TRAIN + DEV):
        none = q in (NONE_MODEL, NONE_WRONG_GOLD)
        r = {"id": q, "source": "gsm8k", "task_type": "math"}
        for rt in ROUTES6:
            r[rt] = _cell(False if none else (i % 2 == 0 if rt == "fast" else True))
        rows.append(r)
        items.append({"item_id": q, "bench": "strat12_00", "scorer": "router_label", "task_type": "math",
                      "task": f"What is 6 times 7? ({q})", "source": "gsm8k", "gold": None})
        pool.append({"id": q, "task_type": "math", "task": f"What is 6 times 7? ({q})", "gold": GOLD, "source": "gsm8k"})
    d = tmp_path / "graded"
    d.mkdir()
    with open(d / "per_question.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
        f.write('{"id": "h_broken", this held-out line is not JSON and must never be parsed\n')
    (d / "split.json").write_text(json.dumps({"seed": 1, "train": TRAIN, "dev": DEV, "held_out": ["h_broken"]}))
    summ = {"questions": 16, "per_strategy": {r: {"accuracy": 0.9 + 0.01 * k, "mean_wall_seconds": 10.0,
                                                  "gpu_seconds_job": COST[r] * 16} for k, r in enumerate(ROUTES6)}}
    (d / "summary.json").write_text(json.dumps(summ))
    with open(tmp_path / "items.jsonl", "w") as f:
        f.writelines(json.dumps(it) + "\n" for it in items)
        f.write('{"item_id": "h_broken", broken\n')
    with open(tmp_path / "pool.jsonl", "w") as f:
        f.writelines(json.dumps(p) + "\n" for p in pool)
    audit = tmp_path / "audit"
    audit.mkdir()
    diag = {NONE_MODEL: ["model wrong", "Qwen is wrong."], NONE_WRONG_GOLD: ["wrong gold", "The gold is wrong."]}
    (audit / "diagnosis.json").write_text(json.dumps(diag))
    (audit / "always_wrong.md").write_text(
        "# x\n\n## Model wrong (1)\n\n### q13 · math · gold: 42\n\n## Wrong gold (1)\n\n### q14 · math · gold: 42\n")
    return str(d), [str(tmp_path / "items.jsonl")], str(tmp_path / "pool.jsonl"), audit


def write_priors(path, ids, p, pick):
    with open(path, "w") as f:
        for i in ids:
            f.write(json.dumps({"id": i, "router": "test", "pick": pick, "p": p}) + "\n")
    return f"file:{path}"


def cfg(**kw):
    return rl.RLConfig(**{"alpha": 0.001, "max_steps": 3, "max_gpu_s": 60.0, "max_repeats": 2, **kw})


def pool_item(q="q00"):
    return {"item_id": q, "task_type": "math", "task": "What is 6 times 7?"}


LME_ITEM = {"item_id": "lme-1", "source": "longmemeval_s", "question": "Who is Bob married to?", "answer": "Carla",
            "question_date": "2023/08/01 (Tue) 12:00", "task": "memory", "task_type": "memory", "bench": "lme",
            "sessions": [{"session_id": "s1", "date": "2023/07/03 (Mon) 08:30",
                          "turns": [{"role": "user", "content": "Bob is married to Carla."}]}]}
FAKE_MEM = {"item_id": "lme-1", "graph_key": "k", "retrieval_key": "r", "chunk_map": [{"date": "2023/07/03"}],
            "retrieval": {"facts": [{"id": "f1", "chunk_id": 0, "subject": "Bob", "relation": "married to", "object": "Carla"}]},
            "build": {"wall_seconds": 32.0, "llm_calls": 10}, "graft": {}}


def state(item, policy, row=None, p=None, pick=None):
    return rl.State(item, np.zeros(rl.R) if p is None else p, pick, rl.offered_routes(item, row, policy.cfg))


# ---------------------------------------------------------------- masks and stop

def test_masks_memory_repeats_stop_and_budgets():
    """Checks that the policy mask hides Memory on pool questions, limits repeats, allows stop only after a step, and enforces GPU and step budgets.
    Guards against: the RL policy running the same greedy route twice or going past max_gpu_s on one question."""
    pol = rl.Policy(cfg(), {r: COST.get(r, 25.0) for r in rl.ROUTES}, rl.sampled_routes())
    assert rl.sampled_routes() == {"vote", "vote_tools", "vote_memory"}
    # pool question: no Memory route, no stop before the first step
    st = state(pool_item(), pol)
    m, forced = pol.mask(st)
    allowed = {rl.ACTIONS[j] for j in np.where(m)[0]}
    assert forced is None and allowed == set(ROUTES6)
    # question with a history: Memory routes offered (vote_memory costs 25 > nothing, fits 60)
    m, _ = pol.mask(state(LME_ITEM, pol))
    assert {"memory", "memory_deep", "deep_tools_memory", "vote_memory"} <= {rl.ACTIONS[j] for j in np.where(m)[0]}
    # after a greedy route and a sampled route: greedy not again, sampled again until max_repeats, stop now allowed
    st.steps.append({"route": "deep", "answer": "42", "verdict": "accept", "gpu_seconds": 8.0})
    st.runs["deep"] += 1
    st.steps.append({"route": "vote", "answer": "42", "verdict": "accept", "gpu_seconds": 16.0})
    st.runs["vote"] += 1
    st.cost = 24.0
    allowed = {rl.ACTIONS[j] for j in np.where(pol.mask(st)[0])[0]}
    assert "deep" not in allowed and "vote" in allowed and "stop" in allowed
    assert "vote_tools" in allowed                       # 24 + 20 <= 60
    st.runs["vote"] = 2
    assert "vote" not in {rl.ACTIONS[j] for j in np.where(pol.mask(st)[0])[0]}
    # GPU budget: a route that would pass max_gpu_s is masked; past the budget only stop (forced)
    st.cost = 45.0
    allowed = {rl.ACTIONS[j] for j in np.where(pol.mask(st)[0])[0]}
    assert "vote_tools" not in allowed and "fast" in allowed
    st.cost = 61.0
    m, forced = pol.mask(st)
    assert forced == "max_gpu_s" and list(np.where(m)[0]) == [rl.NA - 1]
    # step budget
    st.cost = 0.0
    st.steps.append({"route": "fast", "answer": "42", "verdict": "accept", "gpu_seconds": 2.0})
    assert pol.mask(st)[1] == "max_steps"
    # a budget below every route at step 0 still leaves the cheapest route
    tight = rl.Policy(cfg(max_gpu_s=1.0), {r: COST.get(r, 25.0) for r in rl.ROUTES}, rl.sampled_routes())
    m, forced = tight.mask(state(pool_item(), tight))
    assert forced is None and {rl.ACTIONS[j] for j in np.where(m)[0]} == {"fast"}


def test_untrained_policy_starts_from_the_supervised_pick_and_stops_on_accept():
    """Checks that an untrained policy takes the supervised pick first, stops after an accept, and moves to the best route after a reject.
    Guards against: a new policy ignoring the supervised pick, or stopping on an answer the verifier rejected."""
    pol = rl.Policy(cfg(), {r: COST.get(r, 25.0) for r in rl.ROUTES}, rl.sampled_routes())
    p = np.zeros(rl.R)
    p[rl.ROUTES.index("vote")], p[rl.ROUTES.index("deep")], p[rl.ROUTES.index("fast")] = 0.99, 0.6, 0.9
    st = state(pool_item(), pol, p=p, pick="deep")      # supervised router said deep, though vote scores higher
    a, _ = pol.act(pol.features(st), pol.mask(st)[0])
    assert rl.ACTIONS[a] == "deep"
    st.steps.append({"route": "deep", "answer": "42", "verdict": "accept", "gpu_seconds": 8.0})
    st.runs["deep"] += 1
    a, _ = pol.act(pol.features(st), pol.mask(st)[0])
    assert rl.ACTIONS[a] == "stop"
    st.steps[-1]["verdict"] = "reject"
    a, _ = pol.act(pol.features(st), pol.mask(st)[0])
    assert rl.ACTIONS[a] == "vote"                      # escalate to the best estimate after a rejection


def test_update_moves_q_towards_targets_and_save_load(tmp_path):
    """Checks that repeated updates pull the Q-value toward the target, and that a saved policy loads with the same Q-values and update count.
    Guards against: a resumed run starting from a policy whose weights or update count were lost on save."""
    pol = rl.Policy(cfg(), {r: COST.get(r, 25.0) for r in rl.ROUTES}, rl.sampled_routes())
    st = state(pool_item(), pol, pick="fast")
    psi = pol.features(st)
    q0 = pol.q(psi)[0]
    for _ in range(50):
        pol.update(psi, 0, -1.0)
    assert pol.q(psi)[0] < q0 - 0.5
    pol.save(tmp_path / "p.npz")
    back = rl.Policy.load(tmp_path / "p.npz")
    assert np.allclose(back.q(psi), pol.q(psi)) and back.updates == 50


def test_gpu_clock_shares_time_between_steps(monkeypatch):
    """Checks that GpuClock splits GPU time equally between steps running at the same time and counts time with no step as idle.
    Guards against: two parallel steps each being charged the full wall time."""
    t = [0.0]
    monkeypatch.setattr(rl.time, "monotonic", lambda: t[0])
    c = rl.GpuClock(gpus=1)
    c.start("a")
    t[0] = 10.0
    c.start("b")
    t[0] = 20.0
    assert c.stop("a") == pytest.approx(15.0)           # 10 alone + 10 shared by two
    t[0] = 25.0
    assert c.stop("b") == pytest.approx(10.0)
    t[0] = 30.0
    c._tick()
    assert c.idle == pytest.approx(5.0)


# ---------------------------------------------------------------- the real loop with fake Qwen

def test_every_route_reaches_the_model_with_its_own_settings(monkeypatch):
    """Checks that each route runs through the real loop with its own sample count, and the GRAFT build is charged only on the step that asks.
    Guards against: vote running one sample instead of five, or the graph build being charged on every Memory route step."""
    answers = {("q00", r): GOLD for r in rl.ROUTES} | {("lme-1", r): "Carla" for r in rl.ROUTES}
    fake = rl.replay_qwen(answers)
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    runner = rl.LoopRunner(memory={"lme-1": FAKE_MEM}, cost_override=lambda i, r: COST.get(r, 25.0))
    assert runner.sampled() == {"vote", "vote_tools", "vote_memory"}

    async def go():
        out = {}
        for r in rl.ROUTES:
            it = LME_ITEM if r in rl.MEMORY_ROUTES else pool_item()
            out[r] = await runner.run_step(it, r, 0, charge_build=r == "memory")
        return out
    res = asyncio.run(go())
    assert fake.mismatch == []
    assert {r: res[r]["answer"] for r in rl.ROUTES} == {r: ("Carla" if r in rl.MEMORY_ROUTES else GOLD) for r in rl.ROUTES}
    assert fake.calls[("q00", "vote")] == 5 and fake.calls[("q00", "fast")] == 1
    assert res["vote"]["samples"] == 5 and res["fast"]["verdict"] == "accept"
    assert res["memory"]["graft_build_gpu_seconds"] == pytest.approx(32.0 / 16)    # build charged once, here
    assert res["memory"]["gpu_seconds"] == pytest.approx(25.0 + 2.0)
    assert res["memory_deep"]["graft_build_gpu_seconds"] == 0.0
    assert "MEMORY (" in fake.seen[-1]["messages"][1]["content"] or any("MEMORY (" in s["messages"][1]["content"]
                                                                         for s in fake.seen if s["step"][0] == "lme-1")


def _ctx(labels, items, prior_spec, c, tmp_path, names=("train", "dev")):
    data = rl.load_data(labels, items, list(names))
    return data, rl.Ctx(data, rl.make_prior(prior_spec, data, data.ids["train"], 0.95), c, 1)


def test_chain_reward_time_penalty_targets_and_log(tmp_path, monkeypatch):
    """Checks that a chain moves to vote after a rejected fast step and logs steps, GPU-seconds, the reward with the alpha time penalty, and the Q targets.
    Guards against: a wrong final answer earning anything other than minus the time penalty."""
    labels, items, _, _ = make_fixture(tmp_path)
    spec = write_priors(tmp_path / "pri.jsonl", TRAIN + DEV, {"fast": 0.9, "vote": 0.95, "tools": 0.1, "deep": 0.1,
                                                               "deep_tools": 0.1, "vote_tools": 0.1}, "fast")
    c = cfg(alpha=0.01)
    data, ctx = _ctx(labels, items, spec, c, tmp_path)
    fake = rl.replay_qwen({("q03", "fast"): "", ("q03", "vote"): [GOLD]})   # fast: no answer -> verifier rejects
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    runner = rl.LoopRunner(cost_override=data.gpu)
    grader = rl.LabelGrader(data.rows)
    pol = rl.Policy(c, data.cost, runner.sampled())
    out = tmp_path / "run"
    out.mkdir()
    n = asyncio.run(rl.run_many([data.items["q03"]], ctx, pol, runner, grader, out, "t", 0, True, "eval", 4, None, False))
    assert n == 1 and fake.mismatch == []
    ch = rl.read_jsonl(out / "chains_t.jsonl")[0]
    assert [s["route"] for s in ch["steps"]] == ["fast", "vote"]
    assert [s["verdict"] for s in ch["steps"]] == ["reject", "accept"]
    assert [s["answer"] for s in ch["steps"]] == ["", GOLD] and ch["final_answer"] == GOLD and ch["correct"]
    assert ch["stop_reason"] == "policy" and ch["steps"][0]["retried"] is True
    assert [s["gpu_seconds"] for s in ch["steps"]] == [2.0, 16.0] and ch["gpu_seconds"] == 18.0
    assert all(s["tokens_out"] > 0 and s["tokens_total"] > 0 for s in ch["steps"])
    assert ch["reward"] == pytest.approx(1 - 0.01 * 18) and ch["alpha"] == 0.01
    assert [d["action"] for d in ch["decisions"]] == ["fast", "vote", "stop"]
    assert [d["target"] for d in ch["decisions"]] == pytest.approx([1 - 0.18, 1 - 0.16, 1.0])
    assert len(ch["decisions"][0]["psi"]) == rl.D and "stop" not in ch["decisions"][0]["allowed"]
    traces = rl.read_jsonl(out / "traces_t.jsonl")
    assert [t["route"] for t in traces] == ["fast", "vote"] and traces[1]["trace"]["vote"]["winner"] == GOLD
    # a wrong final answer: reward is minus the time penalty only
    fake.answers[("q05", "fast")] = "7"
    asyncio.run(rl.run_many([data.items["q05"]], ctx, pol, runner, grader, out, "t", 0, True, "eval", 4, None, False))
    ch = rl.read_jsonl(out / "chains_t.jsonl")[1]
    assert not ch["correct"] and ch["reward"] == pytest.approx(-0.01 * 2.0)


def test_final_rules():
    """Checks that final_answer returns the last accepted answer, the last answer, or the vote winner as each rule says, and None when there are no steps.
    Guards against: a chain under the last_accept rule returning a rejected answer when an earlier step was accepted."""
    steps = [{"answer": "3", "verdict": "accept"}, {"answer": "4", "verdict": "reject"}]
    assert rl.final_answer(steps, "last_accept", "math") == ("3", 0)
    assert rl.final_answer(steps, "last", "math") == ("4", 1)
    assert rl.final_answer(steps + [{"answer": "3", "verdict": "reject"}], "vote", "math") == ("3", 2)
    assert rl.final_answer([], "last_accept", "math") == (None, None)


# ---------------------------------------------------------------- CLI: train, resume, evaluate, held-out

def _live_args(labels, items, pool, out):
    return ["--labels", labels, "--items", *items, "--out", str(out), "--server-url", "http://fake/v1", "--pool", pool,
            "--concurrency", "4"]


def test_train_resume_and_config_guard(tmp_path, monkeypatch):
    """Checks that training resumes after a job killed mid-write without redoing finished epochs, refuses a changed alpha or held-out IDs, and logs compute.
    Guards against: a resumed run repeating epoch 0 or continuing with a different alpha than the run it extends."""
    labels, items, pool, _ = make_fixture(tmp_path)
    fake = rl.replay_qwen({(q, r): GOLD for q in TRAIN for r in ROUTES6})
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    out = tmp_path / "rl"
    base = ["train", *_live_args(labels, items, pool, out), "--max-questions", "5"]
    rl.main(base + ["--epochs", "1"])
    ch = rl.read_jsonl(out / "chains_train.jsonl")
    assert len(ch) == 5 and {c["epoch"] for c in ch} == {0} and (out / "policy_epoch0.npz").exists()
    with open(out / "chains_train.jsonl", "a") as f:
        f.write('{"mode": "train", "epoch": 1, "item_id": "q0')         # a job killed mid-write
    rl.main(base + ["--epochs", "2"])                                    # resume: epoch 0 not run again
    lines = open(out / "chains_train.jsonl").read().splitlines()
    good = [json.loads(l) for l in lines if l.endswith("}")]
    assert sorted(Counter_(c["epoch"] for c in good).items()) == [(0, 5), (1, 5)]
    pol = rl.Policy.load(out / "policy.npz")
    assert pol.updates == sum(len(c["decisions"]) for c in good)
    assert all(i in TRAIN for i in (c["item_id"] for c in good))
    with pytest.raises(SystemExit, match="alpha"):
        rl.main(base + ["--alpha", "0.5"])
    with pytest.raises(SystemExit, match="held-out"):
        rl.main(["train", *_live_args(labels, items, pool, tmp_path / "x"), "--ids", "h_broken"])
    comp = rl.read_jsonl(out / "compute.jsonl")
    assert comp and "gpu_seconds_job" in comp[-1]


def Counter_(xs):
    from collections import Counter
    return Counter(xs)


def test_held_out_never_read_without_the_flag(tmp_path):
    """Checks that the held-out split is refused without the flag, its lines are never parsed, and a held-out item cannot be run as a chain.
    Guards against: the RL router reading or training on held-out questions."""
    labels, items, _, _ = make_fixture(tmp_path)
    with pytest.raises(SystemExit, match="held-out"):
        rl.load_data(labels, items, ["train", "held_out"])
    data = rl.load_data(labels, items, ["train", "dev"])        # the broken held-out lines are skipped unparsed
    assert set(data.rows) == set(TRAIN + DEV) and "h_broken" in data.held_out
    ctx = rl.Ctx(data, rl.make_prior("route-accuracy", data, TRAIN, 0.95), cfg(), 1)
    pol = rl.Policy(cfg(), data.cost, rl.sampled_routes())
    with pytest.raises(SystemExit, match="held-out"):
        asyncio.run(rl.run_chain({"item_id": "h_broken", "task": "x", "task_type": "math"}, ctx, pol, None, None, 0, True, "eval"))


def test_exclusions_from_the_audit(tmp_path):
    """Checks that exclusions list only the audit's wrong-gold questions, round-trip through a file, and stop when the two audit files disagree.
    Guards against: a model-wrong question excluded as wrong gold, which would change the beyond-oracle count."""
    _, _, _, audit = make_fixture(tmp_path)
    assert rl.build_exclusions(audit) == [(NONE_WRONG_GOLD, "wrong gold")]
    rl.main(["exclusions", "--audit", str(audit), "--out", str(tmp_path / "ex.txt")])
    assert rl.read_exclusions(tmp_path / "ex.txt") == {NONE_WRONG_GOLD}
    assert rl.audit_golds(audit) == {NONE_MODEL: GOLD, NONE_WRONG_GOLD: GOLD}
    (audit / "always_wrong.md").write_text("## Model wrong (2)\n\n### q13 · math · gold: 1\n\n### q14 · math · gold: 1\n")
    with pytest.raises(SystemExit, match="disagree"):
        rl.build_exclusions(audit)


def test_beyond_oracle_counts_only_questions_every_route_missed_minus_wrong_gold(tmp_path):
    """Checks that beyond_oracle counts only solved questions that every fixed route missed, and leaves out those with a wrong gold.
    Guards against: a solved wrong-gold question being reported as beating the oracle."""
    labels, items, _, _ = make_fixture(tmp_path)
    data = rl.load_data(labels, items, ["train", "dev"])
    chains = [{"item_id": NONE_MODEL, "correct": True}, {"item_id": NONE_WRONG_GOLD, "correct": True},
              {"item_id": "q12", "correct": True}, {"item_id": "q15", "correct": False}]
    bo = rl.beyond_oracle(chains, data.rows, {NONE_WRONG_GOLD})
    assert bo["count"] == 1 and [c["item_id"] for c in bo["questions"]] == [NONE_MODEL]
    assert bo["excluded_solved"] == 1
    assert rl.beyond_oracle(chains, data.rows, set())["count"] == 2
    assert rl.beyond_oracle([{"item_id": NONE_MODEL, "correct": False}], data.rows, set())["count"] == 0


def test_evaluate_on_dev_reports_beyond_oracle_with_chains(tmp_path, monkeypatch):
    """Checks that evaluate on dev writes chains, a table and a beyond-oracle report when a second vote run solves questions every fixed route missed.
    Guards against: the beyond-oracle table counting a wrong-gold question, or losing the repeat number of a sampled step.

    Vote's first run gives no answer (rejected); its second run (sampled) finds the gold on the two dev questions
    every fixed route missed. One has a wrong gold: counted 1, excluded 1. Real pool grader (label_loop.grade)."""
    labels, items, pool, audit = make_fixture(tmp_path)
    out = tmp_path / "rl"
    out.mkdir()
    spec = write_priors(tmp_path / "pri.jsonl", TRAIN + DEV, {"vote": 0.99, "fast": 0.1, "tools": 0.1, "deep": 0.1,
                                                               "deep_tools": 0.1, "vote_tools": 0.1}, "vote")
    rl.Policy(cfg(), rl.load_data(labels, items, ["train"]).cost, rl.sampled_routes()).save(out / "policy.npz")
    ans = {(q, r): GOLD for q in DEV for r in ROUTES6}
    for q in (NONE_MODEL, NONE_WRONG_GOLD):
        ans[(q, "vote")] = ["", GOLD]
    fake = rl.replay_qwen(ans)
    monkeypatch.setattr(system, "client_for", lambda srv: fake)
    rl.main(["exclusions", "--audit", str(audit), "--out", str(tmp_path / "ex.txt")])
    rl.main(["evaluate", *_live_args(labels, items, pool, out), "--prior", spec, "--exclude", str(tmp_path / "ex.txt")])
    ch = {c["item_id"]: c for c in rl.read_jsonl(out / "chains_eval_dev.jsonl")}
    assert set(ch) == set(DEV) and fake.mismatch == []
    assert [s["route"] for s in ch[NONE_MODEL]["steps"]] == ["vote", "vote"] and ch[NONE_MODEL]["correct"]
    assert [s["repeat"] for s in ch[NONE_MODEL]["steps"]] == [0, 1]
    tab = json.loads((out / "table_dev.json").read_text())
    rl_row = next(r for r in tab["rows"] if r["row"] == "rl")
    assert rl_row["beyond_oracle"] == 1 and rl_row["solved_but_wrong_gold"] == 1 and rl_row["accuracy"] == 1.0
    assert tab["beyond_oracle_ids"] == [NONE_MODEL] and tab["excluded_solved_ids"] == [NONE_WRONG_GOLD]
    oracle = next(r for r in tab["rows"] if r["row"] == "oracle")
    assert oracle["accuracy"] == 0.5
    md = (out / "beyond_oracle_dev.md").read_text()
    assert "**Count: 1**" in md and f"### {NONE_MODEL}" in md and "| 2 | vote | 2 | 42 | accept | True |" in md
    assert "beyond_oracle" in (out / "table_dev.md").read_text()


def test_dry_run_end_to_end(tmp_path, monkeypatch):
    """Checks that the dry-run command writes a table marked DRY RUN, the wrong-gold exclusions, and six train and six eval chains.
    Guards against: dry-run output that could be mistaken for a real result."""
    labels, items, _, _ = make_fixture(tmp_path)
    monkeypatch.setattr(system, "client_for", system.client_for)      # restored after the dry run patches it
    out = tmp_path / "dry"
    rl.main(["dry-run", "--labels", labels, "--items", *items, "--out", str(out), "--n", "6",
             "--include-always-wrong", "0", "--epochs", "1"])
    text = (out / "table_train_dryrun.md").read_text()
    assert text.startswith("DRY RUN, NOT A RESULT") and "| rl |" in text
    assert rl.read_exclusions(out / "excluded_wrong_gold.txt") == {NONE_WRONG_GOLD}
    assert len(rl.read_jsonl(out / "chains_train.jsonl")) == 6 and len(rl.read_jsonl(out / "chains_eval_train_dryrun.jsonl")) == 6


def test_estimate_from_labels(tmp_path):
    """Checks that the estimate command counts train questions per epoch, gives positive GPU-hours, and simulates the dev questions.
    Guards against: a compute estimate that leaves out the dev questions or reports zero GPU-hours."""
    labels, items, _, _ = make_fixture(tmp_path)
    rl.main(["estimate", "--labels", labels, "--items", *items, "--out", str(tmp_path / "est"), "--epochs", "2"])
    est = json.loads((tmp_path / "est" / "estimate.json").read_text())
    assert est["train_questions_per_epoch"] == len(TRAIN) and est["train_gpu_hours"] > 0
    assert est["simulation"]["dev_greedy"]["questions"] == len(DEV)
