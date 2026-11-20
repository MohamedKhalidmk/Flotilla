Full labels: 1450 pool questions, every route on every question, graded against gold (flotilla/strategy_labels.py). Cheapest correct = the label a router learns. No route right: 17; some route right: 0.9883. GPU-seconds = whole job / questions (server load included).

| route | what_it_does | questions | accuracy | output_tokens_per_question | gpu_seconds_per_question | cheapest_correct | run | status |
|---|---|---|---|---|---|---|---|---|
| Fast | thinking off, no tools, 1 sample | 1450 | 0.903 | 2047 | 2.6 | 1310 | run-03/graded | labels |
| Tools | thinking off, native sympy / Python / constraint tools | 1450 | 0.925 | 1969 | 4 | 75 | run-03/graded | labels |
| Deep | full thinking, no tools | 1450 | 0.952 | 4791 | 7.5 | 42 | run-03/graded | labels |
| Deep+Tools | full thinking with the tools | 1450 | 0.943 | 5278 | 12.1 | 5 | run-03/graded | labels |
| Vote | full thinking, 5 samples, majority (tests on code) | 1450 | 0.967 | 20373 | 16.4 | 0 | run-03/graded | labels |
| Vote+Tools | Vote with the tools in every sample | 1450 | 0.963 | 21541 | 20 | 1 | run-03/graded | labels |
| Memory | GRAFT retrieval on the full T-REx base, all on Qwen |  |  |  |  |  |  | planned |
| Memory+Deep | GRAFT facts, then Deep |  |  |  |  |  |  | planned |
| Vote+Memory | GRAFT facts, then Vote |  |  |  |  |  |  | planned |
| Deep+Tools+Memory | GRAFT facts, then Deep+Tools |  |  |  |  |  |  | planned |
| Some route right (oracle) | best route per question, known only after trying all | 1450 | 0.988 |  |  |  | run-03/graded | labels |
