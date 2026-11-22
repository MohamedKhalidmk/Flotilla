# Forced-tool routes, a self-check route and IFEval-standard constraint checks (design)

> Status: design only, 2026-11-22. Nothing runs until the user approves. New IDs: F37-F40 (routes), S169 (toy check),
> S170 (pilot). The routes go into the single full relabel, after the writer v2 decision.

## Why

Run-04's tool analysis (experiments/test-04-strategy-router/runs/run-04, tool_use.md and tool_by_tool.md):

- Qwen decides alone whether to call a tool. Tools help the cheap Fast-style route (python_exec +52/-31 against Fast,
  constraint_check +41/-17) and add little or hurt once Qwen thinks or votes. sympy is neutral everywhere.
- python_exec on code questions helps on Tools and Deep+Tools (+9/-3, +11/-1).
- constraint_check reads its rules with a hand-written regex. It finds a rule in only 106 of the 236 instruction
  questions, although every one of them (RLVR-IFeval) has exactly one ground-truth rule. The label grader uses the same
  regex, so 130 instruction labels count any non-empty answer as right (see "Grading" below).

So the question is whether making Qwen use a tool, or check itself with code, beats letting it choose, and at what
compute.

## What was read

- **ReTool** (Feng et al., 2025, arXiv 2504.11536; the user cites it as ICLR 2026, which the arXiv page does not
  state). Code runs inside long reasoning: the model writes a code block, generation pauses, the sandbox output (results
  and error messages alike) comes back, and the model continues. After RL, code is used on about 98% of questions,
  responses are about 40% shorter (about 10k to 6k tokens), and the model fixes its own code after errors (an undefined
  function, then "the functions need to be defined in the same scope"). The cold-start model with the interpreter but
  no RL scored 40.9% on AIME 2024 against 26.7% for the base model. Lesson for us: the gain comes from code inside a
  thinking trace, with errors fed back; we have no RL, so we only get the "interpreter at inference" part.
- **CRITIC** (Gou et al., ICLR 2024, arXiv 2305.11738). Answer, verify with a tool (a Python interpreter for maths
  programs: error messages as "Execution: ..." and the value of `answer`), correct, up to 4 corrections, stop when the
  result does not change across two revisions; 2-3 rounds give most of the gain. ChatGPT on GSM8k: 72.5 (program of
  thought) to 78.2. Without the interpreter the corrections are "limited and unstable" (Text-Davinci-003 dropped below
  the start). Lesson: the check must run, not just be reread.
- **IFEval checkers** (google-research/instruction_following_eval, Apache 2.0). 25 instruction IDs with arguments
  (keywords:existence, length_constraints:number_words, detectable_content:postscript, ...), each a checker class with
  `build_description(**kwargs)` and `check_following(response)`. The same code ships in lm-evaluation-harness
  (`lm_eval.tasks.ifeval`), already installed in Flotilla's env and used by `scoring.ifeval`; it needs nltk punkt
  (present in ~/nltk_data on the clusters) and langdetect (installed).
- **RLVR-IFeval** (our instruction pool): every row has `ground_truth` = one of 24 functions with its arguments
  (validate_choice, validate_word_constraint with N and quantifier, verify_postscript with postscript_marker, ...),
  about 610-655 rows each. Each maps onto an IFEval instruction ID.
- **vLLM 0.32.0 (our env) with `--tool-call-parser qwen3_coder`**: `tool_choice` accepts "required" and a named
  function. For this parser vLLM does not use the generic JSON-array constraint; it uses xgrammar's built-in
  `qwen_3_coder` structural tag (VLLM_ENFORCE_STRICT_TOOL_CALLING, default on), which forces a call in Qwen's own XML
  tool format and lets the reasoning come first. Supported on paper; the toy check confirms it on our server before
  anything else.
- **Qwen's chat template** keeps an assistant turn's reasoning after the last user message only when the client sends
  it back as `reasoning_content`. Our tool loop appends `{"role": "assistant", "content": ..., "tool_calls": ...}`
  without it, so in today's Deep+Tools and Vote+Tools every tool round starts its thinking over. A ReTool-style route
  needs the reasoning sent back (change 1 below).

## Changes shared by the new routes

1. **Reasoning kept across tool rounds.** The loop sends each round's `reasoning_content` back with the assistant turn,
   so Qwen's thinking continues after a tool result, as in ReTool. Applies to every tool route in the relabel (it
   changes Deep+Tools and Vote+Tools behaviour, which is why it waits for the relabel).
2. **Errors saved.** Every tool record in the trace gets `detail` (python_exec: return code, the last 1,000 characters
   of stderr, "timeout" or the exception; sympy: the parse error) next to `output`. Qwen already receives them in the
   tool message; now the trace keeps what Qwen saw, so errors can be counted and read.
