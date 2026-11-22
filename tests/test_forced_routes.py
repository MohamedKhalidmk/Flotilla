import asyncio
import json
from types import SimpleNamespace as NS

import pytest

from flotilla import system
from flotilla.trace import Trace


def _reply(r):
    """A fake chat completion: a string is plain content; {"tool": (name, input)} is one native tool call;
    {"content": ..., "reasoning": ...} sets both."""
    if isinstance(r, dict) and "tool" in r:
        name, arg = r["tool"]
        msg = NS(content=r.get("content", ""), reasoning_content=r.get("reasoning"),
                 tool_calls=[NS(id="c1", function=NS(name=name, arguments=json.dumps({"input": arg})))])
        fin = "tool_calls"
    else:
        r = r if isinstance(r, dict) else {"content": r}
        msg = NS(content=r.get("content", ""), reasoning_content=r.get("reasoning"), tool_calls=None)
        fin = "stop"
    return NS(choices=[NS(message=msg, finish_reason=fin)], usage=NS(prompt_tokens=100, completion_tokens=10))


def _run(item, cfg, replies, monkeypatch):
    calls = []

    async def create(name, srv, client, msgs, cfg_, temperature, **extra):
        role = name.split(":")[1] if ":" in name else "solve"
        calls.append({"role": role, "msgs": [dict(m) for m in msgs], "extra": extra, "srv": srv, "temperature": temperature})
        return _reply(replies[role].pop(0))
    monkeypatch.setattr(system, "_create", create)
    monkeypatch.setattr(system, "client_for", lambda srv: None)
    tr = Trace(run_id="t", protocol_version="p", prompt_versions={}, benchmark="b", item_id="1", split="dev")
    return asyncio.run(system.answer(item, {}, cfg, tr)), calls


def _cfg(**kw):
    srv = {"q": {"url": "u", "model": "m", "quant": "w4a16", "native_tools": True}}
    return system.SystemConfig(servers=srv, solvers=["q"], verifier=False, **kw)


def test_forced_route_names_its_tool_on_the_first_call_only(monkeypatch):
    """Checks that a forced route sends tool_choice naming its tool on the first call, plain tools afterwards and no tools on the last round, and adds the forced-tool wording to the system message.
    Guards against: "required" (any tool) instead of the named tool, or a forced choice repeated on every round."""
    item = {"item_id": "1", "task": "Sum of primes below 10?", "task_type": "math"}
    replies = {"solve": [{"tool": ("python_exec", "print(2+3+5+7)")}, {"tool": ("sympy", "2+3+5+7")},
                         '{"final_answer": "17"}']}
    tr, calls = _run(item, _cfg(tools=True, forced_tool="python_exec", tool_rounds=2), replies, monkeypatch)
    assert calls[0]["extra"]["tool_choice"] == {"type": "function", "function": {"name": "python_exec"}}
    assert "tool_choice" not in calls[1]["extra"] and calls[1]["extra"].get("tools")
    assert "tools" not in calls[2]["extra"]                       # last round: answer, no tools
    assert "You must use python_exec" in calls[0]["msgs"][0]["content"] and tr.final_answer == "17"


def test_reasoning_is_sent_back_across_tool_rounds(monkeypatch):
    """Checks that the assistant turn sent after a tool round carries that round's reasoning, and that keep_reasoning false leaves it out.
    Guards against: Qwen restarting its thinking after every tool result (run-04's Deep+Tools and Vote+Tools)."""
    item = {"item_id": "1", "task": "2+2?", "task_type": "math"}
    replies = lambda: {"solve": [{"tool": ("python_exec", "print(4)"), "reasoning": "I will compute 2+2."},
                                 '{"final_answer": "4"}']}
    _, calls = _run(item, _cfg(tools=True), replies(), monkeypatch)
    turn = [m for m in calls[1]["msgs"] if m["role"] == "assistant"][0]
    assert turn["reasoning"] == "I will compute 2+2." and turn["tool_calls"]
    _, calls = _run(item, _cfg(tools=True, keep_reasoning=False), replies(), monkeypatch)
    assert "reasoning" not in [m for m in calls[1]["msgs"] if m["role"] == "assistant"][0]


