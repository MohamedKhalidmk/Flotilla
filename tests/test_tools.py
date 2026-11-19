from flotilla import tools


def test_sympy_check_equivalent_forms():
    assert tools.sympy_check("\\frac{1}{2}", "0.5")["ok"]
    assert tools.sympy_check("\\boxed{2\\sqrt{2}}", "\\sqrt{8}")["ok"]
    assert not tools.sympy_check("3", "4")["ok"]


def test_python_exec_and_public_tests():
    r = tools.python_exec("print(sum(map(int, input().split())))", "2 3")
    assert r["ok"] and r["output"].strip() == "5"
    assert tools.python_exec("while True: pass", timeout_s=1)["detail"] == "timeout"
    t = tools.run_public_tests("a,b=map(int,input().split());print(a*b)", [{"input": "2 3", "output": "6"}, {"input": "4 5", "output": "20"}])
    assert t["ok"] and t["output"] == "2/2"


def test_constraint_check_detects_and_checks():
    task = "Write a poem about rain in all lowercase letters. Use at least 20 words and do not use any commas."
    good = "the rain comes down on the quiet town and every roof sings a soft song while the night grows long and the streets shine bright"
    bad = "The rain, it falls."
    assert tools.constraint_check(task, good)["ok"]
    r = tools.constraint_check(task, bad)
    assert not r["ok"] and r["detail"].startswith("0/3")


def test_constraint_check_json_and_ending():
    task = 'Wrap your entire output in JSON format. End your response with the exact phrase "Is there anything else?"'
    assert not tools.constraint_check(task, '{"a": 1}')["ok"]          # json ok, ending missing
    assert tools.constraint_check("Wrap your entire output in JSON format.", '```json\n{"a": 1}\n```')["ok"]
