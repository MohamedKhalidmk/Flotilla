# Error stages on run-04-lme-maj3 (one stage per wrong answer, PROTOCOL.md 7.1)

13700 route answers tagged. Live stages (taggable without gold): timeout_or_oom, token_cap, format_parse_failure.

## Per route (all task types)

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 1950 | 236 |  |  | 18 | 1 |  |  |  |  | 217 |
| tools | 1950 | 191 |  | 1 | 10 |  |  |  |  |  | 180 |
| deep | 1950 | 128 |  | 13 | 8 |  |  |  |  |  | 107 |
| deep_tools | 1950 | 142 |  | 13 | 4 |  |  |  |  |  | 125 |
| vote | 1950 | 98 |  | 4 | 1 |  | 30 |  |  |  | 63 |
| vote_tools | 1950 | 120 |  |  |  |  | 38 |  |  |  | 82 |
| memory | 500 | 288 |  |  | 1 |  |  |  | 77 |  | 210 |
| memory_deep | 500 | 283 |  |  |  |  |  |  | 77 |  | 206 |
| deep_tools_memory | 500 | 277 |  |  |  |  |  |  | 77 |  | 200 |
| vote_memory | 500 | 280 |  |  |  |  | 6 |  | 77 |  | 197 |

## code

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 79 | 13 |  |  | 6 |  |  |  |  |  | 7 |
| tools | 79 | 7 |  |  | 1 |  |  |  |  |  | 6 |
| deep | 79 | 12 |  | 5 |  |  |  |  |  |  | 7 |
| deep_tools | 79 | 2 |  |  | 1 |  |  |  |  |  | 1 |
| vote | 79 | 7 |  | 1 |  |  | 6 |  |  |  |  |
| vote_tools | 79 | 1 |  |  |  |  |  |  |  |  | 1 |

## instruction

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 236 | 45 |  |  | 12 |  |  |  |  |  | 33 |
| tools | 236 | 25 |  | 1 | 6 |  |  |  |  |  | 18 |
| deep | 236 | 12 |  | 1 | 8 |  |  |  |  |  | 3 |
| deep_tools | 236 | 26 |  | 8 | 3 |  |  |  |  |  | 15 |
| vote | 236 | 6 |  |  | 1 |  | 1 |  |  |  | 4 |
| vote_tools | 236 | 16 |  |  |  |  | 7 |  |  |  | 9 |

## math

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 898 | 61 |  |  |  |  |  |  |  |  | 61 |
| tools | 898 | 49 |  |  | 3 |  |  |  |  |  | 46 |
| deep | 898 | 25 |  | 5 |  |  |  |  |  |  | 20 |
| deep_tools | 898 | 34 |  | 4 |  |  |  |  |  |  | 30 |
| vote | 898 | 19 |  | 2 |  |  | 5 |  |  |  | 12 |
| vote_tools | 898 | 19 |  |  |  |  | 9 |  |  |  | 10 |

## memory

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 500 | 96 |  |  |  |  |  |  |  |  | 96 |
| tools | 500 | 83 |  |  |  |  |  |  |  |  | 83 |
| deep | 500 | 59 |  |  |  |  |  |  |  |  | 59 |
| deep_tools | 500 | 59 |  |  |  |  |  |  |  |  | 59 |
| vote | 500 | 50 |  |  |  |  | 12 |  |  |  | 38 |
| vote_tools | 500 | 66 |  |  |  |  | 14 |  |  |  | 52 |
| memory | 500 | 288 |  |  | 1 |  |  |  | 77 |  | 210 |
| memory_deep | 500 | 283 |  |  |  |  |  |  | 77 |  | 206 |
| deep_tools_memory | 500 | 277 |  |  |  |  |  |  | 77 |  | 200 |
| vote_memory | 500 | 280 |  |  |  |  | 6 |  | 77 |  | 197 |

## science_mc

| route | answers | wrong | timeout_or_oom | token_cap | format_parse_failure | verifier_false_reject | vote_wrong | router_wrong_model | retrieval_miss | verifier_false_accept | reasoning_error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 237 | 21 |  |  |  | 1 |  |  |  |  | 20 |
| tools | 237 | 27 |  |  |  |  |  |  |  |  | 27 |
| deep | 237 | 20 |  | 2 |  |  |  |  |  |  | 18 |
| deep_tools | 237 | 21 |  | 1 |  |  |  |  |  |  | 20 |
| vote | 237 | 16 |  | 1 |  |  | 6 |  |  |  | 9 |
| vote_tools | 237 | 18 |  |  |  |  | 8 |  |  |  | 10 |

## Flags on wrong answers

retrieval_fallback 552, verifier_rejected 361, retry_used 361, samples_ungraded 310, vote_tie 180, tool_error 39

## Memory routes: gold evidence among the facts shown (all answers)

- memory: shown 419, not shown 81, no answer session 0
- memory_deep: shown 419, not shown 81, no answer session 0
- deep_tools_memory: shown 419, not shown 81, no answer session 0
- vote_memory: shown 419, not shown 81, no answer session 0

## Reading it (2026-11-22)

- Made by `python -m flotilla.scoring stages` (Fir 5218454 pool, 5218621 LongMemEval) and `stage_table.py`; every
  trace's final answer matched its label (no skips). Labels unchanged.
- Most wrong answers are reasoning_error: every graded sample was wrong with the information present.
- vote_wrong is the Vote routes' second cause (Vote 30 of 98, Vote+Tools 38 of 120); on memory questions the
  Vote samples are often ungraded (no judge saw that text), so vote_wrong there is a lower bound (samples_ungraded
  310).
- token_cap hits the thinking routes (Deep 13, Deep+Tools 13, 8 of them instruction questions on Deep+Tools);
  format_parse_failure the no-thinking ones (Fast 18: 12 instruction, 6 code).
- verifier_false_reject happened twice; verifier_false_accept never, because the instruction verifier and the label
  grader use the same regex and no code answer passed the public tests while failing the full tests.
- Memory routes: gold evidence (a fact from an answer session) is among the 50 facts shown on 419 of 500 questions,
  yet about 200 wrong answers per route had it: retrieval_miss (77) is the smaller part. "Evidence shown" is
  session-level (any fact from an answer session, not necessarily the needed one), so retrieval_miss is a lower bound.