def test_interpreter_error_reaches_qwen_and_the_trace(monkeypatch):
    """Checks that a failing python_exec program's error text is in the tool message Qwen gets next and in the trace's detail field.
    Guards against: errors Qwen could not read, or a trace that hides why a tool call failed."""
    item = {"item_id": "1", "task": "det?", "task_type": "math"}
    replies = {"solve": [{"tool": ("python_exec", "import numpy_not_installed_xyz")}, '{"final_answer": "5"}']}
    tr, calls = _run(item, _cfg(tools=True, forced_tool="python_exec"), replies, monkeypatch)
    tool_msg = [m for m in calls[1]["msgs"] if m["role"] == "tool"][0]["content"]
    assert "ModuleNotFoundError" in tool_msg
    assert tr.tools[0]["ok"] is False and "ModuleNotFoundError" in tr.tools[0]["detail"]


def test_self_check_pass_stops_after_one_check(monkeypatch):
    """Checks that F40 runs a check with python_exec forced and thinking off, and stops when the program prints CHECK PASS, keeping the answer.
    Guards against: revisions after a passing check, or a check run with thinking on."""
    item = {"item_id": "1", "task": "17*23?", "task_type": "math"}
    replies = {"solve": ['{"final_answer": "391"}'],
               "check": [{"tool": ("python_exec", "print('CHECK PASS' if 17*23 == 391 else 'CHECK FAIL: no')")}]}
    tr, calls = _run(item, _cfg(self_check_rounds=3), replies, monkeypatch)
    chk = [c for c in calls if c["role"] == "check"]
    assert len(chk) == 1 and chk[0]["extra"]["tool_choice"]["function"]["name"] == "python_exec"
    assert chk[0]["srv"]["request"]["extra_body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert tr.final_answer == "391" and tr.self_check[0]["passed"] and len(tr.self_check) == 1


def test_self_check_fail_revises_and_unchanged_answer_stops(monkeypatch):
    """Checks that a failing check leads to a revision that sees the program and its output, that a changed answer is checked again, and that an unchanged answer stops (CRITIC's rule).
    Guards against: endless check-revise loops, or a revision that never sees why the check failed."""
    item = {"item_id": "1", "task": "17*23?", "task_type": "math"}
    replies = {"solve": ['{"final_answer": "381"}', '{"final_answer": "391"}', '{"final_answer": "391"}'],
               "check": [{"tool": ("python_exec", "print('CHECK FAIL: 17*23 is', 17*23)")},
                         {"tool": ("python_exec", "print('CHECK FAIL: still unsure')")}]}
    tr, calls = _run(item, _cfg(self_check_rounds=3), replies, monkeypatch)
    revise = [c for c in calls if c["role"] == "solve"][1]["msgs"][-1]["content"]
    assert "CHECK FAIL: 17*23 is 391" in revise and "381" in revise
    assert tr.final_answer == "391" and len(tr.self_check) == 2 and tr.self_check[1]["revised"] == "391"
    assert sum(1 for m in tr.models if m["name"] in ("q:check", "q:revise")) == 4   # every call counted


def test_self_check_error_is_a_fail_and_three_rounds_at_most(monkeypatch):
    """Checks that a check program that raises counts as a fail with its error shown to the revision, and that the loop stops after three rounds.
    Guards against: a crashing check read as a pass, or more than three check-revise rounds."""
    item = {"item_id": "1", "task": "x?", "task_type": "math"}
    replies = {"solve": ['{"final_answer": "1"}', '{"final_answer": "2"}', '{"final_answer": "3"}', '{"final_answer": "4"}'],
               "check": [{"tool": ("python_exec", "raise ValueError('boom')")}] * 3}
    tr, calls = _run(item, _cfg(self_check_rounds=3), replies, monkeypatch)
    assert len(tr.self_check) == 3 and not any(r["passed"] for r in tr.self_check)
    assert "ValueError: boom" in tr.self_check[0]["output"] and tr.final_answer == "4"


def test_check_verdict_reads_the_last_check_line():
    """Checks that only a final CHECK PASS line passes, and that no line, a FAIL, or PASS followed by FAIL does not.
    Guards against: a program that prints PASS early and fails later being taken as a pass."""
    assert system.check_verdict("x\nCHECK PASS\n") and system.check_verdict("CHECK PASS: nothing to compute")
    assert not system.check_verdict("CHECK PASS\nCHECK FAIL: late") and not system.check_verdict("no verdict")


def test_ground_truth_grading_uses_open_instruct_rules():
    """Checks that instruction answers are graded by the question's RLVR-IFeval ground-truth rule (open-instruct's function), that string options are split before the choice check, and that a JSON-format rule is met by the loop.
    Guards against: the old regex grader that found a rule in only 106 of 236 questions, or a choice check that passes any answer."""
    from flotilla.ifeval_rules import grade_ground_truth, split_options
    from flotilla.vendor.open_instruct_if_functions import IF_FUNCTIONS_MAP
    rlvr = ["validate_sections", "verify_keyword_frequency", "validate_quotation", "validate_highlighted_sections",
            "verify_postscript", "validate_uppercase", "validate_placeholders", "validate_no_commas",
            "validate_json_format", "validate_lowercase", "verify_bullet_points", "verify_letter_frequency",
            "validate_frequency_capital_words", "validate_end", "validate_word_constraint", "validate_forbidden_words",
            "validate_two_responses", "validate_choice", "verify_paragraph_count", "validate_paragraphs",
            "validate_title", "verify_keywords", "verify_sentence_constraint", "validate_repeat_prompt"]
    assert set(rlvr) <= set(IF_FUNCTIONS_MAP)
    gt = lambda **k: json.dumps({"func_name": k.pop("f"), "N": None, "options": None, **k})
    assert grade_ground_truth("a b c d e f g h i j k l m n o", gt(f="validate_word_constraint", N=14, quantifier="at least"))
    assert not grade_ground_truth("C", gt(f="validate_word_constraint", N=14, quantifier="at least"))
    assert split_options("a), b), c), d)") == ["a)", "b)", "c)", "d)"] and split_options("yes/no/maybe") == ["yes", "no", "maybe"]
    assert grade_ground_truth("I know", gt(f="validate_choice", options="I know or I don't know"))
    assert not grade_ground_truth("Zebra", gt(f="validate_choice", options="I know or I don't know"))
    assert grade_ground_truth("anything", gt(f="validate_json_format")) and not grade_ground_truth("", gt(f="validate_title"))


def test_label_grader_prefers_ground_truth():
    """Checks that the label grader uses an instruction item's ground_truth when it has one and the old regex otherwise.
    Guards against: the relabel still grading instructions with the regex, or old labels changing meaning."""
    from flotilla.label_loop import grade
    gt = json.dumps({"func_name": "validate_lowercase"})
    assert grade({"task_type": "instruction", "task": "anything", "ground_truth": gt}, "all lower case")
    assert not grade({"task_type": "instruction", "task": "anything", "ground_truth": gt}, "Not Lower")
    assert grade({"task_type": "instruction", "task": "Write a note."}, "Not Lower")   # no rule found by the regex


def test_rule_list_parsing_drops_unknown_ids_and_bad_arguments():
    """Checks that constraint_check v2 keeps listed rules whose ID and arguments build an official checker, drops unknown IDs and bad arguments, and checks a draft with the official checkers.
    Guards against: a hallucinated rule ID or argument crashing the check or being counted as met."""
    pytest.importorskip("lm_eval")
    from flotilla.ifeval_rules import check_rules, parse_rules
    reply = ('```json\n{"rules": [{"instruction_id": "change_case:english_lowercase", "kwargs": {}}, '
             '{"instruction_id": "made:up", "kwargs": {}}, '
             '{"instruction_id": "detectable_format:number_bullet_lists", "kwargs": {"num_bullets": 3}}]}\n```')
    r = parse_rules(reply)
    assert r["parsed"] and [x["instruction_id"] for x in r["rules"]] == ["change_case:english_lowercase",
                                                                         "detectable_format:number_bullet_lists"]
    assert r["dropped"][0]["why"] == "unknown instruction_id"
    ok = check_rules(r["rules"], "* one\n* two\n* three")
    bad = check_rules(r["rules"], "* One\n* two")
    assert ok["ok"] and not bad["ok"] and bad["detail"] == "0/2 rules met"
    assert parse_rules("no json")["parsed"] is False
