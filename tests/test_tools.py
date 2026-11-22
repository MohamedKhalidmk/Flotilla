from flotilla import tools


def test_sympy_check_equivalent_forms():
    """Checks that sympy_check treats one half and 0.5, and a boxed 2 times root 2 and root 8, as equal, and 3 and 4 as different.
    Guards against: a right maths answer marked wrong because it is written in another form."""
    assert tools.sympy_check("\\frac{1}{2}", "0.5")["ok"]
    assert tools.sympy_check("\\boxed{2\\sqrt{2}}", "\\sqrt{8}")["ok"]
    assert not tools.sympy_check("3", "4")["ok"]


def test_python_exec_and_public_tests():
    """Checks that python_exec runs code on stdin, stops an endless loop with a timeout, and that run_public_tests reports 2/2 passes.
    Guards against: an endless loop in generated code hanging the run."""
    r = tools.python_exec("print(sum(map(int, input().split())))", "2 3")
    assert r["ok"] and r["output"].strip() == "5"
    assert tools.python_exec("while True: pass", timeout_s=1)["detail"] == "timeout"
    t = tools.run_public_tests("a,b=map(int,input().split());print(a*b)", [{"input": "2 3", "output": "6"}, {"input": "4 5", "output": "20"}])
    assert t["ok"] and t["output"] == "2/2"


def test_constraint_check_detects_and_checks():
    """Checks that constraint_check finds the lowercase, word count and no-comma rules, passes an answer meeting them, and fails one breaking all.
    Guards against: an instruction answer passing while it breaks the task's lowercase, length or comma rules."""
    task = "Write a poem about rain in all lowercase letters. Use at least 20 words and do not use any commas."
    good = "the rain comes down on the quiet town and every roof sings a soft song while the night grows long and the streets shine bright"
    bad = "The rain, it falls."
    assert tools.constraint_check(task, good)["ok"]
    r = tools.constraint_check(task, bad)
    assert not r["ok"] and r["detail"].startswith("0/3")


def test_constraint_check_json_and_ending():
    """Checks that a JSON answer missing the required ending phrase fails, and that JSON inside a code fence passes the JSON rule.
    Guards against: a JSON answer in a code fence being rejected as not JSON."""
    task = 'Wrap your entire output in JSON format. End your response with the exact phrase "Is there anything else?"'
    assert not tools.constraint_check(task, '{"a": 1}')["ok"]          # json ok, ending missing
    assert tools.constraint_check("Wrap your entire output in JSON format.", '```json\n{"a": 1}\n```')["ok"]


# 2026-11-20 hand check of test-04 failures: each case below was a correct answer the checks failed.

def test_forbidden_keywords_are_not_required():
    """Checks that keywords the task forbids fail the answer when present and are not required when absent.
    Guards against: a correct answer rejected for not containing words it was told to leave out."""
    from flotilla.tools import constraint_check
    task = "Do not include keywords laborage, narcomatous, lampful in the response. What is the sentiment?"
    assert constraint_check(task, "negative")["ok"]
    assert not constraint_check(task, "negative, a lampful of it")["ok"]


def test_postscript_uses_the_asked_phrase_after_the_main_text():
    """Checks that the postscript rule looks for the phrase the task asks for, such as Addendum or PS, after some main text.
    Guards against: a postscript starting with Addendum being rejected, or a postscript with no main text before it being accepted."""
    from flotilla.tools import constraint_check
    task = "At the end of your response, please explicitly add a postscript starting with Addendum:\nQuestion?"
    assert constraint_check(task, "BLEU and ROUGE. Addendum: also BERTScore.")["ok"]
    assert not constraint_check(task, "Addendum: BLEU and ROUGE.")["ok"]
    task2 = "At the end of your response, please explicitly add a postscript starting with PS: Creatively image a question"
    assert constraint_check(task2, "it is not possible to tell\nPS: Question: ...")["ok"]


def test_markdown_divider_paragraphs():
    """Checks that paragraphs split by the markdown divider * * * are counted against the asked number.
    Guards against: a two-paragraph answer with a * * * divider being counted as one paragraph."""
    from flotilla.tools import constraint_check
    task = "Your response should contain 2 paragraphs. You separate paragraphs using the markdown divider: * * *"
    assert constraint_check(task, "First part.\n\n* * *\n\nSecond part.")["ok"]
    assert not constraint_check(task, "Only one part.")["ok"]


