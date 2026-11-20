# Flotilla evaluation protocol

Status: **FROZEN as protocol-v8 (2026-11-19).** Each version is a git tag (`protocol-v1` to `protocol-v8`); any change is a new version with a dated changelog entry, and results say which version they ran under. No scored run used protocol-v1.

Flotilla is a compound system of quantized open models served with vLLM. This protocol fixes, before any scored run, what we measure, how, and how we decide between components, so that no choice is made after seeing test results.

## 1. Benchmarks

### 1.1 Final-run list (10)

| # | Benchmark | CQL publishes a number? | Notes |
|---|---|---|---|
| 1 | GSM8K | yes | |
| 2 | MATH-500 | yes | |
| 3 | AIME 2025 | yes | contamination dates recorded per model (exam: Feb 2025) |
| 4 | AIME 2026 | yes | exam: Feb 2026 |
| 5 | GPQA-Diamond | yes | |
| 6 | IFEval | yes | |
| 7 | MMMU (validation) | yes | needs a vision model |
| 8 | OCRBench | yes | needs a vision model |
| 9 | RULER | yes (GLM-5.2, 32K/64K) | reported with and without retrieval (retrieval changes what RULER measures) |
| 10 | LiveCodeBench | no CQL number | compared with published model-card numbers instead |

(AIME 2025 and 2026 are separate rows but one benchmark family: 9 benchmarks in all.)

### 1.2 Excluded, decided before any run

- **SWE-bench Verified**: excluded. Needs Docker per task; no cluster we can use allows Docker. Decided 2026-11-19, before any run.
- **CanLegal Bench**: excluded. Its data, prompts, harness and scorer are not public (open release listed as "coming next"), so it cannot be run. Decided 2026-11-19, before any run.
- **MemoryAgentBench**: excluded from the final run. Its FactConsolidation multi-hop split is used only for the graph-memory test (section 4.3).

### 1.3 Settings copied from CQL

From `notes/cql_settings.md` (every setting quoted there with its source). Rule for gaps: **target CQL's best published number for each benchmark, and copy the most completely documented CQL setting for it.** CQL published full settings mainly for its Hy3 and GLM-5.2 runs; the GLM-5.3-Flash text numbers come without harness, prompt or temperature.

