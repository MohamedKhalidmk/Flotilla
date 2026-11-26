"""The grader sanity check (user, 2026-11-26): known right and wrong answers are graded before any grading run, and a
broken environment stops the run instead of grading every math answer wrong."""
import pytest

from flotilla.core import tools
from flotilla.routers import label_loop


def test_cases_cover_math_and_instruction_both_ways():
    """Checks that the sanity cases hold a known-right and a known-wrong answer for both math and instruction questions.
    Guards against: a check that only tests one direction, so a grader that marks everything wrong (or right) passes."""
    kinds = {(it["task_type"], want) for it, _, want in label_loop.SANITY_CASES}
    for t in ("math", "instruction"):
        assert (t, True) in kinds and (t, False) in kinds


def test_broken_math_checker_stops_the_run(monkeypatch):
    """Checks that a math checker that cannot import sympy makes assert_grader_sane raise and name the cause.
    Guards against: the 2026-11-26 regrade where every math answer was silently graded wrong on a login node."""
    monkeypatch.setattr(tools, "sympy_check", lambda a, b: {"ok": False, "output": None,
                                                           "detail": "ModuleNotFoundError: No module named 'sympy'"})
    with pytest.raises(RuntimeError, match="sympy"):
        label_loop.assert_grader_sane()


def test_working_grader_passes(monkeypatch):
    """Checks that a grader giving every expected verdict passes and the check reports how many cases it ran.
    Guards against: a sanity check that stops good runs, so people learn to skip it."""
    def fake_grade(item, answer):
        return next(w for it, a, w in label_loop.SANITY_CASES if it is item and a == answer)
    monkeypatch.setattr(label_loop, "grade", fake_grade)
    assert label_loop.assert_grader_sane() == len(label_loop.SANITY_CASES)
