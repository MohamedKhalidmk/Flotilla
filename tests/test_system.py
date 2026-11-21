from flotilla import system


def test_parse_final_takes_last_json_block():
    text = 'thinking {"final_answer": "3", "confidence": 0.2}\nmore thinking\n```json\n{"final_answer": "4", "confidence": 0.9, "sources": []}\n```'
    assert system.parse_final(text) == ("4", 0.9)
    assert system.parse_final("no json here") == (None, None)


def test_vote_math_groups_equivalent_answers():
    v = system.vote("math", ["1/2", "0.5", "\\frac{1}{2}", "3", None])
    assert v["winner"] in ("1/2", "0.5", "\\frac{1}{2}") and max(v["counts"].values()) == 3


def test_vote_letters_and_code():
    assert system.vote("science_mc", ["b", "B", "C"])["winner"].upper() == "B"
    tests = [{"input": "2 3", "output": "5"}]
    v = system.vote("code", ["print(0)", "a,b=map(int,input().split());print(a+b)"], tests)
    assert v["winner"].startswith("a,b")


def test_verifier_deterministic_checks():
    assert system.verify("x", "math", "\\frac{1}{2}")["verdict"] == "accept"
    assert system.verify("x", "math", None)["verdict"] == "reject"
    assert system.verify("q", "science_mc", "E", options=["a", "b", "c", "d"])["verdict"] == "reject"
    assert system.verify("Answer in all lowercase letters.", "instruction", "Hello")["verdict"] == "reject"


def test_retry_message_says_wrong_and_gives_reason():
    v = system.verify("Answer in all lowercase letters.", "instruction", "Hello World")
    msg = system.retry_message("v2", "Hello World", v)
    assert msg.startswith("Your previous answer was wrong")
    assert "Previous answer: Hello World" in msg and "constraints" in msg and v["reason"] in msg
    assert "(no parseable final answer)" in system.retry_message("v2", None, {"checks": [], "reason": "no final answer"})


def test_solver_messages_include_task_type_addition():
    m = system.solver_messages("What is 2+2?", "math", "v1")
    assert m[0]["role"] == "system" and "sympy" in m[0]["content"] and m[1]["content"] == "What is 2+2?"


def test_valid_option_counts_options_in_the_question():
    from flotilla.system import n_options, verify
    task = "Which?\n\nA. one\nB. two\nC. three\nD. four\nE. five\nF. six\nG. seven\nH. eight\nI. nine\nJ. ten"
    assert n_options(task, None) == 10
    assert verify(task, "science_mc", "I")["verdict"] == "accept"
    assert verify(task, "science_mc", "K")["verdict"] == "reject"
    assert n_options("Pick one.\n(A) x\n(B) y\n(C) z", None) == 3
    assert n_options("no lettered lines", None) == 4
    assert n_options(task, ["a", "b"]) == 2