3. **Forcing.** The first call of a forced route sets `tool_choice` to the route's tool by name
   (`{"type": "function", "function": {"name": "python_exec"}}`), which is stricter than "required" (any tool would
   satisfy it). Later rounds use "auto"; the last round offers no tools, as now. The prompt says the tool must be used.
   If the named form fails the toy check, the fallback is "required" plus the wording, reported before any pilot.
4. **sympy stays available** on every tool route (item 4); forcing one tool never removes the others after the first
   call.

## The routes

| ID | Route | Base | Forced first call | Rounds | Why this base |
|---|---|---|---|---|---|
| F37 | Forced Code | Deep (thinking on) | python_exec | up to 8 tool rounds, reasoning kept | ReTool's gain is code inside long reasoning; our data agree: python_exec on Deep+Tools fixes code questions (+11/-1); Fast has no reasoning to interleave into |
| F38 | Forced Sympy | Fast (thinking off) | sympy | up to 3 | sympy checks one expression; it can catch the arithmetic slips of an answer written without thinking, while Deep already rechecks (sympy on Deep+Tools +4/-10, on Tools +13/-6) |
| F39 | Forced Rules | Fast (thinking off) | constraint_check v2 | up to 3 | constraint_check helped on Tools (+41/-17; instructions +23/-1) and hurt on the thinking routes (Deep+Tools instructions +7/-15); formatting is mechanical and needs no thinking |
| F40 | Self-Check | Fast (thinking off) | python_exec in each check | 1 answer + up to 3 check-revise rounds | CRITIC gains most where the first answer is unchecked and cheap; Fast leaves the most room (0.879 against Deep's 0.934) at the lowest cost. A Deep-based variant only if the pilot shows a gain |

All four: one sample, temperature 0, verifier v2 on (as every route), the same 32,768-token cap per call, every model
call counted in compute. Configs `configs/systems/qwen_strategy_{forced_code,forced_sympy,forced_rules,self_check}.json`.

### F40 Self-Check, step by step

1. Answer as Fast does (no tools). Answer A0.
2. Check: Qwen (thinking off, temperature 0) sees the question and the current answer and must call python_exec (named
   tool choice) with a program that checks the answer independently: recompute it another way, substitute it back,
   test it against the stated rules or the examples in the question, or, for code, run the candidate program on the
   examples given in the question. The program prints `CHECK PASS` or `CHECK FAIL: <reason>`.
3. A run that prints CHECK PASS stops the loop. CHECK FAIL, an error, a timeout or no verdict line counts as a fail;
   Qwen then sees the question, its answer, the check program and the full output (errors included) and writes a
   revised answer in the usual JSON block.
4. Stop after 3 check-revise rounds, or earlier when the revised answer equals the previous one (normalised, CRITIC's
   rule). The final answer is the last answer.

On memory questions there is often nothing to compute; the prompt allows `CHECK PASS: nothing to compute` (dates and
counts in temporal questions can still be checked). The share of such passes is reported, since a route that always
passes is just Fast with extra calls.

## constraint_check v2 on IFEval's standard (item 3)

- **Rule listing.** One Qwen call per question (thinking off, temperature 0, prompt `prompts/ifeval_rules.v1.md`) sees
  only the question (`system.question_only`, so never a chat history) and the list of the 25 IFEval IDs with their
  arguments, and returns `[{"instruction_id": "...", "kwargs": {...}}]` (an empty list when the question sets no rule).
  Each entry is validated against `lm_eval.tasks.ifeval.instructions_registry.INSTRUCTION_DICT` and the checker's
  `build_description` arguments; an unknown ID or bad arguments is dropped and logged. The rules are cached per question
  within a run, so samples and later rounds reuse them, and saved in the trace.
- **Checking.** The official checkers' `check_following(draft)` per rule (IFEval's strict mode), returned to Qwen as one
  line per rule with pass or fail. The loop's own JSON wrapping meets `detectable_format:json_format`, as now.
- **What it replaces.** The tool and verifier v2's instruction check both use the parsed rules; the hand-written regex
  (`tools.detect_constraints`) is kept only as `constraint_check_regex` to reproduce run-04's labels.
- **Free accuracy check.** RLVR-IFeval's ground truth gives the right rule for every pool instruction question, so the
  rule listing's recall and precision are measured in the toy check and the pilot (the 24 functions map onto IFEval
  IDs; the mapping gets its own test).

## Grading instruction questions (a label change, for the relabel)

The label grader should use each question's ground-truth rule (RLVR-IFeval `ground_truth`, mapped onto the official
checkers), not the regex and not Qwen's parsed rules (which are part of what is being tested). Today 130 of the 236
instruction labels accept any non-empty answer. This changes labels for every route, so it goes into the full relabel
and needs the user's yes; the pilot reports instruction accuracy with both graders.

## Prompts (versioned, in prompts/)

- `forced_tool.v1.md`: one section per tool, appended to the solver's system message on a forced route ("Use
  python_exec to work this out; run code for every calculation and keep thinking after each result", and so on).
