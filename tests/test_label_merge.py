"""The LongMemEval label merge's verdict checks (flotilla/routers/strategy_labels.py)."""
import json

import pytest

from flotilla.routers import strategy_labels as sl


def test_every_longmemeval_question_needs_exactly_one_verdict_per_route():
    """Checks that the merge names every question without an answer and every answer without a judge verdict.
    Guards against: a LongMemEval question silently left out of the labels, or graded by nobody, when a judge job dies."""
    v = {("lme-1", "fast"): True, ("lme-1", "memory"): False, ("lme-2", "fast"): True}
    assert sl.verdict_problems(["lme-1", "lme-2"], {"lme-1", "lme-2"}, ["fast", "memory"], {**v, ("lme-2", "memory"): True}) == []
    p = sl.verdict_problems(["lme-1", "lme-2", "lme-3"], {"lme-1", "lme-2"}, ["fast", "memory"], v)
    assert p == ["1 LongMemEval questions have no answer in every route: lme-3",
                 "1 LongMemEval answers have no judge verdict: memory: lme-2"]


def test_a_second_verdict_for_the_same_answer_stops_the_merge(tmp_path):
    """Checks that two judge verdicts for one (question, route) stop loading, naming the pair.
    Guards against: a stray verdict from a partial run folder silently replacing the chosen folder's verdict."""
    f = tmp_path / "verdicts.jsonl"
    rows = [{"item_id": "lme-1", "route": "fast", "correct": True}, {"item_id": "lme-1", "route": "fast", "correct": False}]
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(SystemExit, match="fast: lme-1"):
        sl.load_verdicts(str(f))
    f.write_text(json.dumps(rows[0]) + "\n")
    assert sl.load_verdicts(str(f)) == {("lme-1", "fast"): True}
