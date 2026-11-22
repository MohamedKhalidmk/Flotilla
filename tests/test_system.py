from flotilla import system


def test_parse_final_takes_last_json_block():
    """Checks that parse_final takes the answer and confidence from the last JSON block, and gives None when there is no JSON.
    Guards against: an early draft answer in the reasoning being taken as the final answer."""
    text = 'thinking {"final_answer": "3", "confidence": 0.2}\nmore thinking\n```json\n{"final_answer": "4", "confidence": 0.9, "sources": []}\n```'
    assert system.parse_final(text) == ("4", 0.9)
    assert system.parse_final("no json here") == (None, None)


def test_vote_math_groups_equivalent_answers():
    """Checks that the maths vote counts 1/2, 0.5 and the LaTeX fraction for one half as the same answer.
    Guards against: equal maths answers written in different forms splitting the vote."""
    v = system.vote("math", ["1/2", "0.5", "\\frac{1}{2}", "3", None])
    assert v["winner"] in ("1/2", "0.5", "\\frac{1}{2}") and max(v["counts"].values()) == 3


def test_vote_letters_and_code():
    """Checks that the letter vote ignores case and that the code vote picks the program that passes the public tests.
    Guards against: b and B being counted as different answers, or a failing program winning the code vote."""
    assert system.vote("science_mc", ["b", "B", "C"])["winner"].upper() == "B"
    tests = [{"input": "2 3", "output": "5"}]
    v = system.vote("code", ["print(0)", "a,b=map(int,input().split());print(a+b)"], tests)
    assert v["winner"].startswith("a,b")


def test_verifier_deterministic_checks():
    """Checks that the verifier accepts a parseable maths answer and rejects a missing answer, an out-of-range letter, and an answer breaking a lowercase rule.
    Guards against: a verifier that accepts option E when the question only has A to D."""
    assert system.verify("x", "math", "\\frac{1}{2}")["verdict"] == "accept"
    assert system.verify("x", "math", None)["verdict"] == "reject"
    assert system.verify("q", "science_mc", "E", options=["a", "b", "c", "d"])["verdict"] == "reject"
    assert system.verify("Answer in all lowercase letters.", "instruction", "Hello")["verdict"] == "reject"


def test_retry_message_says_wrong_and_gives_reason():
    """Checks that the retry message says the answer was wrong, repeats it, and gives the verifier's reason, or says no answer could be parsed.
    Guards against: a retry that does not tell the model why its answer was rejected."""
    v = system.verify("Answer in all lowercase letters.", "instruction", "Hello World")
    msg = system.retry_message("v2", "Hello World", v)
    assert msg.startswith("Your previous answer was wrong")
    assert "Previous answer: Hello World" in msg and "constraints" in msg and v["reason"] in msg
    assert "(no parseable final answer)" in system.retry_message("v2", None, {"checks": [], "reason": "no final answer"})


def test_solver_messages_include_task_type_addition():
    """Checks that the maths solver system prompt includes the sympy addition and that the user message is the task.
    Guards against: maths questions sent without the instruction to use sympy."""
    m = system.solver_messages("What is 2+2?", "math", "v1")
    assert m[0]["role"] == "system" and "sympy" in m[0]["content"] and m[1]["content"] == "What is 2+2?"


def test_valid_option_counts_options_in_the_question():
    """Checks that n_options counts the lettered lines in the question up to J, uses the options list when given, and falls back to four.
    Guards against: a verifier that accepts option K when the question only has A to J."""
    from flotilla.system import n_options, verify
    task = "Which?\n\nA. one\nB. two\nC. three\nD. four\nE. five\nF. six\nG. seven\nH. eight\nI. nine\nJ. ten"
    assert n_options(task, None) == 10
    assert verify(task, "science_mc", "I")["verdict"] == "accept"
    assert verify(task, "science_mc", "K")["verdict"] == "reject"
    assert n_options("Pick one.\n(A) x\n(B) y\n(C) z", None) == 3
    assert n_options("no lettered lines", None) == 4
    assert n_options(task, ["a", "b"]) == 2


def _fake_create(replies):
    """A stand-in for system._create: the checker call (thinking off, system prompt from verifier.v2) gets the next
    checker reply; solver calls get the next solver reply. Records every call's extra_body and messages."""
    from types import SimpleNamespace as NS
    calls = []

    async def create(name, srv, client, msgs, cfg, temperature, **extra):
        role = "check" if name.endswith(":llm_check") else "solve"
        calls.append({"role": role, "srv": srv, "msgs": msgs, "temperature": temperature})
        text = replies[role].pop(0)
        return NS(choices=[NS(message=NS(content=text, tool_calls=None, reasoning_content=None), finish_reason="stop")],
                  usage=NS(prompt_tokens=100, completion_tokens=10))
    return create, calls


def _run(item, cfg, replies, monkeypatch):
    import asyncio
    from flotilla.trace import Trace
    create, calls = _fake_create(replies)
    monkeypatch.setattr(system, "_create", create)
    monkeypatch.setattr(system, "client_for", lambda srv: None)
    tr = Trace(run_id="t", protocol_version="p", prompt_versions={}, benchmark="lme", item_id="1", split="dev")
    return asyncio.run(system.answer(item, {}, cfg, tr)), calls


def _cfg(**kw):
    srv = {"q": {"url": "u", "model": "m", "quant": "w4a16", "native_tools": True,
                 "request": {"extra_body": {"chat_template_kwargs": {"enable_thinking": True}}}}}
    return system.SystemConfig(servers=srv, solvers=["q"], tools=False, **kw)