| Benchmark | Target (CQL's best) | From | n | Harness | Sampling | Budget | Prompt | Metric | Gaps and how we fill them |
|---|---|---|---|---|---|---|---|---|---|
| GSM8K | 0.975 | GLM-5.3-Flash W4A16 (H100 / RTX PRO 6000) | 1,319 | lm-eval 0.4.12 `gsm8k` (Hy3 protocol) | greedy | non-thinking (Hy3); GLM-5.2 used 16,384 reasoning | 5-shot, chat template on | exact match, strict-match | GLM-5.3 settings unpublished: use the Hy3 protocol. The 0.99 "200-problem subset" is not a target (subset undefined). |
| MATH-500 | 0.954 | GLM-5.2 W4A16 (8x H200) | 500 | lm-eval or math-verify scorer | greedy | 131,072 thinking (Hy3); GLM-5.2 used 16,384 | 0-shot, chat template | accuracy via math-verify | Use 131,072 (the larger of CQL's two) so budget never limits us more than them. |
| AIME 2025 | 0.8833 (106/120) | GLM-5.3-Flash W4A16, H100 TP=4 | 4 x 30 | not published | temperature 0.0 (stated only for the matched AIME rerun) | 131,072 thinking, truncation scored wrong | not published | mean accuracy over 120 | Prompt and extraction unpublished: use lm-eval's AIME task prompt and math-verify; temperature 0 for single-model rows. |
| AIME 2026 | 0.850 (102/120) | GLM-5.3-Flash W4A16, 2x DGX Spark | 4 x 30 | as AIME 2025 | 0.0 | 131,072 | as AIME 2025 | as AIME 2025 | as AIME 2025 |
| GPQA-Diamond | 0.884 | Hy3 W4A16 (8x H100) | 198 | lm-eval 0.4.12 | greedy | 131,072, thinking high | 0-shot | accuracy, flexible-extract | Choice shuffling not stated: use lm-eval's `gpqa_diamond` default (fixed). GLM-5.3's 0.8586 also reported in the table. |
| IFEval | prompt-strict 0.909 (GLM-5.2); instruction-strict 0.929 (Hy3) | GLM-5.2 / Hy3 | 541 | lm-eval 0.4.12 `ifeval` | greedy | not stated: use 16,384 | chat template | prompt-strict and instruction-strict (loose not reported by CQL; we report all four) | none material |
| MMMU (val) | 0.74667 (672/900) | GLM-5.3-Flash W4A16, 8x H100 TP=8 | 900 | lmms-eval **pinned to 0.7.3** `mmmu_val` (0.7.4 changed MMMU parsing) | greedy, temp 0, seed 42 | not published: use lmms-eval task default | lmms-eval default; `reasoning_effort=low` | accuracy | Max tokens and image settings unpublished: lmms-eval 0.7.3 defaults. |
| OCRBench | 888 / 1000 | same run | 1,000 | lmms-eval 0.7.3 | greedy, seed 42 | default | default | score out of 1000 | as MMMU |
| RULER | 0.832 @32K, 0.841 @64K | GLM-5.2 W4A16 | 50 per sub-task per length | not published | not published: greedy | n/a | not published | mean over sub-tasks | Sub-task list and implementation unpublished: lm-eval `ruler` group (13 standard tasks) with `max_seq_lengths` 32768 and 65536 in `--metadata`, 50 samples per task per length (CQL's count; RULER's own default is 500), greedy, substring string-match, unweighted mean. Haystack and SQuAD/HotpotQA data downloaded on the login node. Reported with and without retrieval. Phi (32K context) runs 32K only. |
| LiveCodeBench | no CQL number | model cards | release_v6, window 2024-08-01 to 2025-05-01 (454 problems) | official `lcb_runner` (not lm-eval) | per LCB defaults | per LCB | per LCB | pass@1 on hidden tests | Compared with Qwen/Phi card numbers. All candidate Qwen models were released after this window: contamination possible, recorded per model. |
Hardware note: CQL's numbers come from 4 to 8 H100, H200, RTX PRO 6000 or DGX Spark. Ours run on H100 80 GB (Trillium, Fir). Hardware changes speed, not the scored answers, except through numerical differences that CQL itself measured (AIME 2025: 0.883 on H100 vs 0.808 on RTX PRO 6000).

## 1.4 Models (from `notes/model_candidates.md`, checked 2026-11-19)

| Role | Model | Size / context | License | Serving build | Release vs AIME 2025 / 2026 |
|---|---|---|---|---|---|
| Solver (general, code, math) | `Qwen/Qwen3.8-27B` | 27B dense / 262K | Apache-2.0 | `RedHatAI/Qwen3.8-27B-INT4` (W4A16) or official FP8, plus our own builds | after both: may have seen both |
| Solver (math, second voter) | `microsoft/Phi-4-reasoning-plus` | 14B / 32K | MIT | `nvidia/...-FP8`, `amd/...-w4a16-llmcompressor`, plus our own builds | cutoff Mar 2025: may have seen 2025, clean on 2026 |
| Vision + generalist (on test) | `CohereLabs/command-a-plus-05-2026` | 218B MoE, 25B active / 128K | Apache-2.0 | official FP8 for the test; our W4A16 if kept | after both |
| Vision fallback | `Qwen/Qwen3.6-27B` | 27B / long | Apache-2.0 | official FP8 | after both |

AIME results are reported per model with this contamination column; Phi's AIME 2026 row is the cleanest reference.

## 2. Splits

- Every benchmark gets a **small test (dev) subset** and a **test set**, fixed by a seeded random draw (seed 20261119) and written to `configs/splits/` before any run. Small test: **5% of items, at least 20 per benchmark** (decided 2026-11-19).
- All tuning (router training checks, prompt changes, N, thresholds, tool rules) uses **dev only**.
- Reported numbers are on the **full benchmark** as CQL ran it, so they stay comparable. Because the dev items are part of the full set, the report also gives the score on test-only items (full set minus dev) next to it, so any dev overfitting shows.
- Resulting small-test sizes: GSM8K 66, MATH-500 25, AIME 2025 20 of 30, AIME 2026 20 of 30, GPQA-Diamond 20, IFEval 27, MMMU 45, OCRBench 50, RULER 33 per length (5% of 13 tasks x 50), LiveCodeBench 23. On AIME the minimum of 20 is two thirds of the exam, so the AIME test-only score rests on 10 problems per year; both numbers are reported.

## 3. Metrics and statistics

- Primary metric per benchmark: exactly the metric CQL reports (section 1.3).
- 95% confidence intervals by bootstrap over items (10,000 resamples). For repeated-sample protocols (AIME 4 x 30), resample problems, keeping repeats together.
- A "win" over a CQL number is claimed only if our lower CI bound is above CQL's point estimate. Otherwise it is reported as a tie or a loss.
- Compute, reported next to every accuracy number: total tokens (prompt and generated, every model, every loop step), GPU-hours, peak GPU memory, wall-clock time, per question and per benchmark.

## 4. Decision rules (fixed now, applied mechanically later)

### 4.1 Quantization (per model)
Benchmark: MATH-500 dev+test (full 500), same settings as section 1.3.
Variants: BF16 (reference), 8-bit (W8A8 FP8), 4-bit (W4A16 GPTQ).
Rule: choose **4-bit if its accuracy is at most 1.0 point below 8-bit**; otherwise 8-bit. Throughput (vLLM, CQL's conventions: 8192/1024 tokens, concurrency 1/8/32) is reported but does not decide.

### 4.2 Command A+ (keep or drop)
Small test: dev subsets of all final-run benchmarks, including MMMU and OCRBench dev items.
Rule (protocol-v5, 2026-11-19, replaces the v1-v4 rule before any Command A+ result existed): **keep Command A+ only if Command A+ alone beats the better of Qwen alone and Qwen + Phi on the small test by a clear margin.** Score = mean over benchmarks of each benchmark's own metric (equal weight; RULER uses its mean sub-task score). "Clear margin" = the 95% lower bound of a paired bootstrap of the difference (10,000 resamples of items, stratified by benchmark, same items for both systems) is above 0. If dropped, MMMU and OCRBench use the vision fallback model from `notes/model_candidates.md`.
Screen first, then local: the small-test screen runs Command A+ through Cohere's hosted API on a free trial key (`command-a-plus-05-2026`, thinking on via `reasoning_effort="high"`, 20 calls per minute, 1,000 calls per month, run capped at 900 calls; no paid credits). The hosted model may differ from the open weights, so it is a screen: only if it passes is the official FP8 served locally, re-checked on the same small test, and given router labels. All three configurations run the same Flotilla loop (solver v1, verifier v2, tools, N = 1, `max_tokens` 32,768, Phi capped at 24,576 by its 32K context), routed by each item's known task type with the decision table, so they differ only in models (`configs/systems/`, `flotilla/smalltest.py`).
Analysis also reported: per benchmark and task type, items only one model got right, both, neither, and the perfect-router score (`flotilla/oracle.py`).

### 4.2b Phi (keep or drop)
**Superseded by protocol-v9 (2026-11-19): Phi is dropped and gpt-oss-20b at medium reasoning effort takes its place; see the changelog.**
Decided 2026-11-19: **keep Phi-4-reasoning-plus only if Qwen + Phi together beats Qwen alone on the small test** (summed small-test accuracy, equal weight per benchmark). Background: on every benchmark both cards report, Phi is far below Qwen3.8-27B, and its 32K context excludes it from RULER 64K. It may still help as a second voter, and it is the only candidate whose stated data cutoff (March 2025) predates AIME 2026.

### 4.3 Graph memory: EiG-Search
Test: MemoryAgentBench FactConsolidation multi-hop, 262K, 100 questions, the saved real-run graph from GRAFT (`MohamedKhalidmk/SGAR`, run exp_a_real_mh_262k), Claude Haiku 5.5 answering with a 256-token limit, exactly as the GOAt result (37, strict 36; A, B, C tied at 37 to 38).
Implementation: EiG-Search from `github.com/sluxsr/EiG-Search` (training-free, O(|E|), returns edge importance and an edge-induced subgraph). Its code has no license file and pins PyG 2.1 / torch 1.11, so we port our GCN weights into its model classes or re-implement its edge-attribution step on the 3-hop subgraph with an `edge_weight` input; use cleared by Prof. Lu (2026-11-19).
Rule: **use EiG-Search if its score is at least 37 and its retrieval time per question is lower than GOAt's (2.7 s), or if its score is at least 40.** Otherwise keep GOAt. No GOAt rerun.

### 4.4 Voting N
After the compound system exists: generate 5 samples per dev item once, then score N = 1, 3, 5 from those same samples.
Rule: **choose the smallest N whose summed dev accuracy is within 0.5 points of the best.**

### 4.5 Router
Both routers are built: A = vLLM Semantic Router, B = our trained classifier. Router B is trained only on non-test data (section 5).
Router A details (protocol-v4): the vLLM Semantic Router's decision model `vllm-sr/vela3-fast` (Apache-2.0, 380M decision backbone; chosen 2026-11-19 over the superseded Decision 1.0 models) classifies each task's type with a "choice" question over our task types, and a fixed decision table maps task type to solver models and Python tools (`flotilla/router_a.py`). Images and very long inputs are routed by rule. The full `vllm-sr` product (router, Envoy, dashboard, v0.4.0) was converted to Apptainer but needs Docker-style services and asset downloads at start, which the offline compute nodes do not allow; its decision model is the component that makes the routing decision, so router A uses it directly. Router A's routing accuracy is measured on 500 clean router-pool items with known task types (`reports/router_a_pool500.json`).
Rule: **use the router with higher routing accuracy on the dev subsets**; ties go to the one with lower latency.

## 5. Leakage controls

- No benchmark test item, or near copy, in any graph, RAG corpus, prompt example, or router training set.
- Near-copy check: 13-gram overlap between every corpus document and every test item, plus embedding similarity above 0.95 flagged for manual review. Results saved in `reports/leakage/`.
- Template wording is not a copy (protocol-v3 clarification): a 13-gram found in 2 or more different test questions, or in 3 or more pool items, is shared template wording (e.g. AIME's "m and n are relatively prime positive integers", IFEval's constraint templates) and is ignored. For code problems the 13-gram check compares only the problem statement (constraint lines and sample I/O repeat across unrelated problems); the embedding check still uses the full text. Every flagged item is dropped, including false positives. The strict count without these filters is reported next to the result.
- Router B training data: benchmark train splits only (GSM8K train, MATH train excluding MATH-500 items, AIME 1983 to 2024, other public sets listed in `configs/router_train.yaml`), deduplicated against every test set with the same check.
- Model contamination is recorded, not fixed: each model's release date and stated data cutoff against each benchmark's release date.

## 6. Claude's role

- Claude never feeds anything into Flotilla's answers.
- Small tests: Claude checks every output (correct or not, and the failing stage).
- Final run: official graders decide correctness; Claude only assigns error stages to wrong answers and answers a fixed subset as a reference row.
- API spend is estimated and approved before each Claude run.

## 7. Traces (every question, every run)

One JSON line per question in `runs/<run_id>/trace.jsonl`:
`run_id, protocol_version, prompt_versions, benchmark, item_id, split (dev/test), router {decision, scores, latency}, tools [{name, input, output, ok}], models [{name, quant, samples [{text, final_answer, tokens_in, tokens_out, latency}]}], retrieval {method, items, latency}, vote {candidates, winner}, verifier {verdict, reason}, final_answer, correct, error_stage, tokens_total, gpu_seconds, wall_seconds`.

Error stages (assigned automatically where possible, by Claude otherwise):
router_wrong_model (another model's sample was right), retrieval_miss, reasoning_error, vote_wrong (a correct sample existed but lost), verifier_false_accept, verifier_false_reject, format_parse_failure, timeout_or_oom.

## 8. Compute accounting

Every vLLM server logs token counts per request; every Slurm job records GPU count, elapsed time and peak memory (`sacct`, `nvidia-smi`). GPU-hours = GPUs x elapsed hours for every job, including failed and repeated jobs, which are listed in the report.

## 9. Prompts and output format

Every role (router, each solver, cross-checker, verifier, judge) has a versioned prompt in `prompts/` with its purpose, input, and output schema. Models reason in free text and end with one JSON block (`final_answer`, `confidence`, `sources`). Baseline single-model rows use each benchmark's standard prompt so they stay comparable with CQL. See `docs/PROMPTS.md`.

## 10. Verifier retry (protocol-v2)

When the verifier rejects the voted answer, the system retries once (`prompts/verifier.v2.md`). The retry message tells the model its previous answer was wrong and includes the previous answer, the failed checks with their details (e.g. the failing test or the parse error) and the verifier's reason. The retry's answer is returned whatever its verdict. Both attempts are logged in the trace under `verifier.attempts` (attempt number, final answer, verdict, every check with detail, and the retry message sent).

## Changelog
- 2026-11-19: draft started.
- 2026-11-19: frozen as protocol-v1. Decisions recorded: CanLegal Bench and SWE-bench excluded, MemoryAgentBench only for the graph test; small test 5% with at least 20 per benchmark; Phi kept only if Qwen + Phi beats Qwen alone on the small test; router A uses vela3-fast; EiG-Search cleared by Prof. Lu.
- 2026-11-19: protocol-v2. Verifier retry changed (section 10, `prompts/verifier.v2.md` replaces v1): the retry prompt now tells the model its previous answer was wrong and includes the verifier's reason and failed checks; both attempts are logged. Requested by the user before any scored system run.
- 2026-11-19: protocol-v3 (clarification of section 5). The 13-gram leakage check ignores template wording and, for code, compares problem statements only; the strict check had flagged 648 of 4,856 router-pool items, almost all shared templates. Result: 96 flagged and dropped (including real overlaps such as an old AIME problem that is also in MATH-500), 4,760 kept. All test sets checked, including GPQA-Diamond (0 overlaps with the MMLU-Pro science questions).
- 2026-11-19: protocol-v4 (implementation of router A, section 4.5). Router A runs the vLLM Semantic Router's decision model vela3-fast directly plus a fixed decision table, instead of the full vllm-sr service stack, which cannot run on the offline compute nodes.
- 2026-11-19: protocol-v5 (section 4.2, decided by the user before any Command A+ result). Command A+ is kept only if it alone beats the better of Qwen alone and Qwen + Phi on the small test by a clear margin (paired bootstrap lower bound above 0); screened on Cohere's hosted API with a free trial key, then served locally from the official FP8 only if it passes. Small-test configurations share one loop and max_tokens (32,768). Answer parsing switched from a regex to a JSON decoder so answers containing braces (code) parse; this changes no scored result (none existed).
- 2026-11-19: protocol-v6 (implementation of the Command A+ screen, before any Command A+ result was scored). Cohere's compatibility API rejects the request (422) when Command A+ emits a tool call and the request lists no tools, so the model could not use the Flotilla tools and those items failed; a first screen run was stopped after 116 calls and discarded (kept in `runs/cmda-smalltest`, not scored). Command A+ now receives the same three tools (sympy, python_exec, constraint_check) through native function calling (`native_tools`), and its system instructions are sent with role `developer` (Cohere's convention). The prompt text is unchanged; vLLM models keep the text TOOL-line protocol. Fixed with it: the verifier retry now shows the model its previous turn (cut to its last 8,000 characters) before the retry note, and the tool loop no longer overwrote the server name with the tool name.
  RULER items (`flotilla/export_ruler.py`, lm_eval 0.4.11+computecanada, Qwen tokenizer): the full `ruler` group is rebuilt with lm-eval's own seeds for lengths 32768 and 65536 and the first 50 samples per task per length are kept (lm-eval has no sample-count option); dev draw uses the per-benchmark seed rule of `flotilla/splits.py`. lm-eval's HotpotQA host no longer resolves, so `hotpot_dev_distractor_v1.json` was taken from the Wayback Machine (7,405 questions, sha256 recorded in the script's cache folder; not checked against an official checksum).
- 2026-11-19: protocol-v7 (tool loop, before any scored run). When the tool budget (3 rounds) is used up, the last call carries a note that no more tools are available and the final answer is due; before this, a model that kept calling tools ended with no answer (32 of 113 Command A+ items in the second screen run, which is discarded, not scored). The native sympy tool description now says it takes one expression, not a program. The trial key's 1,000 calls per month cannot cover the full Command A+ screen at the measured 4.5 calls per item (652 used).
- 2026-11-19: protocol-v8 (section 4.2, decided by the user before any Command A+ result was scored). The hosted-API screen is dropped: the trial key's monthly calls cannot cover it. Command A+ runs the small test directly from the official FP8 (`CohereLabs/command-a-plus-05-2026-fp8`) on 4 H100s with vLLM 0.32 (cohere_command4 tool and reasoning parsers, thinking on as the template default), through the same loop as Qwen alone and Qwen + Phi (`configs/systems/cmda_local.json`, `flotilla/serve.py`). The clear-margin rule is unchanged.
- 2026-11-19: protocol-v9 (sections 1.4, 4.2, 4.2b; decided by the user). Phi-4-reasoning-plus is dropped. `openai/gpt-oss-20b` (Apache-2.0, native MXFP4 weights, 131K context, text only) takes its place at `reasoning_effort="medium"`. Basis, MATH-500 small test (25 dev items, greedy): gpt-oss-20b low 23/25 (701 output tokens on average, 0 at the cap), medium 24/25 (2,480, 0), high 21/25 (7,232, 4 of 25 at the 32,768 cap); Phi-4-reasoning-plus FP8 21/25 (24,354 tokens, 18 of 25 at its 30,000 cap). Qwen FP8 got all 25, so this set cannot show complementarity. Next step: Qwen alone, gpt-oss-20b alone and Command A+ alone run the same small-test items through the same loop (solver v1, verifier v2, tools, N = 1, `max_tokens` 32,768), and the report gives per benchmark the items only one model got right, all, none, and the perfect-router score against Qwen alone (`flotilla/oracle.py`). gpt-oss-20b has no image input, so MMMU and OCRBench are not run for it (reported as n/a). The Command A+ keep rule (4.2) now compares Command A+ alone with Qwen alone. Router labels for router B: the first Qwen and Phi label runs are not used (answer extraction failed on many items; Phi produced no parsed answer at all); they are rerun after the cause is found.
- 2026-11-20: protocol-v9 addendum (before any small-test result was scored). All three models call tools through native function calling (vLLM tool parsers: `qwen3_coder` for Qwen, `openai` for gpt-oss-20b, `cohere_command4` for Command A+). With the text TOOL-line protocol, gpt-oss returned empty answers when it called a tool in its own format, and Qwen sent multi-line code as a one-line text tool call and used 77,546 tokens without answering a LiveCodeBench smoke item. Groups that use tools (math, mixed) are rerun for Qwen; vision and long-context groups offer no tools and are kept. Job servers now use a free port each (jobs sharing a node had reached each other's servers on port 8000; affected requests failed with 404 and were rerun, none was scored).
- 2026-11-20: protocol-v9 addendum 2 (before any small-test result was scored). With native function calling, the solver prompt's TOOL-line sentence is replaced by a native-tool wording kept in the same prompt file (`prompts/solver.v1.md`, section "Native-tool wording"); smoke checks showed both models still writing TOOL lines as text otherwise. On the forced last round, native servers get `tool_choice: none`. The smoke check treats an item with no answer because every sample used the whole token budget as allowed (reported), since that is the model running out of budget, not a pipeline failure.
- 2026-11-20: rule 4.1 applied to Qwen3.8-27B. MATH-500 (all 500, 131,072-token budget, greedy): BF16 0.978, FP8 (ours) 0.984, W4A16 (ours, GPTQ, ultrachat_200k calibration) 0.984 (2 of 500 at the cap, 2,136 s on one H100), RedHat INT4 0.988 (reference). Our W4A16 is 0.0 points below our FP8, inside the 1.0-point margin, so Qwen is served as W4A16 (`quant/qwen3.8-27b-w4a16`). Calibration leakage check (`flotilla/calib_pool.py` + `flotilla/leakage.py`): the 512 calibration conversations (3,132 messages) share no 13-gram with any test set and none has embedding cosine >= 0.95 to a test item (0 flagged; 0 also without the template filter).
