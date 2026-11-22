# Tests (Flotilla)

91 tests in 12 files, in plain words. Generated from each test's docstring by `scripts/make_tests_doc.py`; to change a line, edit the docstring and rerun the script. `tests/test_tests_doc.py` fails if a test is missing here or a line is out of date. The Gaps section at the end is written by hand.

## [tests/test_formats.py](../../tests/test_formats.py)

Format tests for every dataset Flotilla converts (LongMemEval has its own, tests/test_longmemeval.py).

| Test | What it checks | Guards against |
|---|---|---|
| `test_math_benchmarks` | Checks that GSM8K, MATH-500 and AIME items keep the dataset's ID, question and gold, with the GSM8K gold taken after #### and commas removed. | a GSM8K gold that keeps the worked solution or a thousands comma, so a right answer is graded wrong. |
| `test_gpqa_options_shuffled_but_complete` | Checks that each GPQA item has the four original options in some order and that the gold letter points at the correct answer. | a shuffle that drops an option or leaves the gold letter pointing at a wrong answer. |
| `test_ifeval_keeps_instructions` | Checks that IFEval items keep the prompt, the key-based ID, the instruction ID list and their kwargs unchanged. | IFEval items losing the instruction list or kwargs the ifeval scorer needs to grade them. |
| `test_vision_benchmarks_keep_images_and_options` | Checks that MMMU items keep every image, option and answer letter, and OCRBench items keep the image, a gold list and the OCR type. | a vision item with a missing image, or an MMMU multiple-choice question whose lettered options differ from the dataset. |
| `test_lcb_keeps_every_test` | Checks that LiveCodeBench items keep all public and private tests, give public tests only for stdin problems, and show starter code. | a code item graded on fewer tests than the dataset has, or a function problem shown without its starter code. |
| `test_ruler_items_and_round_trip` | Checks that exported RULER 32k and 64k items have a list of gold strings and the ruler_substring scorer, and rebuild exactly from the lm-eval instance. | a RULER item whose ID, gold list or token count no longer matches what export_ruler.ruler_item produces. |
| `test_pool_sources_round_trip` | Checks that every router pool source (GSM8K, MATH, AIME, MMLU-Pro, IFEval-like, LiveCodeBench) keeps the raw row's ID, question, gold and tests. | MMLU-Pro rows cut to four options instead of up to ten, or a MATH gold not taken from the boxed answer. |
| `test_strategy_label_items_round_trip` | Checks that strategy label items built from pool rows keep the pool ID, task, task type and source, with no gold and the router_label scorer. | a label item carrying its gold in the item file, or an ID that no longer matches the pool row it is graded against. |

## [tests/test_label_merge.py](../../tests/test_label_merge.py)

The LongMemEval label merge's verdict checks (flotilla/strategy_labels.py).

| Test | What it checks | Guards against |
|---|---|---|
| `test_every_longmemeval_question_needs_exactly_one_verdict_per_route` | Checks that the merge names every question without an answer and every answer without a judge verdict. | a LongMemEval question silently left out of the labels, or graded by nobody, when a judge job dies. |
| `test_a_second_verdict_for_the_same_answer_stops_the_merge` | Checks that two judge verdicts for one (question, route) stop loading, naming the pair. | a stray verdict from a partial run folder silently replacing the chosen folder's verdict. |

## [tests/test_leakage_extra.py](../../tests/test_leakage_extra.py)

