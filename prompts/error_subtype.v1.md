# error_subtype.v1: sub-type of a reasoning error (PROTOCOL.md 7.1, stage reasoning_error)

Sources: original (docs/reference/REFERENCES.md)

Used by `flotilla/error_subtypes.py` on Claude Haiku 5.5 (thinking off, max_tokens 200), once per trace whose error
stage is reasoning_error. `{question}`, `{gold}` and `{answer}` are the question, its gold answer (or grading rubric)
and the route's final answer; `{facts}` is the list of facts a Memory route showed, or a note that the route read the
whole history (base routes on memory questions) or had no memory (other questions). The reply is one JSON object.

## User

You are auditing a wrong answer. Pick the one sub-type that best explains why the answer is wrong.

- partial_answer: the answer is right as far as it goes but leaves out part of what the gold requires (an item, a unit, a date, the second part of the question).
- calculation_error: the answer uses the right information but gets a count, a sum, a date difference or another computation wrong.
- outdated_fact: the answer gives an older value that was later updated (the gold is the newer value).
- abstention_error: the answer says the information is not available when the gold gives an answer, or gives an answer when the gold says the question cannot be answered.
- misread_question: the answer addresses a different question than the one asked (wrong entity, wrong event, wrong quantity, wrong format asked for).
- other: none of the above (for example a plainly wrong fact, a guess, or a rule of the task broken).

Question:
{question}

Gold answer (or grading rubric):
{gold}

Wrong answer:
{answer}

Facts the system was shown:
{facts}

Reply with one JSON object and nothing else:
{"subtype": "partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other", "reason": "one short sentence"}
