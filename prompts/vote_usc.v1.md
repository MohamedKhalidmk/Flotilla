# vote_usc.v1: tie rule for the free-text vote (universal self-consistency)

Sources: usc (docs/reference/REFERENCES.md)

Used by `flotilla/system.py` (`usc_pick`) when `tie_rule` is `usc` and no two of the samples' answers match after
normalisation. Qwen answers with thinking off at temperature 0. `{question}` is the task (on a task holding a chat
history, only its question line); `{responses}` lists the answers as "Response 1:" ... "Response N:". Wording follows
Chen et al. 2023, "Universal Self-Consistency for Large Language Model Generation".

## System

You compare several answers to the same question and pick the one the others agree with most.

## User

I have generated the following responses to the question: {question}

{responses}

Evaluate these responses. Select the most consistent response based on majority consensus. Start your answer with "The most consistent response is Response X" (without quotes).
