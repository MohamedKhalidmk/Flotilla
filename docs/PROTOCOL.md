# Flotilla evaluation protocol

Status: **FROZEN as protocol-v1 (2026-11-19).** This file is tagged `protocol-v1` in git; any change is a new version with a dated changelog entry, and results say which version they ran under.

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
Rule: **keep Command A+ if the system with it scores higher on the summed dev accuracy (equal weight per benchmark) than without it.** If dropped, MMMU and OCRBench use the vision fallback model from `notes/model_candidates.md`.

### 4.2b Phi (keep or drop)
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
Router A details (from `notes/benchmarks_components.md`): `vllm-project/semantic-router` v0.4.0, Apache-2.0, shipped as Docker; on the clusters it runs as an Apptainer image converted from that Docker image, CPU-only (about 12 GiB RAM), OpenAI-compatible endpoint. Decision model: `vela3-fast`, the router's current default (chosen 2026-11-19 over the superseded Decision 1.0 models). Python tools are exposed to it as model-style endpoints, the only routing target it supports.
Rule: **use the router with higher routing accuracy on the dev subsets**; ties go to the one with lower latency.

## 5. Leakage controls

- No benchmark test item, or near copy, in any graph, RAG corpus, prompt example, or router training set.
- Near-copy check: 13-gram overlap between every corpus document and every test item, plus embedding similarity above 0.95 flagged for manual review. Results saved in `reports/leakage/`.
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

## Changelog
- 2026-11-19: draft started.
- 2026-11-19: frozen as protocol-v1. Decisions recorded: CanLegal Bench and SWE-bench excluded, MemoryAgentBench only for the graph test; small test 5% with at least 20 per benchmark; Phi kept only if Qwen + Phi beats Qwen alone on the small test; router A uses vela3-fast; EiG-Search cleared by Prof. Lu.