def test_capital_word_limit_is_a_count():
    """Checks that the all-capitals word limit counts capitalised words against the asked maximum.
    Guards against: an answer with one capitalised word rejected under an at most 2 times limit."""
    from flotilla.tools import constraint_check
    task = "In your response, words with all capital letters should appear at most 2 times. Explain."
    assert constraint_check(task, "This is NOT shouting.")["ok"]
    assert not constraint_check(task, "THIS IS ALL SHOUTING")["ok"]


def test_whole_output_json_is_met_by_the_loop():
    """Checks that the whole-output JSON rule passes only when the loop wraps the answer, and that a JSON array request does not block bullets.
    Guards against: a correct answer rejected as not JSON when the Flotilla loop already wraps its output in JSON."""
    from flotilla.tools import constraint_check
    task = "Entire output should be wrapped in JSON format. Where is a basketball court likely to be outdoors?"
    assert constraint_check(task, "park", loop_wrapped=True)["ok"]
    assert not constraint_check(task, "park")["ok"]
    bullets = ("Your answer must contain exactly 2 bullet points. Please format your results as a JSON array.")
    assert constraint_check(bullets, "* a\n* b")["ok"]


def test_float_outputs_within_tolerance():
    """Checks that same_tokens matches floats that differ only in the last digits and still tells apart different numbers and integers.
    Guards against: a correct code output failing a test over float rounding in the 15th digit."""
    from flotilla.tools import same_tokens
    assert same_tokens(["215.913355350494385"], ["215.913355350494384765625"])
    assert same_tokens(["0.749999999999999"], ["0.7500000000000000"])
    assert not same_tokens(["0.74"], ["0.75"])
    assert not same_tokens(["12"], ["13"])


def test_math_format_matches():
    """Checks that the maths grader accepts answers equal to the gold without dollar signs or LaTeX text, and the right letter in a lettered question.
    Guards against: answering C, where option C is 0.20, being graded wrong against a gold of 0.20."""
    from flotilla.label_loop import grade
    assert grade({"task_type": "math", "task": "price?", "gold": "\\$3.50"}, "3.50")
    assert grade({"task_type": "math", "task": "list", "gold": "\\text{Softball, Kickball, Picnic}"}, "Softball, Kickball, Picnic")
    mc = "Which is closest?\n\nA. 0.10\n\nB. 0.15\n\nC. 0.20\n\nD. 0.25\n\n(Type the letter that corresponds to your answer.)"
    assert grade({"task_type": "math", "task": mc, "gold": "0.20"}, "C")
    assert not grade({"task_type": "math", "task": mc, "gold": "0.20"}, "B")
    geo = "The area is:\n$\\textbf{(A)}\\ \\frac{bx}{h}(h-x)\\qquad \\textbf{(B)}\\ \\frac{hx}{b}(b-x)$"
    assert grade({"task_type": "math", "task": geo, "gold": "\\frac{bx}{h}(h-x)"}, "A")


def test_math_unicode_units_and_thousands():
    """Checks that the maths grader accepts Unicode infinity, union and root signs, thousands separators, and a unit or short phrase around the number.
    Guards against: 852 BC graded wrong against a gold of 852, or 650 graded right against 670."""
    from flotilla.label_loop import grade
    g = lambda gold, ans: grade({"task_type": "math", "task": "q", "gold": gold}, ans)
    assert g("(-\\infty,-2)\\cup(-2, 2)\\cup(2,\\infty)", "(-∞, -2) ∪ (-2, 2) ∪ (2, ∞)")
    assert g("(-\\sqrt{2}, 0, \\sqrt{2})", "(-√2, 0, √2)")
    assert g("\\$23{,}000", "23000")
    assert g("\\$3.50", "3.5")
    assert g("852", "852 BC")
    assert g("4", "Brad, by 4 books")
    assert not g("4", "Brad, by 4 books out of 26")
    assert not g("670", "650")
