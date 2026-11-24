from flotilla.core.scoring import LIVE_STAGES, STAGE_RULES, error_stage


def _t(answers, final, *, models=None, vote=None, attempts=None, tools=None, retrieval=None, call_log=None, texts=None):
    names = models or ["q"] * len(answers)
    by = {}
    for i, (n, a) in enumerate(zip(names, answers)):
        by.setdefault(n, []).append({"text": (texts or {}).get(i, f"... {a}"), "final_answer": a})
    return {"models": [{"name": n, "samples": s} for n, s in by.items()], "final_answer": final,
            "vote": vote or {"rule": "majority of normalized answers", "winner": final,
                             "counts": {str(a): answers.count(a) for a in answers if a}},
            "verifier": {"attempts": attempts or [{"attempt": 1, "final_answer": final, "verdict": "accept", "checks": []}]},
            "tools": tools or [], "retrieval": retrieval or {}, "call_log": call_log or []}


RIGHT = {"4"}
grade = lambda a: None if a is None else a in RIGHT


def test_correct_is_none():
    """Checks that a right final answer gets stage none, whatever else happened.
    Guards against: right answers counted as errors in the stage table."""
    assert error_stage(_t(["4"], "4"), True, grade)["stage"] == "none"


def test_timeout_or_oom():
    """Checks that a question whose every sample crashed with a timeout or out-of-memory error, and so has no answer, is timeout_or_oom.
    Guards against: crashes counted as the model's format failures."""
    t = _t([None, None], None, texts={0: "ERROR APITimeoutError: Request timed out.", 1: "ERROR OutOfMemoryError: CUDA out of memory"})
    assert error_stage(t, False, grade)["stage"] == "timeout_or_oom"


def test_token_cap_and_format_parse_failure():
    """Checks that no final answer is token_cap when a call stopped at the token limit, and format_parse_failure otherwise; both are live stages.
    Guards against: answers cut at max_tokens mixed with answers that ended without the JSON block."""
    cut = _t([None], None, call_log=[{"finish_reason": "length"}])
    r = error_stage(cut, False, grade)
    assert r["stage"] == "token_cap" and r["live"]
    r = error_stage(_t([None], None, call_log=[{"finish_reason": "stop"}]), False, grade)
    assert r["stage"] == "format_parse_failure" and r["live"]


def test_verifier_false_reject():
    """Checks that a right first answer rejected by the verifier, followed by a wrong retry, is verifier_false_reject.
    Guards against: the verifier's wrong rejection being blamed on the model's reasoning."""
    att = [{"attempt": 1, "final_answer": "4", "verdict": "reject", "checks": [{"name": "math_parses", "passed": False}]},
           {"attempt": 2, "final_answer": "5", "verdict": "accept", "checks": []}]
    r = error_stage(_t(["4"], "5", attempts=att), False, grade)
    assert r["stage"] == "verifier_false_reject" and "verifier_rejected" in r["flags"] and "retry_used" in r["flags"]


def test_vote_wrong_and_tie_flag():
    """Checks that a wrong vote winner when some sample was right is vote_wrong, and that five different answers set the vote_tie flag.
    Guards against: a lost right sample counted as a reasoning error."""
    r = error_stage(_t(["4", "5", "6", "7", "8"], "5"), False, grade)
    assert r["stage"] == "vote_wrong" and "vote_tie" in r["flags"] and not r["live"]


def test_router_wrong_model():
    """Checks that with two solver models, a winner from the model whose samples were all wrong is router_wrong_model.
    Guards against: losing to the other model being reported as an ordinary vote loss."""
    r = error_stage(_t(["5", "5", "4"], "5", models=["qwen", "qwen", "phi"]), False, grade)
    assert r["stage"] == "router_wrong_model"


def test_retrieval_miss_only_on_memory_routes_with_evidence_missing():
    """Checks that a wrong Memory-route answer is retrieval_miss when no gold evidence was shown, reasoning_error when it was, and never retrieval_miss on an abstention question.
    Guards against: blaming retrieval for a question with nothing to retrieve, or for a miss with the evidence in hand."""
    mem = {"source": "graft", "fact_ids": ["f:1"]}
    assert error_stage(_t(["5"], "5", retrieval=mem), False, grade, evidence_shown=False)["stage"] == "retrieval_miss"
    assert error_stage(_t(["5"], "5", retrieval=mem), False, grade, evidence_shown=True)["stage"] == "reasoning_error"
    assert error_stage(_t(["5"], "5", retrieval=mem), False, grade, evidence_shown=False,
                       abstention=True)["stage"] == "reasoning_error"


def test_verifier_false_accept_needs_a_correctness_check():
    """Checks that a wrong answer accepted after a correctness check (public tests, constraints, LLM check) is verifier_false_accept, while one accepted after a form-only check is reasoning_error.
    Guards against: blaming the verifier for maths answers it can only check for form."""
    tests = [{"attempt": 1, "final_answer": "5", "verdict": "accept", "checks": [{"name": "public_tests", "passed": True}]}]
    assert error_stage(_t(["5"], "5", attempts=tests), False, grade)["stage"] == "verifier_false_accept"
    form = [{"attempt": 1, "final_answer": "5", "verdict": "accept", "checks": [{"name": "math_parses", "passed": True}]}]
    assert error_stage(_t(["5"], "5", attempts=form), False, grade)["stage"] == "reasoning_error"


def test_reasoning_error_and_ungraded_samples():
    """Checks that all samples wrong with nothing else to blame is reasoning_error, and that samples no grader can judge set samples_ungraded instead of vote_wrong.
    Guards against: a LongMemEval vote called right or wrong on samples nobody judged."""
    assert error_stage(_t(["5", "5", "6"], "5"), False, grade)["stage"] == "reasoning_error"
    r = error_stage(_t(["5", "x", "y"], "5"), False, lambda a: {"5": False}.get(a))
    assert r["stage"] == "reasoning_error" and "samples_ungraded" in r["flags"]


def test_flags_and_stage_lists():
    """Checks the tool_error and retrieval_fallback flags, and that every stage the tagger returns is in the rule list, with only gold-free stages marked live.
    Guards against: a stage name drifting from trace.py's ERROR_STAGES, or a gold-dependent stage offered to flotilla-deploy."""
    from flotilla.core.trace import ERROR_STAGES
    t = _t(["5"], "5", tools=[{"name": "python_exec", "ok": False}], retrieval={"source": "graft", "fallback": True})
    assert {"tool_error", "retrieval_fallback"} <= set(error_stage(t, False, grade)["flags"])
    assert set(STAGE_RULES) <= set(ERROR_STAGES)
    assert set(LIVE_STAGES) == {"timeout_or_oom", "token_cap", "format_parse_failure"}