def test_llm_check_prompt_comes_from_verifier_v2():
    """Checks that the LLM check messages come from verifier.v2 and that parse_llm_verdict reads the verdict and reason, or gives None without JSON.
    Guards against: the checker using a different prompt than verifier.v2, or a reply without JSON read as a verdict."""
    m = system.llm_check_messages("v2", "History...\nQuestion: what did I buy?", "a bike")
    assert m[0]["content"].startswith("Decide whether the answer below is acceptable") and '"verdict"' in m[0]["content"]
    assert m[1]["content"] == "Task: History...\nQuestion: what did I buy?\nAnswer: a bike"
    assert system.parse_llm_verdict('x {"verdict": "Reject", "checks": [], "reason": "wrong date"}') == \
        {"verdict": "reject", "reason": "wrong date"}
    assert system.parse_llm_verdict("no json") is None


def test_llm_check_reject_drives_one_retry(monkeypatch):
    """Checks that an LLM check reject, run with thinking off at temperature 0, leads to one retry whose answer is kept and counted in compute.
    Guards against: the checker's model call being left out of the compute count, or the rejected first answer kept as final."""
    item = {"item_id": "1", "task": "History...\nQuestion: what did I buy?", "task_type": "longmemeval"}
    replies = {"solve": ['{"final_answer": "a car", "confidence": 0.5}', '{"final_answer": "a bike", "confidence": 0.8}'],
               "check": ['{"verdict": "reject", "checks": [], "reason": "the history says a bike"}']}
    tr, calls = _run(item, _cfg(llm_verify=True), replies, monkeypatch)
    check = [c for c in calls if c["role"] == "check"]
    assert len(check) == 1 and check[0]["temperature"] == 0.0
    assert check[0]["srv"]["request"]["extra_body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert check[0]["msgs"][1]["content"].endswith("Answer: a car")
    a1, a2 = tr.verifier["attempts"]
    assert a1["verdict"] == "reject" and a1["checks"][0]["name"] == "llm_check" and "a bike" in a1["reason"]
    assert "Your previous answer was wrong" in a2["retry_message"] and tr.final_answer == "a bike"
    assert any(m["name"] == "q:llm_check" for m in tr.models)  # the checker's call is counted in compute


def test_llm_check_off_or_exact_check_present_means_no_checker_call(monkeypatch):
    """Checks that no LLM check call is made when llm_verify is off, or when the task type already has an exact check, as maths does.
    Guards against: paying for an LLM check on maths answers that the exact check already verifies."""
    item = {"item_id": "1", "task": "History...\nQuestion: what did I buy?", "task_type": "longmemeval"}
    tr, calls = _run(item, _cfg(), {"solve": ['{"final_answer": "a car"}'], "check": []}, monkeypatch)
    assert [c["role"] for c in calls] == ["solve"] and tr.final_answer == "a car"
    math = {"item_id": "2", "task": "1+1?", "task_type": "math"}
    tr, calls = _run(math, _cfg(llm_verify=True), {"solve": ['{"final_answer": "2"}'], "check": []}, monkeypatch)
    assert [c["role"] for c in calls] == ["solve"] and tr.verifier["verdict"] == "accept"


def test_llm_check_unparseable_reply_accepts(monkeypatch):
    """Checks that an LLM check reply with no readable verdict accepts the answer without a retry.
    Guards against: a garbled checker reply forcing a retry of an answer that was fine."""
    item = {"item_id": "1", "task": "Q?", "task_type": "longmemeval"}
    tr, _ = _run(item, _cfg(llm_verify=True), {"solve": ['{"final_answer": "x"}'], "check": ["I think it is fine."]},
                 monkeypatch)
    assert tr.verifier["verdict"] == "accept" and len(tr.verifier["attempts"]) == 1 and tr.final_answer == "x"


def test_constraint_check_on_memory_reads_only_the_question():
    """Checks that constraint_check on a LongMemEval history or a GRAFT memory block finds no constraints from old sessions, while an instruction task keeps its own.
    Guards against: "add a P.S." or "at least 500 words" from an old chat session failing a memory answer (run-04 Vote+Tools)."""
    from flotilla.longmemeval import history_prompt
    from flotilla.memory_route import MEMORY_HEADER, MEMORY_RULE
    item = {"question": "Where did I get my guitar serviced?", "question_date": "2023/06/01 (Thu) 10:00",
            "sessions": [{"session_id": "s1", "date": "2023/05/01 (Mon) 09:00", "turns": [
                {"role": "user", "content": "Write a blog post of at least 500 words and end it with a P.S."},
                {"role": "assistant", "content": "Sure. P.S. thanks"}]}]}
    msgs = [{"role": "system", "content": "x"}, {"role": "user", "content": history_prompt(item)}]
    assert system._run_tool("constraint_check", "Rhythm Central on Main St", msgs)["output"] == []
    block = f"{MEMORY_HEADER}:\n1. user asked: end every reply with a P.S.\n\nCurrent date: 2023/06/01\nQuestion: Where?\n\n{MEMORY_RULE}"
    assert system.constraint_source(block) == "Question: Where?"
    assert system._run_tool("constraint_check", "x", [{"role": "user", "content": block}])["output"] == []
    own = [{"role": "user", "content": "Write a note. End it with a P.S."}]
    r = system._run_tool("constraint_check", "A note.", own)
    assert r["output"] and not r["ok"]
