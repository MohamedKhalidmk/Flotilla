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


# 2026-11-20 hand check of test-04 failures: each case below was a correct answer the checks failed.

def test_forbidden_keywords_are_not_required():
    from flotilla.tools import constraint_check
    task = "Do not include keywords laborage, narcomatous, lampful in the response. What is the sentiment?"
    assert constraint_check(task, "negative")["ok"]
    assert not constraint_check(task, "negative, a lampful of it")["ok"]


def test_postscript_uses_the_asked_phrase_after_the_main_text():
    from flotilla.tools import constraint_check
    task = "At the end of your response, please explicitly add a postscript starting with Addendum:\nQuestion?"
    assert constraint_check(task, "BLEU and ROUGE. Addendum: also BERTScore.")["ok"]
    assert not constraint_check(task, "Addendum: BLEU and ROUGE.")["ok"]
    task2 = "At the end of your response, please explicitly add a postscript starting with PS: Creatively image a question"
    assert constraint_check(task2, "it is not possible to tell\nPS: Question: ...")["ok"]


def test_markdown_divider_paragraphs():
    from flotilla.tools import constraint_check
    task = "Your response should contain 2 paragraphs. You separate paragraphs using the markdown divider: * * *"
    assert constraint_check(task, "First part.\n\n* * *\n\nSecond part.")["ok"]
    assert not constraint_check(task, "Only one part.")["ok"]


def test_capital_word_limit_is_a_count():
    from flotilla.tools import constraint_check
    task = "In your response, words with all capital letters should appear at most 2 times. Explain."
    assert constraint_check(task, "This is NOT shouting.")["ok"]
    assert not constraint_check(task, "THIS IS ALL SHOUTING")["ok"]


def test_whole_output_json_is_met_by_the_loop():
    from flotilla.tools import constraint_check
    task = "Entire output should be wrapped in JSON format. Where is a basketball court likely to be outdoors?"
    assert constraint_check(task, "park", loop_wrapped=True)["ok"]
    assert not constraint_check(task, "park")["ok"]
    bullets = ("Your answer must contain exactly 2 bullet points. Please format your results as a JSON array.")
    assert constraint_check(bullets, "* a\n* b")["ok"]


def test_float_outputs_within_tolerance():
    from flotilla.tools import same_tokens
    assert same_tokens(["215.913355350494385"], ["215.913355350494384765625"])
    assert same_tokens(["0.749999999999999"], ["0.7500000000000000"])
    assert not same_tokens(["0.74"], ["0.75"])
    assert not same_tokens(["12"], ["13"])


def test_math_format_matches():
    from flotilla.label_loop import grade
    assert grade({"task_type": "math", "task": "price?", "gold": "\\$3.50"}, "3.50")
    assert grade({"task_type": "math", "task": "list", "gold": "\\text{Softball, Kickball, Picnic}"}, "Softball, Kickball, Picnic")
    mc = "Which is closest?\n\nA. 0.10\n\nB. 0.15\n\nC. 0.20\n\nD. 0.25\n\n(Type the letter that corresponds to your answer.)"
    assert grade({"task_type": "math", "task": mc, "gold": "0.20"}, "C")
    assert not grade({"task_type": "math", "task": mc, "gold": "0.20"}, "B")
    geo = "The area is:\n$\\textbf{(A)}\\ \\frac{bx}{h}(h-x)\\qquad \\textbf{(B)}\\ \\frac{hx}{b}(b-x)$"
    assert grade({"task_type": "math", "task": geo, "gold": "\\frac{bx}{h}(h-x)"}, "A")
