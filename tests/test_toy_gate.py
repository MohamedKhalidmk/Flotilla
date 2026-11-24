from flotilla.research import toy_gate


def test_toy_gate_stops_on_missing_answer_or_unforced_first_call():
    """Checks that the toy gate flags an empty final answer, a forced route whose first call did not name its tool or called another tool, an unparsed rule list, and a self-check with no program.
    Guards against: the pilot starting after a route quietly failed to parse, skipped its forced tool or never ran its check."""
    req = [{"name": "q", "extra": {"tool_choice": {"type": "function", "function": {"name": "python_exec"}}}}]
    ok = {"final_answer": "17", "tools": [{"name": "python_exec"}], "ifeval_rules": {}, "self_check": []}
    assert toy_gate.gate_problems("forced_code", ok, req) == []
    assert toy_gate.gate_problems("forced_code", {**ok, "final_answer": None}, req)
    assert toy_gate.gate_problems("forced_code", {**ok, "tools": [{"name": "sympy"}]}, req)
    assert toy_gate.gate_problems("forced_code", ok, [{"name": "q", "extra": {}}])
    assert toy_gate.gate_problems("forced_rules", {**ok, "tools": [{"name": "constraint_check"}]},
                                  [{"name": "q", "extra": {"tool_choice": {"function": {"name": "constraint_check"}}}}])
    assert toy_gate.gate_problems("self_check", {**ok, "tools": []}, [])


def test_toy_gate_grades_known_answers():
    """Checks the toy grader: a number inside a sentence, a fraction, a letter and a lowercase answer containing the city.
    Guards against: right toy answers reported wrong because of formatting."""
    assert toy_gate.number_in("The sum is 76,127.", 76127) and toy_gate.number_in("1/3", 1 / 3, 1e-6)
    assert toy_gate.grade({"check": {"kind": "letter", "value": "B"}}, "B") is True
    assert toy_gate.grade({"check": {"kind": "contains", "value": "paris"}}, "paris") is True
    assert not toy_gate.number_in("about 600", 599.55, 0.01)