- `self_check.v1.md`: the check message and the revise message of F40.
- `ifeval_rules.v1.md`: the rule-listing prompt, with the 25 IDs and their arguments copied from the registry.

## Tests (fake model, Mac or Fir CPU)

- the first call of a forced route sends the named tool choice; later rounds send "auto"; the last round sends no tools
- the assistant turn sent back after a tool round carries `reasoning_content`
- a failing python_exec program's stderr reaches the tool message and the trace's `detail`
- F40: CHECK PASS stops after one check; FAIL then the same answer stops (CRITIC rule); three FAILs stop at 3 rounds;
  an error counts as FAIL and its text reaches the revise message; every call is in compute
- constraint_check v2: rule JSON parsing, unknown IDs and bad arguments dropped, rules read from the question only (a
  history's "add a P.S." gives no rule), the official checker's verdict returned, rules cached per question
- the 24 RLVR-IFeval functions map onto IFEval IDs with the right arguments (one sample row each)
- `test_formats`-style check that the ground-truth grader agrees with the dataset on hand-made right and wrong answers

## Gate before any pilot: toy check on the real Qwen (item 8, S169)

One Fir GPU job, Qwen served as in the labels, 3-5 known-answer questions per route:

| Route | Toy questions (known answers) |
|---|---|
| F37 | sum of the primes below 1,000 (76127); trailing zeros of 100! (24); determinant of [[2,1],[1,3]] using numpy (5; numpy is not in the sandbox, so the ImportError must come back and Qwen must recover); one pool code question with public tests |
| F38 | solve 2x + 3 = 11 (4); (x^2 - 1)/(x - 1) at x = 3 (4); the integral of x^2 from 0 to 1 (1/3) |
| F39 | "capital of France, all lowercase" (paris, change_case:english_lowercase); "exactly 3 bullet points about cats" (detectable_format:number_bullet_lists, 3); 3 RLVR-IFeval rows with known ground truth |
| F40 | 17 x 23 (391); days from 2023-03-01 to 2023-04-15 (45); one multiple-choice science question; one pool code question |

Passes only if every question has a parsed final answer, every forced route's first call is the forced tool, every
rule listing parses, and no answer is empty. On any failure the run stops there and the failure is reported, with no
pilot. For each route one full trace is dumped to `experiments/test-10-forced-tools/toy/<route>.md`: the system prompt
and tool schemas, the tool choice per call, every reply (reasoning, content, tool calls), every tool result with its
error text, and the final answer, so the user can read what Qwen saw and did.

## Pilot (item 6, S170), after the toy check passes and the user says go

- 193 dev questions, stratified and seeded: math 70, memory 40, instruction 36 (all dev), science 35 (all), code 12
  (all). Dev only; held-out untouched.
- Routes, all the same day: F37-F40 and the comparators Fast, Tools, Deep, Deep+Tools as they are today. One repeat
  (a screen, not a keep decision).
- Memory answers by the Haiku judge, majority of 3 (about $0.05, the key through the dialog); instruction answers
  graded both ways (regex grader and ground-truth grader).
- Reported per route and task type: accuracy, GPU-seconds, Qwen calls, forced-call success, tool calls and error
  rate, F40's rounds and its "nothing to compute" share, and F39's rule recall and precision against the ground truth.
- Cost: about 7 GPU-hours on H100 (new routes about 4, comparators about 3), free.

## After the pilot (item 7): route list, relabel cost, RL router

- **Route list for the full relabel:** Fast, Tools, Deep, Deep+Tools, Vote, Vote+Tools, the four Memory routes, plus
  whichever of F37-F40 the pilot does not rule out; the existing tool routes run with changes 1-2 and constraint_check v2.
- **Extra GPU cost** to label all 1,950 questions on the new routes, from run-04's per-question GPU-seconds (Fast 9.8,
  Tools 11.9, Deep 17.5, Deep+Tools 19.7): F37 about 25 GPU-s per question (13-14 GPU-hours), F38 about 12 (6-7), F39
  about 13 (7), F40 about 20 (10-11), so about 38 GPU-hours for all four (range 25-60), against about 70 for run-04's
  six base routes. The pilot's measured GPU-seconds replace these estimates.
- **RL router (F28):** its actions are the routes plus stop; 10 routes become up to 14, so 15 actions. The new routes are
  greedy (temperature 0), so they are never repeated on a question. Its state features grow with one supervised
  success estimate per route, and its priors come from supervised routers retrained on the relabel with the new routes.
  Saved policies record their action set and refuse another, so the RL router is trained afresh on the relabel (as
  planned). F40 overlaps with what the RL router does across steps (answer, check, try again), which the pilot
  comparison should show.

## Open questions for the user

1. Named tool choice (stricter) rather than "required" for the forced first call.
2. Change 1 (reasoning kept across tool rounds) also changes today's Deep+Tools and Vote+Tools in the relabel.
3. Grading instruction questions with the ground-truth rule in the relabel (130 labels change meaning).
4. F40's base: Fast as proposed, or Deep.