leakage --extra-targets: sets besides the test sets (the chat guide's source vs LongMemEval, 2026-11-22).

| Test | What it checks | Guards against |
|---|---|---|
| `test_extra_targets_reads_task_or_text_and_skips_empty` | Checks that extra_targets reads each line's task, or its text when there is no task, and drops blank or missing ones. | blank strings or lines with neither field being added as leakage targets. |

## [tests/test_longmemeval.py](../../tests/test_longmemeval.py)

| Test | What it checks | Guards against |
|---|---|---|
| `test_sample_format` | Checks that the 10-item LongMemEval sample has exactly the expected fields, all six question types, an abstention item and clean turns. | converted items with a missing or extra field, or an abstention flag that does not match the _abs question ID. |
| `test_convert_round_trip` | Checks that convert() on the raw dataset layout gives back the stored sessions, answer and map of answer-holding turns. | convert() dropping turns or losing which turns hold the answer. |
| `test_units_and_flags` | Checks that a long turn is cut into overlapping windows that keep every 13-word run whole, and that item_flags reports only a flagged turn or question. | a 13-gram overlap being missed because it straddles two windows, or a clean item being flagged as leaked. |
| `test_split_is_seeded_and_stratified` | Checks that split() gives the same split whatever the input order, spreads each question type evenly, and puts no item in two splits. | the split changing when items are read in another order, or one question type missing from held-out. |
| `test_history_prompt_orders_sessions_by_date` | Checks that history_prompt sorts sessions by date, lists every session, and ends with the question after the current date. | sessions shown out of date order, so the model reads an old fact as the newest one. |

## [tests/test_memory_route.py](../../tests/test_memory_route.py)

Memory routes (flotilla/memory_route.py): availability, GRAFT documents, cache keys, the memory block, the judge,

| Test | What it checks | Guards against |
|---|---|---|
| `test_availability_is_explicit_per_item` | Checks that Memory routes are offered only on items with sessions, and that memory on a pool item raises MemoryUnavailable. | a Memory route silently running on a question with no history instead of being marked unavailable. |
| `test_normalize_item_hides_the_answer` | Checks that normalize_item turns a LongMemEval item into a memory task with the lme_judge scorer and removes the answer, answer sessions and meta. | the gold answer or the answer-session IDs leaking into what the model or router sees. |
| `test_sessions_become_dated_chunks_in_date_order` | Checks that sessions become dated chunks in date order, and that a long session is cut into numbered parts within the size limit. | chunks out of date order, or the later parts of a long session losing their date. |
| `test_graph_key_covers_history_and_build_settings_only` | Checks that the graph key changes with the history, build settings and LLM label, but not with retrieval settings like max_facts. | a graph built by the fake LLM or from another history being reused for a real run. |
| `test_graft_config_is_a_named_preset` | Checks that GRAFT settings come from named presets with unique G IDs, the env variable overrides them, and Memory configs match their base. | a Memory route changing GRAFT's method outside a named preset, or an unknown preset name being accepted. |
| `test_memory_block_is_labelled_and_dated` | Checks that the memory block has its header, dates each fact, ends before the question, and says when no facts were recalled. | recalled facts shown without dates, or the memory block placed after the question. |
| `test_judge_prompts_follow_longmemeval` | Checks that judge prompts use LongMemEval's wording for each question type and for abstention, reject unknown types, and that yes or no replies parse. | memory answers judged with a prompt that differs from LongMemEval's, so scores cannot be compared with the paper. |
| `test_judge_answer_with_fake_qwen` | Checks that judge_answer marks Canada right and France wrong with thinking off, and makes no judge call when there is no answer. | the judge running with thinking on, or spending a call on a missing answer. |
| `test_grade_refuses_memory_items` | Checks that the label grader raises an error when given a memory item. | memory answers silently counted wrong by the label grader instead of being sent to LongMemEval's judge. |
| `test_strategy_labels_with_memory_routes` | Checks that strategy labels mark pool items unavailable on Memory routes, grade LongMemEval items from judge verdicts, and count each GRAFT build once. | the GRAFT build cost for one history being counted four times, once per Memory route. |
| `test_four_routes_share_one_graph_and_see_the_memory` | Checks that the four Memory routes share one cached graph per history, see the memory in every prompt, and log build cost apart. | each Memory route rebuilding the same graph, or build tokens being added to the answer's token count. |
| `test_smalltest_run_with_a_memory_config` | Checks that smalltest.run with a Memory config skips pool items, answers LongMemEval items with memory, and logs the GRAFT build in graft_prepare.json. | real label runs sending pool items to GRAFT or putting the answer into the router record. |
| `test_cheapest_label_uses_the_rows_own_costs` | Checks that cheapest_label picks the right route with the lowest GPU-seconds on that row, uses route order on ties, and gives none if all fail. | a LongMemEval row labelled fast when memory was right and cheaper on that row. |
| `test_haiku_judge_logs_every_call_with_ids_and_cost` | Checks that the Haiku judge sends LongMemEval's prompt with thinking off and max_tokens 10, and logs each call's IDs, hash and cost. | a judge call with no usage log row, or a paid call made when there is no answer. |
| `test_merge_keeps_legacy_pool_rows_available` | Checks that merging old pool labels treats a route with a verdict as available, keeps the labels, and adds per-row GPU-seconds. | every run-03 pool row being labelled none because it lacks the available field. |
| `test_writer_v2_and_thinking_change_the_graph_key` | Checks that the writer prompt and LLM thinking change the graph build key, while user_node and log_writer_replies do not. | a G41 or G42 run reusing a G35 graph built with another writer prompt or without thinking. |
| `test_ask_for_more_adds_pool_facts_within_the_limits` | Checks that with ask_more on, a NEED MORE MEMORIES reply adds the next pool batch and asks again, up to the ask limit. | G40 on LongMemEval silently answering with only the first facts, or asking forever past the limits. |

## [tests/test_rl_router.py](../../tests/test_rl_router.py)

flotilla/rl_router.py with fake models only: masks, stop, the supervised start, reward with the time penalty, chain

| Test | What it checks | Guards against |
|---|---|---|
| `test_masks_memory_repeats_stop_and_budgets` | Checks that the policy mask hides Memory on pool questions, limits repeats, allows stop only after a step, and enforces GPU and step budgets. | the RL policy running the same greedy route twice or going past max_gpu_s on one question. |
| `test_untrained_policy_starts_from_the_supervised_pick_and_stops_on_accept` | Checks that an untrained policy takes the supervised pick first, stops after an accept, and moves to the best route after a reject. | a new policy ignoring the supervised pick, or stopping on an answer the verifier rejected. |
| `test_update_moves_q_towards_targets_and_save_load` | Checks that repeated updates pull the Q-value toward the target, and that a saved policy loads with the same Q-values and update count. | a resumed run starting from a policy whose weights or update count were lost on save. |
| `test_gpu_clock_shares_time_between_steps` | Checks that GpuClock splits GPU time equally between steps running at the same time and counts time with no step as idle. | two parallel steps each being charged the full wall time. |
| `test_every_route_reaches_the_model_with_its_own_settings` | Checks that each route runs through the real loop with its own sample count, and the GRAFT build is charged only on the step that asks. | vote running one sample instead of five, or the graph build being charged on every Memory route step. |
| `test_chain_reward_time_penalty_targets_and_log` | Checks that a chain moves to vote after a rejected fast step and logs steps, GPU-seconds, the reward with the alpha time penalty, and the Q targets. | a wrong final answer earning anything other than minus the time penalty. |
| `test_final_rules` | Checks that final_answer returns the last accepted answer, the last answer, or the vote winner as each rule says, and None when there are no steps. | a chain under the last_accept rule returning a rejected answer when an earlier step was accepted. |
| `test_train_resume_and_config_guard` | Checks that training resumes after a job killed mid-write without redoing finished epochs, refuses a changed alpha or held-out IDs, and logs compute. | a resumed run repeating epoch 0 or continuing with a different alpha than the run it extends. |
| `test_held_out_never_read_without_the_flag` | Checks that the held-out split is refused without the flag, its lines are never parsed, and a held-out item cannot be run as a chain. | the RL router reading or training on held-out questions. |
| `test_exclusions_from_the_audit` | Checks that exclusions list only the audit's wrong-gold questions, round-trip through a file, and stop when the two audit files disagree. | a model-wrong question excluded as wrong gold, which would change the beyond-oracle count. |
| `test_beyond_oracle_counts_only_questions_every_route_missed_minus_wrong_gold` | Checks that beyond_oracle counts only solved questions that every fixed route missed, and leaves out those with a wrong gold. | a solved wrong-gold question being reported as beating the oracle. |
| `test_evaluate_on_dev_reports_beyond_oracle_with_chains` | Checks that evaluate on dev writes chains, a table and a beyond-oracle report when a second vote run solves questions every fixed route missed. | the beyond-oracle table counting a wrong-gold question, or losing the repeat number of a sampled step. |
| `test_dry_run_end_to_end` | Checks that the dry-run command writes a table marked DRY RUN, the wrong-gold exclusions, and six train and six eval chains. | dry-run output that could be mistaken for a real result. |
| `test_estimate_from_labels` | Checks that the estimate command counts train questions per epoch, gives positive GPU-hours, and simulates the dev questions. | a compute estimate that leaves out the dev questions or reports zero GPU-hours. |

## [tests/test_session_docs.py](../../tests/test_session_docs.py)

The session documents (docs/session/) must match scripts/SHA256SUMS, which scripts/sync_session_docs.py

| Test | What it checks | Guards against |
|---|---|---|
| `test_session_docs_match_their_manifest` | Checks that the files in docs/session/ are exactly those listed in scripts/SHA256SUMS and that each file's hash matches. | a session document edited in one repo without running scripts/sync_session_docs.py. |
| `test_status_open_experiments_table` | Checks that the Open experiments table in STATUS.md has the fixed columns, rows numbered 1 to n, one of six states, and a date on every row. | a deleted row or an unknown state in the experiments table. |

## [tests/test_strategy_router.py](../../tests/test_strategy_router.py)

flotilla/strategy_router.py on small synthetic labels: route order and masks from the labels, "none" items, ties,

| Test | What it checks | Guards against |
|---|---|---|
| `test_load_routes_masks_costs_and_held_out_untouched` | Checks that load orders routes cheapest first, masks memory on items without one, scales costs by wall time, and refuses held-out. | the router being trained with a memory route on items that have no history. |
| `test_label_index_cheapest_correct_and_none` | Checks that label_index gives the cheapest correct available route, or -1 when no route is right. | a label pointing at a route that was right but not available on that item. |
| `test_argmax_and_threshold_rules_respect_masks_and_ties` | Checks that masked_argmax and cheapest_above skip masked routes, prefer the cheaper route on ties, and fall back to the top score. | a router picking memory on an item without a history because its score was highest. |
| `test_evaluate_refuses_unavailable_and_counts` | Checks that evaluate raises on a pick of an unavailable route and reports accuracy, pick counts, per-source results and output tokens. | an evaluation that silently scores memory picks on items with no memory. |
| `test_best_fixed_oracle_keep_rule_and_choice` | Checks the best fixed route choice, the oracle picks, the keep rule's thresholds, and picking tau by the keep rule or by accuracy. | memory being chosen as the best fixed route although it is not available on every item. |
| `test_lr_and_knn_never_pick_masked_routes` | Checks that the logistic regression and kNN routers never pick a masked route at any tau, and pick memory where it exists and deep elsewhere. | a trained router sending items without a history to the memory route. |
| `test_knn_none_neighbour_and_missing_route_prior` | Checks that a kNN neighbour no route solved gives zero for every route, and that a route the neighbour lacks falls back to its training accuracy. | a route missing on the neighbour being scored as if the neighbour had answered with it. |
| `test_train_and_evaluate_cheap_routers_end_to_end` | Checks that training bge_lr and kNN with fake embeddings writes their meta files and a dev table with fixed and oracle rows, and no held-out table. | a held-out table being written by a train run, or a fixed memory row when memory is not on every item. |
| `test_per_item_costs_pick_the_cheaper_route_on_each_row` | Checks that label_index, cheapest_above and masked_argmax use per-row GPU costs when given, and the global route order on ties or without them. | a LongMemEval row labelled fast at 300 GPU-seconds when memory was right at 40. |
| `test_load_reads_row_costs_and_task_text` | Checks that load reads per-row gpu_seconds and a row's own task text, and that labels and oracle picks use those row costs. | per-row costs in merged labels being ignored in favour of the job-wide average. |
| `test_item_text_longmemeval_reads_the_question` | Checks that item_text gives a LongMemEval item's history mark and question without the session text, and a pool item's task unchanged. | the router embedding the whole chat history, or the word memory, instead of the question. |
| `test_train_subset_nested_stratified_and_seeded` | Checks that train_subset keeps source proportions, nests smaller fractions inside larger ones, keeps ID order, and changes only with the seed. | learning-curve subsets that are not nested, so a bigger subset drops questions a smaller one had. |
| `test_lr_router_pickles_when_run_with_dash_m` | Checks that LRRouter can be pickled when strategy_router runs as python -m. | saving the trained router failing because its class was defined under __main__. |

## [tests/test_supersede_check.py](../../tests/test_supersede_check.py)

flotilla.supersede_check on hand-made graphs (the real-model check runs on the cluster; see the module docstring).

| Test | What it checks | Guards against |
|---|---|---|
| `test_all_steps_pass_when_the_newer_fact_wins` | Checks that check() passes extract, link and retrieve when both facts exist, the newer one supersedes the older, and the older is marked outdated. | a correct graph and retrieval being reported as a failed supersede. |
| `test_each_failing_step_is_reported` | Checks that check() fails the link and retrieve steps when a reworded new fact has no SUPERSEDES edge, and fails extract when the old fact is missing. | a broken step hidden behind a pass, so the wrong part of GRAFT gets blamed or fixed. |
| `test_chain_and_anchor` | Checks that check() follows a chain of SUPERSEDES edges, uses the anchor word to ignore unrelated facts with the same number, and reads 50th as 50. | a fact like 10 pages a night being taken as the old episode 10 fact. |
| `test_toy_items_carry_their_check` | Checks that the four toy items carry old, new and anchor values, dated sessions in order, the new value as answer and the old in session 1. | toy items whose answer or session order does not match their supersede check. |

## [tests/test_system.py](../../tests/test_system.py)

| Test | What it checks | Guards against |
|---|---|---|
| `test_parse_final_takes_last_json_block` | Checks that parse_final takes the answer and confidence from the last JSON block, and gives None when there is no JSON. | an early draft answer in the reasoning being taken as the final answer. |
| `test_vote_math_groups_equivalent_answers` | Checks that the maths vote counts 1/2, 0.5 and the LaTeX fraction for one half as the same answer. | equal maths answers written in different forms splitting the vote. |
| `test_vote_letters_and_code` | Checks that the letter vote ignores case and that the code vote picks the program that passes the public tests. | b and B being counted as different answers, or a failing program winning the code vote. |
| `test_verifier_deterministic_checks` | Checks that the verifier accepts a parseable maths answer and rejects a missing answer, an out-of-range letter, and an answer breaking a lowercase rule. | a verifier that accepts option E when the question only has A to D. |
| `test_retry_message_says_wrong_and_gives_reason` | Checks that the retry message says the answer was wrong, repeats it, and gives the verifier's reason, or says no answer could be parsed. | a retry that does not tell the model why its answer was rejected. |
| `test_solver_messages_include_task_type_addition` | Checks that the maths solver system prompt includes the sympy addition and that the user message is the task. | maths questions sent without the instruction to use sympy. |
| `test_valid_option_counts_options_in_the_question` | Checks that n_options counts the lettered lines in the question up to J, uses the options list when given, and falls back to four. | a verifier that accepts option K when the question only has A to J. |
| `test_llm_check_prompt_comes_from_verifier_v2` | Checks that the LLM check messages come from verifier.v2 and that parse_llm_verdict reads the verdict and reason, or gives None without JSON. | the checker using a different prompt than verifier.v2, or a reply without JSON read as a verdict. |
| `test_llm_check_reject_drives_one_retry` | Checks that an LLM check reject, run with thinking off at temperature 0, leads to one retry whose answer is kept and counted in compute. | the checker's model call being left out of the compute count, or the rejected first answer kept as final. |
| `test_llm_check_off_or_exact_check_present_means_no_checker_call` | Checks that no LLM check call is made when llm_verify is off, or when the task type already has an exact check, as maths does. | paying for an LLM check on maths answers that the exact check already verifies. |
| `test_llm_check_unparseable_reply_accepts` | Checks that an LLM check reply with no readable verdict accepts the answer without a retry. | a garbled checker reply forcing a retry of an answer that was fine. |
| `test_constraint_check_on_memory_reads_only_the_question` | Checks that constraint_check on a LongMemEval history or a GRAFT memory block finds no constraints from old sessions, while an instruction task keeps its own. | "add a P.S." or "at least 500 words" from an old chat session failing a memory answer (run-04 Vote+Tools). |

## [tests/test_tests_doc.py](../../tests/test_tests_doc.py)

docs/reference/TESTS.md lists every test, generated from the docstrings (scripts/make_tests_doc.py).

| Test | What it checks | Guards against |
|---|---|---|
| `test_tests_doc_lists_every_test_and_is_up_to_date` | Checks that every test has a two-line docstring and that TESTS.md matches what the docstrings generate. | a new or changed test that TESTS.md does not describe, so the plain-words list drifts from the code. |

## [tests/test_tools.py](../../tests/test_tools.py)

| Test | What it checks | Guards against |
|---|---|---|
| `test_sympy_check_equivalent_forms` | Checks that sympy_check treats one half and 0.5, and a boxed 2 times root 2 and root 8, as equal, and 3 and 4 as different. | a right maths answer marked wrong because it is written in another form. |
| `test_python_exec_and_public_tests` | Checks that python_exec runs code on stdin, stops an endless loop with a timeout, and that run_public_tests reports 2/2 passes. | an endless loop in generated code hanging the run. |
| `test_constraint_check_detects_and_checks` | Checks that constraint_check finds the lowercase, word count and no-comma rules, passes an answer meeting them, and fails one breaking all. | an instruction answer passing while it breaks the task's lowercase, length or comma rules. |
| `test_constraint_check_json_and_ending` | Checks that a JSON answer missing the required ending phrase fails, and that JSON inside a code fence passes the JSON rule. | a JSON answer in a code fence being rejected as not JSON. |
| `test_forbidden_keywords_are_not_required` | Checks that keywords the task forbids fail the answer when present and are not required when absent. | a correct answer rejected for not containing words it was told to leave out. |
| `test_postscript_uses_the_asked_phrase_after_the_main_text` | Checks that the postscript rule looks for the phrase the task asks for, such as Addendum or PS, after some main text. | a postscript starting with Addendum being rejected, or a postscript with no main text before it being accepted. |
| `test_markdown_divider_paragraphs` | Checks that paragraphs split by the markdown divider * * * are counted against the asked number. | a two-paragraph answer with a * * * divider being counted as one paragraph. |
| `test_capital_word_limit_is_a_count` | Checks that the all-capitals word limit counts capitalised words against the asked maximum. | an answer with one capitalised word rejected under an at most 2 times limit. |
| `test_whole_output_json_is_met_by_the_loop` | Checks that the whole-output JSON rule passes only when the loop wraps the answer, and that a JSON array request does not block bullets. | a correct answer rejected as not JSON when the Flotilla loop already wraps its output in JSON. |
| `test_float_outputs_within_tolerance` | Checks that same_tokens matches floats that differ only in the last digits and still tells apart different numbers and integers. | a correct code output failing a test over float rounding in the 15th digit. |
| `test_math_format_matches` | Checks that the maths grader accepts answers equal to the gold without dollar signs or LaTeX text, and the right letter in a lettered question. | answering C, where option C is 0.20, being graded wrong against a gold of 0.20. |
| `test_math_unicode_units_and_thousands` | Checks that the maths grader accepts Unicode infinity, union and root signs, thousands separators, and a unit or short phrase around the number. | 852 BC graded wrong against a gold of 852, or 650 graded right against 670. |

## Gaps

Things nothing tests yet (written by hand; the generator keeps this section).

- **Every LongMemEval question has exactly one judge verdict per route.** The label merge now stops and names every
  question with no answer, every answer with no verdict, and every pair with two verdicts
  (`flotilla/strategy_labels.py`, tested in `tests/test_label_merge.py` on toy data). No test reads the real label
  files: run-04-lme was checked once by hand on 2026-11-22 (5,000 verdicts, 500 questions x 10 routes, none missing,
  none twice).
- **The LLM check (F33, F34) on a real server.** Its tests use a fake model client; the first real use is test 06.
- **The truncation rule for histories past the window** (protocol section 11). Not built yet, so not tested; it needs a
  test before any run past the window.
- **Supersede on chat histories with a real model.** The checker is tested on hand-made graphs
  (`tests/test_supersede_check.py`); whether Qwen's writer and GRAFT get it right is a cluster check (status row 23).
- **Scorer names.** The format tests check each item's scorer against a fixed list, not against `scoring.SCORERS`
  (importing it needs math_verify, which the Mac lacks).
- **RULER generation.** The format test uses exported items; a change in how lm-eval builds RULER would only show in
  `export_ruler.py`'s own count checks at build time.
- **IDs across documents.** Nothing checks that every system config, status row or test table names a candidate that
  exists in the registry.
