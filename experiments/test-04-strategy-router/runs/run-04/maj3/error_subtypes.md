# Sub-types of reasoning_error on run-04-lme-maj3 (Claude Haiku 5.5, prompts/error_subtype.v1.md)

1120 traces (every reasoning_error after the fact-level retag). Hand check of 50: 36 agree (72%); 43 (86%) if a count that misses items may be either partial_answer or calculation_error (the prompt allows both). 57 replies (5%) were cut at the 200-token cap before their JSON (unparsed).

## Per route

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 217 | 20 | 60 | 7 | 21 | 8 | 88 | 13 |
| tools | 180 | 20 | 47 | 3 | 14 | 7 | 77 | 12 |
| deep | 107 | 10 | 29 | 4 | 12 |  | 44 | 8 |
| deep_tools | 125 | 14 | 32 | 4 | 10 | 3 | 48 | 14 |
| vote | 63 | 5 | 14 | 3 | 11 | 3 | 23 | 4 |
| vote_tools | 82 | 11 | 14 | 2 | 14 | 3 | 32 | 6 |
| memory | 89 | 16 |  | 5 | 50 | 5 | 13 |  |
| memory_deep | 88 | 17 | 2 | 4 | 57 | 5 | 3 |  |
| deep_tools_memory | 84 | 19 | 2 | 5 | 47 | 5 | 6 |  |
| vote_memory | 85 | 14 | 2 | 3 | 54 | 4 | 8 |  |

## code

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 7 |  |  |  |  |  | 6 | 1 |
| tools | 6 |  |  |  |  |  | 4 | 2 |
| deep | 7 |  |  |  |  |  | 7 |  |
| deep_tools | 1 |  |  |  |  |  | 1 |  |
| vote_tools | 1 |  |  |  |  |  | 1 |  |

## instruction

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 33 | 1 |  |  | 1 | 3 | 27 | 1 |
| tools | 18 | 1 |  |  |  |  | 17 |  |
| deep | 3 |  |  |  |  |  | 3 |  |
| deep_tools | 15 |  |  |  |  | 1 | 14 |  |
| vote | 4 |  |  |  |  |  | 4 |  |
| vote_tools | 9 | 1 |  |  |  | 1 | 7 |  |

## math

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 61 | 2 | 35 |  |  | 1 | 14 | 9 |
| tools | 46 |  | 26 |  |  | 1 | 12 | 7 |
| deep | 20 | 1 | 9 |  | 1 |  | 2 | 7 |
| deep_tools | 30 |  | 13 |  |  | 1 | 4 | 12 |
| vote | 12 |  | 6 |  | 1 | 1 |  | 4 |
| vote_tools | 10 |  | 5 |  |  |  | 1 | 4 |

## memory

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 96 | 17 | 15 | 7 | 20 | 4 | 33 |  |
| tools | 83 | 18 | 10 | 3 | 14 | 5 | 33 |  |
| deep | 59 | 9 | 11 | 4 | 11 |  | 24 |  |
| deep_tools | 59 | 13 | 12 | 4 | 10 | 1 | 19 |  |
| vote | 38 | 5 | 4 | 3 | 10 | 2 | 14 |  |
| vote_tools | 52 | 9 | 6 | 2 | 14 | 2 | 18 | 1 |
| memory | 89 | 16 |  | 5 | 50 | 5 | 13 |  |
| memory_deep | 88 | 17 | 2 | 4 | 57 | 5 | 3 |  |
| deep_tools_memory | 84 | 19 | 2 | 5 | 47 | 5 | 6 |  |
| vote_memory | 85 | 14 | 2 | 3 | 54 | 4 | 8 |  |

## science_mc

| route | n | partial_answer | calculation_error | outdated_fact | abstention_error | misread_question | other | unparsed |
|---|---|---|---|---|---|---|---|---|
| fast | 20 |  | 10 |  |  |  | 8 | 2 |
| tools | 27 | 1 | 11 |  |  | 1 | 11 | 3 |
| deep | 18 |  | 9 |  |  |  | 8 | 1 |
| deep_tools | 20 | 1 | 7 |  |  |  | 10 | 2 |
| vote | 9 |  | 4 |  |  |  | 5 |  |
| vote_tools | 10 | 1 | 3 |  |  |  | 5 | 1 |

## All routes

partial_answer 146, calculation_error 202, outdated_fact 40, abstention_error 290, misread_question 43, other 342, unparsed 57

## Hand check (50, seeded 20261122; labels in error_subtypes_hand50.json)

36 of 50 agree. The disagreements: 7 undercounts ("2" where the gold is 3) that Haiku calls partial_answer and the
hand check calculation_error (the prompt allows both; v2 should say which); 3 wrong counts or computations Haiku calls
other; 1 personalised-advice miss Haiku calls misread_question; 1 answer missing its required explanation and
postscript (Haiku partial_answer, hand other); 1 unparsed reply; and 2 answers that abstained correctly but were judged
wrong (lme-f685340e_abs on Vote and Deep: judge errors, which no sub-type covers).

## Reading it

- Memory routes: abstention_error dominates (47-57 of 84-89): with the facts in hand, Qwen says the memory does not
  hold the answer, often on preference questions where the rubric wants a personalised suggestion, and on counts it
  cannot complete. partial_answer comes second (missed items).
- Base and pool routes: other (wrong facts, wrong multiple-choice picks, broken instruction rules) and
  calculation_error (maths, counts) lead; outdated_fact is rare everywhere (2-7 per route).
- Prompt v2 (not run): count misses go to partial_answer; a judge_error sub-type for answers that are right; a larger
  reply cap (the 57 unparsed replies reasoned at length before their JSON).
