"""flotilla.supersede_check on hand-made graphs (the real-model check runs on the cluster; see the module docstring)."""
import json
from pathlib import Path

from flotilla.supersede_check import check

TOY = Path(__file__).parent / "data" / "supersede_toy.jsonl"


def fact(i, s, r, o, span=""):
    return {"type": "Fact", "id": f"f:{i}", "subject": s, "relation": r, "object": o, "provenance": {"span": span}}


def graph(facts, sup=()):
    return {"nodes": [{"type": "Entity", "id": "e:user", "name": "user"}] + facts,
            "edges": [{"type": "SUPERSEDES", "source": a, "target": b} for a, b in sup]}


def ret(*fs, outdated=()):
    return [{**f, "outdated": f["id"] in outdated} for f in fs]


def test_all_steps_pass_when_the_newer_fact_wins():
    old, new = fact(1, "user", "lives in", "France"), fact(2, "user", "lives in", "Canada")
    r = check(graph([old, new], [("f:2", "f:1")]), ret(new, old, outdated={"f:1"}), "France", "Canada", None)
    assert (r["extract"], r["link"], r["retrieve"]) == (True, True, True)


def test_each_failing_step_is_reported():
    old, new = fact(1, "user", "is based in", "Lyon, France"), fact(2, "user", "moved to", "Toronto", "Canada is home now")
    r = check(graph([old, new]), ret(old, new), "France", "Canada", None)          # reworded: no edge, old ranked first
    assert (r["extract"], r["link"], r["retrieve"]) == (True, False, False)
    r = check(graph([new]), ret(new), "France", "Canada", None)                     # old fact never extracted
    assert (r["extract"], r["link"], r["retrieve"]) == (False, False, True)


def test_chain_and_anchor():
    a = fact(1, "user", "is on episode", "10", "episode 10 of the History series")
    b = fact(2, "user", "is on episode", "30", "episode 30")
    c = fact(3, "user", "finished episode", "50", "the 50th History episode")
    noise = fact(4, "user", "reads", "10 pages", "10 pages a night")
    r = check(graph([a, b, c, noise], [("f:3", "f:2"), ("f:2", "f:1")]), ret(noise, c), "10", "50", "episode")
    assert r["link"] and r["retrieve"] and r["old_facts"] == ["f:1: user | is on episode | 10"]
    assert r["new_facts"] == ["f:3: user | finished episode | 50"]                  # "50th" counts as 50
    assert not check(graph([c]), [], "10", "50", "episode")["extract"]           # no old fact


def test_toy_items_carry_their_check():
    items = [json.loads(l) for l in open(TOY)]
    assert len(items) == 4 and all({"old", "new", "anchor"} <= set(i["supersede_check"]) for i in items)
    for it in items:
        dates = [s["date"] for s in it["sessions"]]
        assert dates == sorted(dates) and it["answer"] == it["supersede_check"]["new"]
        old_s, new_s = it["sessions"][0], it["sessions"][-1]
        assert it["supersede_check"]["old"] in old_s["turns"][0]["content"]
