# Error stages on run-04-lme-maj3 (one stage per wrong answer, PROTOCOL.md 7.1; retrieval_miss at fact level)

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
| memory | 500 | 288 |  |  | 1 |  |  |  | 198 |  | 89 |
| memory_deep | 500 | 283 |  |  |  |  |  |  | 195 |  | 88 |
| deep_tools_memory | 500 | 277 |  |  |  |  |  |  | 193 |  | 84 |
| vote_memory | 500 | 280 |  |  |  |  | 6 |  | 189 |  | 85 |

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
| memory | 500 | 288 |  |  | 1 |  |  |  | 198 |  | 89 |
| memory_deep | 500 | 283 |  |  |  |  |  |  | 195 |  | 88 |
| deep_tools_memory | 500 | 277 |  |  |  |  |  |  | 193 |  | 84 |
| vote_memory | 500 | 280 |  |  |  |  | 6 |  | 189 |  | 85 |

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

## Memory routes: gold in the facts shown (fact level; all answers)

- memory: gold in facts 165, not in facts 275, rule does not apply (preference, abstention) 60; for reference, a fact from an answer session shown 419
- memory_deep: gold in facts 165, not in facts 275, rule does not apply (preference, abstention) 60; for reference, a fact from an answer session shown 419
- deep_tools_memory: gold in facts 165, not in facts 275, rule does not apply (preference, abstention) 60; for reference, a fact from an answer session shown 419
- vote_memory: gold in facts 165, not in facts 275, rule does not apply (preference, abstention) 60; for reference, a fact from an answer session shown 419

## Reading it (fact level, 2026-11-22)

- retrieval_miss now needs the gold answer itself inside the facts shown (GRAFT's gold-in-facts rule), not just a fact
  from an answer session. On the Memory routes it rises from 77 to 189-198 per route and reasoning_error falls from
  about 200 to 84-89: most Memory misses are retrieval (and writer) misses, as the 20-case study found.
- The gold is in the facts shown on 165 of the 440 questions the rule applies to (60 preference or abstention
  questions are left out); the session-level check said 419.
- The rule is a substring test after normalisation, so a gold worded differently from the fact ("45 minutes each way"
  against "45 minutes") counts as not shown: retrieval_miss is an upper bound and reasoning_error a lower bound.
- Base routes and pool questions are unchanged (no facts shown). The session-level table is kept as
  error_stages_session_level.md.
