"""flotilla.supersede_check on hand-made graphs (the real-model check runs on the cluster; see the module docstring)."""
import json
from pathlib import Path

from flotilla.supersede_check import check

TOY = Path(__file__).parent / "data" / "supersede_toy.jsonl"


def fact(i, s, r, o, span="", chunk=0):
    return {"type": "Fact", "id": f"f:{i}", "subject": s, "relation": r, "object": o,
            "provenance": {"span": span, "chunk_id": chunk}}


def graph(facts, sup=()):
    return {"nodes": [{"type": "Entity", "id": "e:user", "name": "user"}] + facts,
            "edges": [{"type": "SUPERSEDES", "source": a, "target": b} for a, b in sup]}


def ret(*fs, outdated=()):
    return [{**f, "outdated": f["id"] in outdated} for f in fs]


def test_all_steps_pass_when_the_newer_fact_wins():
    """Checks that check() passes extract, link and retrieve when both facts exist, the newer one supersedes the older, and the older is marked outdated.
    Guards against: a correct graph and retrieval being reported as a failed supersede."""
    old, new = fact(1, "user", "lives in", "France"), fact(2, "user", "lives in", "Canada", chunk=2)
    r = check(graph([old, new], [("f:2", "f:1")]), ret(new, old, outdated={"f:1"}), "France", "Canada", None)
    assert (r["extract"], r["link"], r["retrieve"]) == (True, True, True)


def test_each_failing_step_is_reported():
    """Checks that check() fails the link and retrieve steps when a reworded new fact has no SUPERSEDES edge, and fails extract when the old fact is missing.
    Guards against: a broken step hidden behind a pass, so the wrong part of GRAFT gets blamed or fixed."""
    old = fact(1, "user", "is based in", "Lyon, France", "I'm based in Lyon, France")
    city = fact(2, "user", "moved to", "Toronto", "Canada is home now", chunk=2)
    new = fact(3, "user", "home country", "Canada", "Canada is home now", chunk=2)
    r = check(graph([old, city, new]), ret(old, new), "France", "Canada", None)    # no edge, old ranked first
    assert (r["extract"], r["link"], r["retrieve"]) == (True, False, False)
    r = check(graph([old, city, new], [("f:2", "f:1")]), ret(new, city), "France", "Canada", None)
    assert (r["extract"], r["link"], r["retrieve"]) == (True, True, True)          # superseded by the Toronto fact
    assert r["supersedes"] == ["f:1 superseded by f:2"]
    assert not check(graph([city]), ret(city), "France", "Canada", None)["extract"]  # the span alone is not a mention
    r = check(graph([new]), ret(new), "France", "Canada", None)                     # old fact never extracted
    assert (r["extract"], r["link"], r["retrieve"]) == (False, False, True)


def test_chain_and_anchor():
    """Checks that check() follows a chain of SUPERSEDES edges, uses the anchor word to ignore unrelated facts with the same number, and reads 50th as 50.
    Guards against: a fact like 10 pages a night being taken as the old episode 10 fact."""
    a = fact(1, "user", "is on", "episode 10 of the History series")
    b = fact(2, "user", "is on", "episode 30", chunk=1)
    c = fact(3, "user", "finished", "the 50th History episode", chunk=2)
    noise = fact(4, "user", "reads", "10 pages a night")
    r = check(graph([a, b, c, noise], [("f:3", "f:2"), ("f:2", "f:1")]), ret(noise, c), "10", "50", "episode")
    assert r["link"] and r["retrieve"] and r["old_facts"] == ["f:1: user | is on | episode 10 of the History series"]
    assert r["new_facts"] == ["f:3: user | finished | the 50th History episode"]  # "50th" counts as 50
    assert not check(graph([c]), [], "10", "50", "episode")["extract"]           # no old fact


def test_toy_items_carry_their_check():
    """Checks that the four toy items carry old, new and anchor values, dated sessions in order, the new value as answer and the old in session 1.
    Guards against: toy items whose answer or session order does not match their supersede check."""
    items = [json.loads(l) for l in open(TOY)]
    assert len(items) == 4 and all({"old", "new", "anchor"} <= set(i["supersede_check"]) for i in items)
    for it in items:
        dates = [s["date"] for s in it["sessions"]]
        assert dates == sorted(dates) and it["answer"] == it["supersede_check"]["new"]
        old_s, new_s = it["sessions"][0], it["sessions"][-1]
        assert it["supersede_check"]["old"] in old_s["turns"][0]["content"]
