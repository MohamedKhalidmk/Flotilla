# History rewrite of 2026-11-22 (GPQA removal): old and new commit hashes

GPQA asks that its examples not be published online. Its question text had reached seven files in this repository's
history (test 02 audits, the old reports/failure_audit pages, the format samples); the history of `main` and
`restructure` was rewritten with git filter-repo to replace those files' GPQA parts (made-up rows, or "withheld"),
checked against all 546 GPQA questions (zero matches on every ref), and force-pushed once with the user's approval.
Commits before the first affected one keep their hashes (the protocol tags v1-v9 are unchanged). Hashes quoted in
older docs (run log, STATUS, GRAFT notes) refer to the old history; this table maps them.

125 commits changed hash.

| Old | New | Date and subject |
|---|---|---|
| 0188cca | 4e92a2e | 2026-11-20 run_log: stopword link before/after counts, corrected cleaning |
| 02313d4 | 76ac264 | 2026-11-20 test 04 run-03: per-route need (only-this-route-right, cheapest correct, oracle without it); run_lo |
| 066b240 | 5040095 | 2026-11-22 Error stages at scoring time (PROTOCOL 7.1 rules, token_cap added, live stages marked, tests); REFE |
| 078f9cf | 8227c4d | 2026-11-21 LongMemEval labels: base routes and GRAFT on 3g.40gb MIG slices (measured), GRAFT env check fixed,  |
| 0854bce | 723fef9 | 2026-11-21 LongMemEval for the Memory routes: download manifest (longmemeval-cleaned at 98d7416, sha256 checke |
| 09818dd | ad628a9 | 2026-11-20 run_log: GRAFT runs on the original graph, embed once, twins |
| 09ce506 | 80fd3d4 | 2026-11-21 Candidate and setup IDs (registry) in every test table, figure and README; INDEX and the learning-c |
| 0c72bcd | b8e42d8 | 2026-11-22 STATUS.md: Open experiments table (both repos), report rule in WORKING_SETUP, table check in test_s |
| 0d5363d | 4ca577b | 2026-11-22 Supersede check for chat histories (checker, toy histories, unit tests, submit script); STATUS rows |
| 0eabe60 | 464faf5 | 2026-11-22 Bridge keeps the guide plan in each retrieval record; STATUS row 25 (relation-name mismatch check) |
| 0eac958 | cdf94c2 | 2026-11-22 STATUS: G39/G40 Qwen runs started (row 5) |
| 0eb0595 | 9a3a3e8 | 2026-11-22 Design F37-F40 (forced tools, self-check, IFEval rules); run-04-lme-maj3 is the label set; lme-3c10 |
| 0f159ad | 58d3f41 | 2026-11-22 Session PDFs rebuilt from the current markdown (WeasyPrint on Fir, same theme; code blocks wrap) |
| 165bbd1 | b8f8cbc | 2026-11-21 merge_lme_labels.sh: one complete run folder per route and shard, then the run-04-lme merge as a Fi |
| 166882e | 3b41eb3 | 2026-11-22 Docs restructure (user): docs/reference/ (PROTOCOL, REGISTRY, run log, PROMPTS), docs/session/ (HAN |
| 16aa17a | 015d9b7 | 2026-11-21 docs: HANDOFF.pdf (built on Fir with WeasyPrint, same theme) |
| 1a30a86 | df47dc8 | 2026-11-22 LongMemEval judge: --repeats and combine-verdicts (majority of 3 per answer), tests |
| 1c1f27e | ca5961b | 2026-11-20 run_log: GRAFT full T-REx jobs ended at 0.0 on all 9 repeats (retrieval bug), spend now $4.58 |
| 1d12780 | fa74593 | 2026-11-22 Reports and legacy cleanup: reports/ keeps leakage only; failure audit moved into tests 02 and 03 ( |
| 20f2a1d | 4d27bf0 | 2026-11-22 test-04: error stages on run-04-lme-maj3; STATUS rows 33-34 |
| 23d3899 | b9ac076 | 2026-11-20 run_log: keep all six routes for router training |
| 2486112 | bdbbc9b | 2026-11-21 run log: Trillium as a third GPU pool for free Qwen work; Qwen 1,024-token rerun twinned there |
| 2801d0b | 783895f | 2026-11-20 run_log: GRAFT full T-REx retrieval bug cause (PageRank stopped after one step) and fix |
| 2e7fb19 | 965fe73 | 2026-11-21 Memory routes use the T-REx structure guide (GRAFT default since test 06); router choices recorded  |
| 2fae2d1 | 83dda4b | 2026-11-21 merge_lme_labels.sh: keep only the verdicts of the chosen run folders (a timed-out partial shard wa |
| 3059244 | 6af752e | 2026-11-20 Older-model failure audit: every wrong answer of gpt-oss, Command A+ and Phi (small test, router-B  |
| 33579c0 | 8cecc49 | 2026-11-22 LLM verifier: verifier v2's LLM check behind llm_verify (Qwen checker, thinking off), tests; F33/F3 |
| 346db0e | 18b2ea1 | 2026-11-22 Test 06: table script (accuracy, reject rate, retry flips, checker failures, extra GPU-seconds) |
| 3aabd5f | 461f554 | 2026-11-22 Memory route: writer prompt is a graph build key and GRAFT's thinking switch (graft.llm_thinking) g |
| 3ac7f6c | bfb432e | 2026-11-22 submit_strategy_router.sh: ROUTER_GPU picks the GPU (e.g. a 3g.40gb MIG slice, which starts sooner  |
| 3bdfc57 | f58e01f | 2026-11-21 strategy_labels merge: pool rows from before the 'available' field (run-03) count a route with a ve |
| 3c8fab1 | a2f6104 | 2026-11-22 run log: docs restructure |
| 3da5288 | 8d7e3b7 | 2026-11-21 lme_job: GRAFT env check imports openai and the gateway |
| 3ebffba | 0589bce | 2026-11-21 memory_route HaikuJudge: await the async raw response's parse() (judge job 5119538 failed on it aft |
| 3efc91f | f334434 | 2026-11-22 F35 keep-rule numbers confirmed by the user; STATUS row 9 queued |
| 4223769 | 70add15 | 2026-11-21 READMEs and INDEX: full T-REx base dropped (no base graph for Memory routes), Memory routes only on |
| 4601d85 | e36d591 | 2026-11-21 PROJECT_HISTORY: candidate IDs and the old-name map |
| 4e5cfea | 126048f | 2026-11-21 docs: WORKING_SETUP (clusters, jobs, keys, rules, protocol summary, first 10 minutes; PDF built on  |
| 5052d92 | 5e87a5c | 2026-11-21 Memory routes wired to GRAFT: graph per history built once on Qwen and cached (presets plain_c and  |
| 5121529 | 224f648 | 2026-11-22 TESTS.md: every test in plain words, generated from two-line docstrings (scripts/make_tests_doc.py) |
| 52c6d74 | 0ee8f00 | 2026-11-21 run log: Haiku baseline check result (drop is outside the code); Qwen released; spend $6.05 |
| 5569321 | 5e70e38 | 2026-11-22 F37-F40: named forced tool, reasoning kept across tool rounds (all tool routes), tool errors saved, |
| 5980b64 | aa310a4 | 2026-11-21 run log: GRAFT on Qwen recorded, answer cap check and 1,024-token Qwen rerun, LongMemEval base rout |
| 5c883c3 | 3620181 | 2026-11-22 Remove GPQA question text: made-up GPQA rows in the format samples (sampler too), GPQA questions wi |
| 5fa7ec5 | bdc9304 | 2026-11-22 leakage: --extra-targets NAME=JSONL checks a corpus against more sets than the test sets (for the c |
| 64af3d4 | 26fc593 | 2026-11-21 Registry (approved, IDs frozen): Flotilla candidates F01-F28, setups S102-S146, statuses, pre-fix r |
| 66d39bc | dc56953 | 2026-11-20 run_log: EiG and working-memory jobs submitted |
| 67086ff | 075eb1b | 2026-11-21 run log: decisions, same-day check submitted |
| 684b26a | a85bc61 | 2026-11-20 run_log: working memory run-01, spend now $5.24 (T-REx passes still running) |
| 69a67b1 | e68d844 | 2026-11-22 servers_longmemeval_memory.json note: the judge is Haiku (protocol-v10 addendum), not this Qwen ser |
| 6abbfa3 | 14eca40 | 2026-11-22 G41 rebuilt with the fixed writer, pre-fix graphs marked; old-writer check; port-clash audit; calls |
| 6b47a48 | 062630a | 2026-11-21 test-04: judge_check.py, seeded sample of LongMemEval judge verdicts for the hand check and the agr |
| 6c9cb73 | 4bfad00 | 2026-11-22 run log: user decisions (DNLI approved, RL from F30 after the Memory decision, retrain all four on  |
| 6f1d265 | fc7e892 | 2026-11-22 F36: USC tie rule for the free-text vote (prompt, config, replay script, tests); registry F36, S168 |
| 7188482 | f6b0a46 | 2026-11-21 submit_strategy_router.sh: ITEMS may list several globs (pool shards and LongMemEval items) |
| 71a5e3e | e7c5443 | 2026-11-22 Reasoning-graph route design (F35); protocol-v10 addendum 2: truncation rule for histories past the |
| 71fc9b0 | a4ba330 | 2026-11-22 combine-verdicts: majority over all verdicts when one answer sits in several folders |
| 7280319 | b2461da | 2026-11-21 run log: Memory-route timeouts and staggered resubmit; Phi and Qwen FP8 v9 figures traced to test 0 |
| 72bdc0a | 272ff74 | 2026-11-20 run_log: slow imports on Fir, local-disk fix; EiG waits for the key |
| 739ddc6 | 9ff13fe | 2026-11-22 LongMemEval retrieval comparison: five rule configs (G41, G47, G48, G39, G40), submit script; Memor |
| 7416708 | 74a7139 | 2026-11-21 Pre-fix runs marked: test 03 run-01 and test 04 run-02's 263 questions invalid; test 02 run-01 and  |
| 7cd51d3 | e2ad2cf | 2026-11-22 Hand override of lme-3c1045c8 (combine-verdicts --overrides, PROTOCOL 12, run-04-lme-maj3-hand); 20 |
| 7d2a6d9 | bc8900c | 2026-11-21 run log: LongMemEval labels progress, fc10713 failures, GRAFT pilot cost, judge spend estimate |
| 7ea6d95 | a155f35 | 2026-11-22 Docs cleanup (user): redirect notes removed, session docs markdown only (PDFs removed), hash manife |
| 7f88edd | f596a2f | 2026-11-21 strategy_router: LongMemEval items are read by their question (with date) behind a fixed history ma |
| 83a29eb | 70deabe | 2026-11-21 submit_longmemeval.sh: read shard numbers as decimal (08 and 09 failed as octal in printf) |
| 84d7512 | d68f670 | 2026-11-21 Project history of Flotilla and GRAFT, a study document: every test, decision, number (linked to it |
| 86f8264 | 9c11464 | 2026-11-21 run log: LongMemEval judged (Haiku, 5,000 verdicts kept, $0.18 with checks), hand check 96%, merge  |
| 8754774 | 3e5adc6 | 2026-11-21 PROTOCOL: status line names protocol-v10; v10 addendum: Haiku is the LongMemEval judge (official ju |
| 897339c | 75275fe | 2026-11-20 run_log: autonomy through router training and live RL |
| 8d813a2 | 024d6c0 | 2026-11-21 run log: run-04-lme merged (after the available-field fix), router training and the learning curve  |
| 927ff4e | 341ff4c | 2026-11-21 run log: WM round 2, T-REx bridge, guide extraction, old-commit resubmit |
| 9487bae | 63faa03 | 2026-11-21 run log: same-day confirmation (guide +12.0); spend $7.02 |
| 9b24634 | 2d61e46 | 2026-11-20 run_log: GRAFT full T-REx retrieval works; question layer and Qwen released |
| 9b6a291 | 616ef6f | 2026-11-22 Test 04 run-04: LongMemEval labels merged, judge hand check, four routers on run-04-lme (F29-F32: s |
| 9d556c3 | 6f1dbde | 2026-11-21 run log: test 06 guide extraction, dry check, arm B and bridge rerun submitted |
| 9f19f0d | 69063c8 | 2026-11-22 Pipeline diagram: Verifier card shows what is built (exact checks: maths, letters, code tests, inst |
| a40367d | eec1773 | 2026-11-20 run_log: GRAFT Haiku and Qwen jobs queued; router training waits for the Memory routes |
| a5fae33 | 3919439 | 2026-11-22 Toy gate for F37-F40 (S169): known-answer questions per route, full trace dumps, stop on any parse  |
| a79ebba | 8102fe9 | 2026-11-22 Format tests for every dataset: real raw rows per source in tests/data/formats (sampler script), co |
| aa91882 | 0cd226a | 2026-11-22 test-04: per tool, route and task type against the no-tool twin |
| ab3ea47 | d91a4b3 | 2026-11-22 GRAFT presets carry G IDs (plain_c G08, guide_b G35); test requires an ID per preset and only runti |
| ab4e2d1 | 4f9e161 | 2026-11-21 run log: GRAFT full T-REx not adopted (17-19% vs 34.7%); Qwen swap moved to the empty-start graph;  |
| ace3012 | ec1d433 | 2026-11-21 Cheapest route judged per row: strategy_labels labels by the row's own gpu_seconds (ties and rows w |
| b105b8f | 460078f | 2026-11-22 STATUS rows 27, 31; run log: majority-of-3 judge |
| b131501 | f4e50c5 | 2026-11-22 constraint_check reads only the question on tasks holding a chat history (new runs only; labels unc |
| b151c5f | 147bfce | 2026-11-21 run log: Qwen GRAFT job with the guide arm, Fir/Nibi twins |
| b2e697d | 0cb7a0f | 2026-11-22 G42 dropped (user): thinking used the 16,384-token cap on 336 of 358 extraction calls; jobs cancell |
| b537090 | 3bc3ca0 | 2026-11-21 lme_job: install openai into the unpacked GRAFT venv when missing (GRAFT's local Qwen backend needs |
| b65a88c | 875e1b5 | 2026-11-21 run log: test 06 arm E (not kept), spend $7.39; handoff updated |
| b786521 | 43f7738 | 2026-11-21 run log: Haiku traceability and fixed check |
| b7e38f5 | 9e96afd | 2026-11-20 run_log: first base-cleaning rule too wide, caught before use; narrowed rule rerunning |
| b84381b | 3bb0855 | 2026-11-21 HANDOFF and run log: Haiku is the LongMemEval judge; PROTOCOL status line fixed |
| ba6708c | 40bb4de | 2026-11-22 run log: Memory-route diagnosis, the user's plan and its first steps, router pickling failure and r |
| bbad573 | 9bfc961 | 2026-11-21 run log: LongMemEval route labels, setup decisions and pilot jobs |
| bc9eed8 | 2a1dcf0 | 2026-11-22 Registry: F06 checked against the saved runs (same build, vLLM settings, native tools, temperature  |
| c4bfbdb | eb1e5f0 | 2026-11-21 LongMemEval judge on Claude Haiku 5.5 (protocol-v10 addendum): anthropic SDK with raw response (req |
| c88433d | 6faa757 | 2026-11-22 G41 rebuild: 39 of 76 built before the time limit; rest resubmitted as 8 jobs; STATUS and run log |
| cad466d | 60a22d7 | 2026-11-21 Metric rule (user): match the comparison's metric; label learning-curve plan (not run until the rou |
| cc45587 | b492120 | 2026-11-22 Supersede check: match facts on subject, relation and object (not the source sentence); step 2 pass |
| cd26de9 | b509c63 | 2026-11-21 run log: Haiku baseline check jobs; cost guard fix; Qwen held |
| cdeb4dd | fd1aaee | 2026-11-21 Merge pull request #1 from MohamedKhalidmk/restructure |
| d17abcb | 6ade335 | 2026-11-21 run log: LongMemEval base-route pilots on MIG, shards submitted, Haiku judge wiring |
| d1a4dcd | 9a187c5 | 2026-11-22 STATUS row 5, run log: GRAFT test 09 scored |
| d23e9f2 | ea10823 | 2026-11-21 Supervised strategy routers (label and success ModernBERT, bge + logistic regression, kNN): routes  |
| d4060c2 | 8cee2f2 | 2026-11-22 test-04: what Haiku received for the 8 short-answer breaks; judge consistency over all verdicts |
| d5c1fce | 166bba4 | 2026-11-22 test-04: majority-of-3 Haiku labels (run-04-lme-maj3): 6 of 500 memory labels change; spend $0.283 |
| d71cec1 | 3dd7a7f | 2026-11-21 run log: arm D in parallel; guide B resubmitted |
| dbe28cf | ff000c3 | 2026-11-20 test 04 run-03: 263 affected questions rerun, all 1,450 labels regraded with the fixed verifier and |
| dc82563 | d5c9729 | 2026-11-22 run log: routers on run-04-lme and the learning curve; Dialogue NLI chosen, download and leakage ch |
| dd0693c | 1719200 | 2026-11-21 LongMemEval route labels: run-item shards (whole history, long_context; Memory shards with the same |
| deaeafc | a35e0d8 | 2026-11-21 run log: WM round 2 result; bridge OOM ($0) and cost guard fix; spend $6.53 |
| df0e69e | 47a6af1 | 2026-11-22 STATUS and run log: supersede toy results, writer bare-list bug, port clash and six reruns, G41 hel |
| e2e12bf | 4460abe | 2026-11-21 Label learning curve: bar set by the user before any result (100% must beat 75% by more than the sp |
| e8a03f8 | b021e2e | 2026-11-20 run_log: twin watcher bug, fixed |
| eb911a0 | dc735ea | 2026-11-21 run log: test 06 arm E submitted |
| ec2a888 | a9fa554 | 2026-11-22 Pilot submit script for F37-F40 and comparators (S170) |
| eca4695 | 3b3bcc9 | 2026-11-21 Live RL router: per-decision contextual bandit (ridge values over frozen features, prior from the s |
| f25a5e7 | 2d3d685 | 2026-11-22 test-04: constraint_check on instructions, memory answer length; judge temperature not supported (r |
| f6334b3 | 6da38d5 | 2026-11-22 strategy_router: when run with -m, register the module under its import name so LRRouter pickles (F |
| f6610ec | 056f142 | 2026-11-22 test-04: tool use on run-04's tool routes, by task type, against the no-tool twin |
| f75135e | e550e22 | 2026-11-21 run log and README: GRAFT test 06 (structure guide 45.7 vs 34.7, kept); spend $6.80 |
| fd7a8b4 | a14ecf7 | 2026-11-21 strategy_router: --train-frac/--frac-seed (nested stratified train fraction for the label learning  |
| fe4c520 | 665dc8b | 2026-11-22 test-04: why Vote+Tools broke 25 memory questions |
| fff2a82 | 53332e0 | 2026-11-20 run_log: grader fixes and reruns, older-model audit, GRAFT full T-REx retrieval bug |
