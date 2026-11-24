# forced_tool.v1: wording appended to the solver's system message on a forced-tool route (F37-F39)

Sources: retool (docs/reference/REFERENCES.md)

Used by `flotilla/core/system.py` when `forced_tool` is set; the first call also sets tool_choice to that tool by name.
One section per tool; the section title is the tool's name.

## python_exec

You must use python_exec on this task: run code for every calculation, check and test, read each result before you go
on, and keep thinking after it. If the code fails, read the error, fix the code and run it again.

## sympy

You must use sympy on this task: check the expression or equation your answer rests on with sympy before you give the
final answer.

## constraint_check

You must use constraint_check on this task: write a draft answer, check it with constraint_check, fix whatever rule it
reports as failed, and check again before you give the final answer.
