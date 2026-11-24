# self_check.v1: check and revise messages of the Self-Check route (F40)

Sources: critic (docs/reference/REFERENCES.md)

Used by `flotilla/core/system.py` (`self_check`): after the first answer, up to 3 rounds of a check (Qwen must call
python_exec; thinking off, temperature 0) and, when the check does not pass, a revision. `{question}` is the task
(only its question line when it holds a chat history), `{answer}` the current answer, `{program}` and `{output}` the
check program and everything it printed or raised.

## Check system

You check an answer by running code. Call python_exec with one program that checks the answer independently: compute it
another way, substitute it back, test it against the rules the task states, or run it on the examples the task gives.
The program must end by printing exactly one line, either CHECK PASS or CHECK FAIL: <reason>. If nothing in the answer
can be checked by computation, the program prints CHECK PASS: nothing to compute.

## Check user

Task:
{question}

Answer to check:
{answer}

## Revise user

Your answer was checked by running this program:
```python
{program}
```
It printed:
```
{output}
```
The check did not pass. Work out the right answer to the task again, then give it in the usual JSON block.

Task:
{question}

Your previous answer:
{answer}
