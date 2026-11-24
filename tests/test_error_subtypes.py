from flotilla.research import error_subtypes as es


def test_subtype_reply_parsing_never_guesses():
    """Checks that the classifier reply's JSON gives the sub-type and reason, and that an unknown or missing sub-type is recorded as unparsed.
    Guards against: a malformed Haiku reply silently counted as "other" or as a real sub-type."""
    assert es.parse_subtype('{"subtype": "calculation_error", "reason": "81 days is 11 weeks"}')["subtype"] == "calculation_error"
    assert es.parse_subtype('x {"subtype": "Outdated_Fact", "reason": "r"}')["subtype"] == "outdated_fact"
    assert es.parse_subtype('{"subtype": "laziness"}')["subtype"] == "unparsed"
    assert es.parse_subtype("no json")["subtype"] == "unparsed"


def test_subtype_prompt_shows_question_gold_answer_and_facts():
    """Checks that the fixed prompt is filled with the question, gold, answer and facts, that long text is cut with a mark, and that code and instruction golds are described rather than left empty.
    Guards against: the classifier judging without the facts shown, or an empty gold on code and instruction questions."""
    p = es.subtype_prompt("How many weeks?", "15", "11 weeks", "user | recovered from | flu")
    assert "How many weeks?" in p and "Gold answer" in p and "11 weeks" in p and "recovered from" in p
    assert "{question}" not in p and "{facts}" not in p
    assert "more characters cut" in es.subtype_prompt("q" * 5000, "g", "a", "f")
    assert "hidden tests" in es.gold_text({"task_type": "code"})
    assert "P.S." in es.gold_text({"task_type": "instruction", "constraint": "add a P.S."})
