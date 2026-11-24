import json
from collections import Counter
from pathlib import Path

from flotilla.memory import longmemeval as lme

SAMPLE = Path(__file__).parent / "data" / "longmemeval_sample.jsonl"
KEYS = {"item_id", "source", "task", "question_type", "question", "answer", "question_date", "sessions",
        "answer_session_ids", "abstention", "meta"}


def items():
    return [json.loads(l) for l in open(SAMPLE)]


def raw(item):
    """Back to the dataset's own layout, to check convert() round-trips it."""
    has = item["meta"]["has_answer_turns"]
    return {"question_id": item["meta"]["question_id"], "question_type": item["question_type"],
            "question": item["question"], "answer": item["meta"].get("answer_raw", item["answer"]),
            "question_date": item["question_date"], "answer_session_ids": item["answer_session_ids"],
            "haystack_session_ids": [s["session_id"] for s in item["sessions"]],
            "haystack_dates": [s["date"] for s in item["sessions"]],
            "haystack_sessions": [[{**t, **({"has_answer": True} if i in has.get(s["session_id"], []) else {})}
                                   for i, t in enumerate(s["turns"])] for s in item["sessions"]]}


def test_sample_format():
    """Checks that the 10-item LongMemEval sample has exactly the expected fields, all six question types, an abstention item and clean turns.
    Guards against: converted items with a missing or extra field, or an abstention flag that does not match the _abs question ID."""
    its = items()
    assert len(its) == 10
    assert len({it["question_type"] for it in its}) == 6       # every question type is in the sample
    for it in its:
        assert set(it) == KEYS
        assert it["item_id"] == f"lme-{it['meta']['question_id']}" and it["task"] == "memory"
        assert it["source"] == "longmemeval_s" and isinstance(it["answer"], str)
        assert it["abstention"] == it["meta"]["question_id"].endswith("_abs")
        for s in it["sessions"]:
            assert set(s) == {"session_id", "date", "turns"}
            assert all(set(t) == {"role", "content"} and t["role"] in ("user", "assistant") for t in s["turns"])
    assert any(it["abstention"] for it in its)


def test_convert_round_trip():
    """Checks that convert() on the raw dataset layout gives back the stored sessions, answer and map of answer-holding turns.
    Guards against: convert() dropping turns or losing which turns hold the answer."""
    for it in items():
        out = lme.convert(raw(it), "longmemeval_s")
        assert out["sessions"] == it["sessions"] and out["answer"] == it["answer"]
        assert out["meta"]["has_answer_turns"] == it["meta"]["has_answer_turns"]


def test_units_and_flags():
    """Checks that a long turn is cut into overlapping windows that keep every 13-word run whole, and that item_flags reports only a flagged turn or question.
    Guards against: a 13-gram overlap being missed because it straddles two windows, or a clean item being flagged as leaked."""
    ex = raw(items()[0])
    long_turn = " ".join(f"w{i}" for i in range(450))
    windows = lme._windows(long_turn)
    assert len(windows) == 3 and all(len(w.split()) <= lme.WINDOW for w in windows)
    words = long_turn.split()                               # every 13-gram lies whole inside some window
    assert all(any(" ".join(words[i:i + 13]) in w for w in windows) for i in range(len(words) - 12))
    t = ex["haystack_sessions"][0][0]["content"]
    assert lme.item_flags(ex, {lme.turn_key(t)}, set())[0].startswith("turn:")
    assert lme.item_flags(ex, set(), {ex["question_id"]}) == [f"question:{ex['question_id']}"]
    assert lme.item_flags(ex, set(), set()) == []


def test_split_is_seeded_and_stratified():
    """Checks that split() gives the same split whatever the input order, spreads each question type evenly, and puts no item in two splits.
    Guards against: the split changing when items are read in another order, or one question type missing from held-out."""
    fake = [{"item_id": f"lme-{t}{i}", "question_type": t} for t in "abc" for i in range(20)]
    sp = lme.split(fake)
    assert sp == lme.split(list(reversed(fake)))
    assert [len(sp[k]) for k in ("train", "dev", "held_out")] == [42, 9, 9]
    assert Counter(i[4] for i in sp["held_out"]) == {"a": 3, "b": 3, "c": 3}
    assert len(set(sp["train"]) | set(sp["dev"]) | set(sp["held_out"])) == 60


def test_history_prompt_orders_sessions_by_date():
    """Checks that history_prompt sorts sessions by date, lists every session, and ends with the question after the current date.
    Guards against: sessions shown out of date order, so the model reads an old fact as the newest one."""
    it = items()[0]
    p = lme.history_prompt({**it, "sessions": list(reversed(it["sessions"]))})
    assert p == lme.history_prompt(it)
    assert p.endswith(f"Question: {it['question']}") and f"Current Date: {it['question_date']}" in p
    assert p.count("### Session ") == len(it["sessions"])
