# CQL (Canada Quant Labs) published evaluation settings

Compiled 2026-11-19 from public sources only (list at the end). Every setting below is quoted or paraphrased from a named file or page. Where CQL did not publish something, it is listed under GAPS, not guessed. "Not published" means it was not found in any public file read. "CQL" below means canada-quant / cql.ca.

Key access facts:
- Several CQL docs that hold full protocols are NOT public: `docs/VISION_EVALS.md`, `bench/vision/raw/`, `bench/h2h/H100_COMPETITOR_COMPARISON_2026-09-28.md` ("in the source repo"), and the hy3 "companion repo" `docs/RUNLOG.md`. GitHub `canada-quant/hy3-w4a16-mtp`, `canada-quant/glm-5.3-w4a16-mtp`, `canada-quant/GLM-5.3-Flash-W4A16-MTP`, `canada-quant/glm-5.2-w4a16-mtp` all return 404. GLM-5.3 BENCHMARKS.md says: "raw logs and scripts are available to collaborators on request."
- `github.com/canada-quant/vllm-glm53-flash-sm121/drafter/` is public but contains only the drafter acceptance-length eval kit (`drafter/eval/holdout_client.py`, `prompts_holdout_500.jsonl`, `drafter/all/*.json`), not any of the quality benchmarks below.
- The only public, machine-readable lm-eval configs from CQL are in the DeepSeek-V4 GitHub repos (GSM8K, IFEval). They are a different model family, included in an appendix because they show CQL's default lm-eval habits.
- All pages fetched successfully (HTTP 200); nothing was unreachable except the 404 companion repos above.

Abbreviations: GLM53 = canada-quant/GLM-5.3-Flash-W4A16-MTP; GLM52 = canada-quant/GLM-5.2-W4A16-MTP; HY3 = canada-quant/hy3-w4a16-mtp.

---

## 1. GSM8K

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| 0.9704–0.9750 ("0.970–0.975") | GLM53 | H100 and RTX PRO 6000 | GLM53 README "Quality" table; BENCHMARKS.md "Quality — full results" |
| 0.99 "(200-problem subset)" | GLM53, H200 TP=4 MTP N=2 recipe | 4x H200 | BENCHMARKS.md: "The GSM8K score on this exact recipe on H200 is 0.99 (200-problem subset)." |
| 0.97 | GLM53 | not stated | cql.ca/news/glm-5-3-w4a16-mtp: "GSM8K: 0.97 — parity with the FP8 baseline (quant-insensitive)." |
| 0.960 (strict); FP8 baseline 0.955 | GLM52 | 8x H200 | GLM52 README "Evaluation — vs the FP8 baseline" |
| 0.948 | GLM52 | 8x RTX PRO 6000 | GLM52 README "Serving on Blackwell" |
| 93.6% (5-shot, strict-match); FP8 93.0% | HY3 | 8x H100-SXM, vLLM 0.25.1 | HY3 README "Quality" |

### Settings published
- **GLM53**: no harness, shot count, metric filter, sampling, or token budget published. Only "GSM8K | H100 and RTX PRO 6000 | 0.9704–0.9750". Subset: the 0.99 is explicitly a "200-problem subset"; which 200 problems is not published. The 0.97 figures do not state n.
- **GLM52** (README): "Measured against `zai-org/GLM-5.2-FP8` under an identical setup (generative tasks via chat-completions with a 16,384-token generation budget for the reasoning CoT; matched serve config with `--reasoning-parser`). Quality is measured with speculative decoding off". Metric label: "GSM8K (strict)". Harness/version, shots, temperature: not published.
- **HY3** (README "Quality"): "using **lm-eval 0.4.12** through vLLM's OpenAI-compatible endpoints. Generation tasks are greedy (temperature 0), with the chat template applied; speculative decoding is **off** for quality runs ... GSM8K is 5-shot". Metric: "GSM8K (5-shot, strict-match)". Thinking: non-thinking ("default no_think — the tables above are the conventional non-thinking protocol"). Noise quoted: "GSM8K ±0.65 pp".

---

## 2. MATH-500

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| 0.954 (math-verify); FP8 0.958 | GLM52 | 8x H200 | GLM52 README |
| 0.954 math-verify | GLM52 | 8x RTX PRO 6000 | GLM52 README "Serving on Blackwell" |
| 94.0% (math_verify); FP8 93.4%, cyankiwi AWQ 95.2%, AngelSlim GPTQ 93.4% | HY3 | 8x H100-SXM, vLLM 0.25.1 | HY3 README "Reasoning mode" table |
| GLM53: not reported | — | — | — |

### Settings published
- **GLM52**: "MATH-500 (math-verify)"; chat-completions, "16,384-token generation budget for the reasoning CoT", `--reasoning-parser`, spec-decode off. Harness, temperature, prompt: not published.
- **HY3**: "runs **thinking=high** (0-shot, 14k-token generation budget, `\boxed{}`/letter-grading via math_verify, identical template/harness/server settings for every model, spec-decode off)" then superseded: "All rows: 0-shot, thinking=high, **native 256K context (`max_model_len` 262144), 131,072-token generation budget** — uniform for every model ... (Earlier 14k/32k-budget runs are superseded". Noise: "MATH-500 ±1pp". Thinking is set via the template knob: "`reasoning_effort` ∈ no_think/low/high".
- Equivalence checker: `math_verify` (HY3) / "math-verify" (GLM52). Version not published.

---

## 3. AIME 2025

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| **0.8833 (106/120)** | GLM53 | H100 TP=4, MTP | BENCHMARKS.md "Quality — full results" |
| 0.8083 / 0.8000 (two pooled arms) raw; 0.8833 with commit-hook fix (0.8917 hook-credited) | GLM53 | RTX PRO 6000 TP=4, MTP | BENCHMARKS.md |
| 0.783 (superseded, drafter-corruption bug vLLM #54374) | GLM53 | H100 | BENCHMARKS.md |
| NVFP4 comparison 0.9000 (H100) | NVIDIA NVFP4 | H100 | news/glm-5-3-w4a16-mtp; news/glm-5-3-flash-h100-nvfp4-vision |
| 83.3% (n=30); FP8 90.0% | HY3 | 8x H100 | HY3 README |

### Settings published
- **GLM53**: "AIME 2025 — n=120 (4×30), max thinking, 131,072-token budget" (BENCHMARKS.md). Post: "4 epochs × 30, max thinking, 131,072 budget." Spec decode was ON (MTP) for the H100 number ("H100 TP=4, MTP"). The RTX PRO fix: "a whole-trace commit hook plus a 98,304-token thinking-budget force-commit ... It is not part of the published recipes." Empty-answer rate on RTX PRO: "EMPTY-answer rate 11.7–14.2%".
- "max thinking" interpretation: the GLM53 `chat_template.jinja` (HF repo) sets `effective_reasoning_effort = reasoning_effort if ... in ['low','high'] else 'max'`, i.e. the template default is Max. CQL does not state the request parameters used; this is my reading of the template file, not a CQL statement.
- Temperature: not stated for AIME 2025 specifically. (For AIME 2026 the post says "temp-0.0"; see below.)
- **HY3**: 0-shot, thinking=high, 131,072-token generation budget, `max_model_len` 262144, `\boxed{}` graded via math_verify, spec-decode off, n=30. "AIME24/25 are n=30 each (±7–9pp stderr)". Budget sensitivity: "14k → 33/23%; 32k → 53/57%; **131k → 70/83%**".

---

## 4. AIME 2026

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| **85.0% (102/120)**; epochs 28/25/26/23 of 30 | GLM53 + incoai DFlash2 drafter, 1M serve | 2x DGX Spark (GB10, SM121), TP=2 | BENCHMARKS.md; news/glm-5-3-w4a16-mtp |
| EXL3 (MiaAI-Lab) 80.0% (96/120), epochs 25/25/24/22 | EXL3 quant | 2x DGX Spark | BENCHMARKS.md |
| 24/30 · 22/30 (n=30, max thinking) | GLM53 | RTX PRO 6000 · H100 | BENCHMARKS.md |

### Settings published
- "AIME 2026 — n=120 (4×30), max thinking, 131,072-token budget | 2× DGX Spark, DFlash2" (BENCHMARKS.md).
- Temperature: news/glm-5-3-w4a16-mtp, "What's next": "EXL3 quality arm: queued ... — identical temp-0.0 / 131,072-token / n=120 config". This is the only place CQL states AIME temperature; it implies temp 0.0 for the GLM53 AIME 2026 run (four epochs at temp 0 still differed, 28/25/26/23).
- Drafter: BENCHMARKS.md: "1M on 2× Spark is validated with the incoai drafter only; the AIME 2026 85.0% result was measured on that stack (speculative decoding does not change outputs)."
- Truncations scored as wrong: "16 are budget-exhaustion truncations, 2 are genuine wrong answers"; EXL3 "23/120 rows hitting the token cap, scored as written under the identical config."
- Note a contradiction in CQL's own sources: the 4 Sep post said the matched EXL3 AIME arm was "NOT RUN (owner pause)", while BENCHMARKS.md (later) reports EXL3 80.0% "matched protocol".

---

## 5. GPQA-Diamond

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| 0.8586 · 0.8586 | GLM53 | H100 · RTX PRO 6000 | BENCHMARKS.md / README |
| 88.4% (flexible); FP8 89.9% | HY3 | 8x H100 | HY3 README |

### Settings published
- **GLM53**: "GPQA-Diamond — n=198 @131K". Post: "GPQA-Diamond n=198 @131k: within noise of NVFP4 on both SM90 and SM120." Nothing else (no thinking level, temperature, prompt, extraction, shuffling, repeats).
- **HY3**: same reasoning protocol as MATH-500 (0-shot, thinking=high, 131,072 budget, spec off). "GPQA is flexible-extract." Grading: "`\boxed{}`/letter-grading via math_verify". Noise: "GPQA n=198 ±2pp".
- Choice shuffling: not published for either.

---

## 6. IFEval

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| 0.909 / 0.911 (prompt-strict / inst-strict); FP8 0.891 / 0.903 | GLM52 | 8x H200 | GLM52 README |
| 0.909 / 0.920 | GLM52 | 8x RTX PRO 6000 | GLM52 README |
| 89.7% / 92.9% (prompt-strict / inst-strict); FP8 90.2% / 93.1% | HY3 | 8x H100 | HY3 README |
| GLM53: not reported | — | — | — |

### Settings published
- **GLM52**: chat-completions, 16,384-token generation budget for reasoning CoT, `--reasoning-parser`, spec-decode off. Only strict metrics reported (prompt-level strict, instruction-level strict). Loose metrics, thinking on/off, harness: not published.
- **HY3**: lm-eval 0.4.12, OpenAI-compatible endpoint, greedy temperature 0, chat template applied, spec-decode off, non-thinking (default no_think). Only strict metrics reported. Noise: "IFEval ±≈1.3 pp".

---

## 7. MMMU

### Reported numbers
- **0.74667 (672/900)**, MC 0.766 · open 0.434. GLM53, 8x H100 TP=8, spec-off, measured 2026-09-28. NVIDIA NVFP4 on same rig: 0.680 (news/glm-5-3-flash-h100-nvfp4-vision).

### Settings published
- BENCHMARKS.md: "MMMU (validation) — n=900, lmms-eval 0.7.3 task spec | 8× H100 TP=8, spec-off, greedy".
- BENCHMARKS.md: "lmms-eval 0.7.3 task specs + installed scoring functions, greedy temp 0, seed 42; `reasoning_effort=low` via the template's native knob". Image: "8×H100 closeout stack" = `ghcr.io/canada-quant/vllm-glm53-flash-h100:v2-w4a16-dflash2` (vLLM dev516 + FA3 sparse-MLA, block 64).
- Post: "We ran the lmms-eval 0.7.3 task specs on the 8× H100 stack (TP=8, spec-off, greedy, seed 42)".
- Full protocol in `docs/VISION_EVALS.md` + `bench/vision/raw/` "in the source repo" (not public).
- Wording "task specs + installed scoring functions" suggests the prompts/scoring came from lmms-eval but generation may have been driven by CQL's own client against the vLLM server; not stated explicitly.

---

## 8. OCRBench

### Reported numbers
- **888 / 1000**. Weakest: handwritten math 56/100; strongest: doc-VQA 192/200. GLM53, 8x H100 TP=8, spec-off, 2026-09-28. NVIDIA NVFP4 on same rig: 882.

### Settings published
- Same as MMMU: "OCRBench — n=1000, lmms-eval 0.7.3 task spec", greedy temp 0, seed 42, `reasoning_effort=low`, TP=8, spec-off.

---

## 9. RULER

### Reported numbers
| Number | Artifact | Hardware | Source |
|---|---|---|---|
| @32K 0.832; @64K 0.841 (FP8: 0.831 / 0.813) | GLM52 | 8x H200 | GLM52 README; news/glm-5-2-w4a16-mtp |
| @32K 0.918; @64K 0.826 | GLM52 | 8x RTX PRO 6000 | GLM52 README |

### Settings published
- Context lengths: 32K and 64K only.
- Samples: "RULER used 50 samples per sub-task, not the full 500." (GLM52 README).
- Same eval framing as the other GLM52 tasks ("same harness", spec-decode off).
- Which RULER sub-tasks (13 standard? subset?), aggregation (mean over tasks?), RULER harness (NVIDIA RULER repo vs lm-eval `ruler` task), tokenizer used for length, thinking on/off: not published.
- Separate long-context sanity (not RULER): needle retrieved from ~936K-token prompt on 8x H200; 64K needle at mid and end placement on 4x H200.

---

## 10. CanLegal Bench

CQL's own benchmark. Public leaderboard only; data, harness and scoring code are not released ("Not yet reproducible by you. Until the open evaluation release ships, the data, harness and scoring code are not public", news/canlegal-bench-leaderboard). No CQL quant (GLM53 etc.) appears on the board; only API frontier models plus Cohere Command A+.

### Reported numbers (canlegalbench.com, v0.8.3, scoring version 2026-10-09, read 2026-11-19)
| Model | Suite mean | 95% CI |
|---|---|---|
| Claude Fable 5 | 80.4% | 79.2–81.6 |
| GPT-5.6 Sol | 78.2% | 77.0–79.3 |
| Gemini 3.1 Pro | 77.5% | 76.4–78.6 |
| Grok 4.5 | 71.6% | 70.3–72.9 |
| Cohere Command A+ | 49.8% | 48.2–51.3 |
(The 8 Oct blog snapshot differs slightly: 80.1 / 78.1 / 77.5 / 71.7 / 49.5. The post says "The live board at canlegalbench.com is authoritative.")

### Settings published
- Size: 14,547 frozen scored records, 17 task types, 14 jurisdictions, 30.8% French (10,062 EN / 4,485 FR).
- Protocol: "closed-book evaluation · no tool use · no RAG injection" (/about). "Same prompts, same frozen record set for every model." (blog)
- Headline metric: "Suite Mean ... is an unweighted macro mean over all 17 task types"; judge-scored tasks at strict accuracy ("a record counts only at full credit, verdict 1.0"); lenient (verdict >= 0.5) shown beside. Issue Spotting: "a record counts when every key issue is identified; additional issues are not penalized." Citation Resolution: "a declined answer earns no credit".
- Structured tasks: "Exact-match with alias-aware scoring ... Word-overlap fallback at threshold 0.45 for multi-word answers." (/about)
- Failures: "Network failures (empty outputs from API timeouts) count as wrong"; empty/budget-exhausted outputs scored 0 and stay in denominator.
- Judges (/transparency): Statute QA and Bijural Equivalence `qwen3.8-27b-i53f6qqg-semantic-full-v2`; Regulation QA `qwen3.8-27b-i53f6qqg-regv2-element-v1`; Tribunal QA `qwen3.8-27b-tribv32-disposition-v1`; Citation Holding `claude-sonnet-5-semantic-v2`; Issue Spotting `claude-sonnet-5-issue-set-v1`; all other tasks deterministic scorers with dated versions (e.g. `citation_lookup_score@2026-10-08`). "LLM-judge human validation: PENDING".
- Uncertainty: per-cell Wilson 95% CI; suite-mean CI by "parametric-binomial-bootstrap — 100,000 replicates, fixed seed".
- Per-model generation config (canlegalbench.com/models/<id>):
  - Claude Fable 5: adaptive thinking always on; "Effort set to max on 13 of the 17 tasks; on Citation Lookup, Citation Holding, Limitation Periods and Issue Spotting no effort setting is sent"; max output tokens 32,768; temperature not sent (API default).
  - GPT-5.6 Sol: reasoning effort xhigh; max output tokens 32,768; temperature not sent.
  - Gemini 3.1 Pro: always-on thinking; max output tokens 32,768; temperature not sent ("API default (1.0)").
  - Grok 4.5: reasoning effort high; max output tokens 32,768; temperature not sent ("API default (1.0)").
  - Cohere Command A+ (self-served via vLLM with reasoning parser): "temperature 0.6, top_p 0.95; seed 20261007 recorded"; max_tokens 65,536, then re-run of budget-exhausted records at 131,072, then at the model maximum (200,000 minus prompt); "The earlier temperature-0 cells are archived."
- Single sample per record (no repeats) is implied by "Correct / Records" counts; not stated explicitly.

---

## 11. SWE-bench Verified (excluded, brief)

- GLM52: 82.0% (410/500), FP8 82.2% (411/500), 8x H200. Setting: "SWE-bench Verified (mini-SWE-agent + official grading)". mini-SWE-agent version, step limit, cost limit, sampling, token budget: not published.

---

## Appendix A: Serving/sampling defaults that could matter

- GLM53 `generation_config.json`: `do_sample: true, temperature: 1.0, top_p: 0.95`. GLM52 same. HY3: `temperature: 0.9, top_k: -1, top_p: 1`. These are model defaults, not stated as eval settings. Any CQL run that did not set temperature explicitly would inherit them through vLLM's `--generation-config` default.
- GLM53 benchmarked serve recipe (README Quick start, 4x H100/H200): `--tensor-parallel-size 4 --enable-expert-parallel --max-model-len 262144 --max-num-seqs 512 --gpu-memory-utilization 0.92 --no-enable-prefix-caching --speculative-config '{"method":"mtp","num_speculative_tokens":2}' --reasoning-parser glm45 --tool-call-parser glm47 --enable-auto-tool-choice`, image `vllm/vllm-openai:glm53-flash-x86_64-cu130`.
- GLM53 SM121 launcher passes `--default-chat-template-kwargs '{"enable_thinking":true}'` (`scripts/launch_glm53_w4a16_dflash2_sm121.sh`, line ~151).
- CQL repeatedly claims spec decoding "changes latency, not answers" and runs quality with spec off (GLM52, HY3, GLM53 vision) but with spec ON for GLM53 AIME (MTP on H100, DFlash2 on Spark).
- GLM52 serve: vLLM v0.23.0, `--kv-cache-dtype fp8`, `--reasoning-parser glm45`. HY3: vLLM 0.25.1.

## Appendix B: DeepSeek-V4 repos (other family, lm-eval habits)

From `github.com/canada-quant/dsv4-flash-w4a16-fp8-mtp/benchmarks/phase2/gsm8k_phase2_2026-05-22.json` (lm_eval_version 0.4.11): model `local-completions` (no chat template), `num_fewshot: 8`, `max_gen_toks: 512`, `gen_kwargs: {temperature: 0, do_sample: false}`, `until: ["Question:", "</s>", "<|im_end|>"]`, filters strict-match regex `#### (\-?[0-9\.\,]+)` and flexible-extract, full 1,319, seeds random 0 / numpy 1234 / torch 1234 / fewshot 1234. Result 93.71% strict / 93.63% flex.
From `dsv4-flash-nvfp4-fp8-mtp/docs/benchmarks/phase6_gsm8k_2026_05_21.md`: "lm-eval 0.4.12 via local-chat-completions", "num_fewshot=8, batch_size=1, num_concurrent=8, apply_chat_template=True", 1,319. IFEval (`phase6_expanded_2026_05_21.md`): "`lm_eval ifeval`, `--apply_chat_template`, num_concurrent=16", all four metrics published (prompt-strict 0.8540, prompt-loose 0.8928, inst-strict 0.9005, inst-loose 0.9293). `requirements-bench.txt`: `lm-eval>=0.4.12`.
DSV4-Pro HF card: GSM8K "matched n=300 (chat greedy, max_tokens=2048)" and full n=1319. DSV4-Flash-W4A16-FP8-MTP card notes CQL abandoned lm-eval `aime24` because "completions-mode prompt (no chat template), `exact_match` scorer" missed boxed answers, and used custom `scripts/aime_thinking_bench.py` instead.

---

## GAPS (settings needed to reproduce that CQL did not publish)

| Benchmark | Missing setting |
|---|---|
| GSM8K (GLM53) | Harness and version; few-shot count; CoT format; strict vs flexible metric; thinking on/off and reasoning_effort; temperature/top_p/seed; max tokens; n for the 0.970–0.975 rows; which 200 problems make the H200 subset; chat template on/off |
| GSM8K (GLM52) | Harness/version; shots; temperature; seed; thinking level (only "16,384-token generation budget for the reasoning CoT"); full set or subset |
| GSM8K (HY3) | max_gen_toks; seed; stop sequences; fewshot_as_multiturn; exact RUNLOG (private) |
| MATH-500 (GLM52) | Harness; prompt template; temperature; seed; thinking level; math-verify version; n repeats |
| MATH-500 (HY3) | Temperature (thinking runs not stated as greedy); seed; prompt text; math_verify version; harness name |
| AIME 2025 (GLM53) | Temperature/top_p (only AIME 2026 is stated as temp 0.0); seed per epoch; prompt text and answer-extraction rule; dataset source (which AIME 2025 file, I and II); the exact request param for "max thinking"; how truncated/empty answers are scored (implied wrong); harness/script name |
| AIME 2026 (GLM53) | Dataset source for AIME 2026 problems/answers; prompt; extraction; seeds; why epochs differ at temp 0 (nondeterminism vs sampling); harness |
| GPQA-Diamond (GLM53) | Thinking level; temperature; prompt format; choice shuffling and seed; extraction (flexible vs strict); repeats; harness |
| GPQA-Diamond (HY3) | Choice shuffling; temperature; prompt text; repeats |
| IFEval (GLM52, HY3) | Loose metrics; max tokens (HY3); thinking state (GLM52); whether reasoning text is stripped before scoring (GLM52 uses reasoning parser, implied stripped); harness version (GLM52) |
| IFEval (GLM53) | Not run / not reported at all |
| MATH-500 (GLM53) | Not reported at all |
| MMMU | Max new tokens; prompt variant (lmms-eval default vs CoT); whether lmms-eval drove generation or only scoring ("task specs + installed scoring functions"); image resolution / processor settings; how open-ended answers were scored; protocol doc is private |
| OCRBench | Max new tokens; image settings; same private-doc issue |
| RULER | Sub-task list; RULER implementation and version; aggregation; tokenizer for length; thinking on/off; max new tokens; temperature; seed for the 50 samples per sub-task |
| CanLegal Bench | Data, prompts, harness and scoring code not public; judge prompts and judge sampling; exact prompt per task; how a self-served open model should be configured (only Command A+ example: temp 0.6, top_p 0.95, 65,536 then 131,072 then 200,000 max_tokens); whether a system prompt is used; one sample per record assumed |
| SWE-bench Verified | Agent version, step/cost limits, sampling, budget |
| All GLM53 text evals | Whether spec decode was on (stated only for AIME rows); vLLM image tag per number; client concurrency |

---

## Sources (all fetched 2026-11-19)

- https://huggingface.co/canada-quant/GLM-5.3-Flash-W4A16-MTP — `README.md`, `BENCHMARKS.md`, `generation_config.json`, `chat_template.jinja` (via /raw/main/)
- https://huggingface.co/canada-quant/GLM-5.2-W4A16-MTP — `README.md`, `generation_config.json`, `chat_template.jinja`
- https://huggingface.co/canada-quant/hy3-w4a16-mtp — `README.md`, `generation_config.json`, `deploy-hopper.md`, `findings/*.md` (findings hold no eval settings)
- https://huggingface.co/canada-quant/DeepSeek-V4-Flash-W4A16-FP8-MTP, .../DeepSeek-V4-Flash-NVFP4-FP8-MTP, .../DeepSeek-V4-Pro-NVFP4-FP8-MTP, .../DeepSeek-V4-Flash-W4A16-FP8 — `README.md`
- https://huggingface.co/canada-quant/GLM-5.3-Flash-DFlash2-E, -F, -G — `README.md`, `PROVENANCE.txt` (drafter acceptance only)
- https://github.com/canada-quant/vllm-glm53-flash-sm121 — `README.md`, `drafter/README.md`, `drafter/RESULTS.md`, `drafter/eval/holdout_client.py`, `drafter/cards/GLM-5.3-Flash-DFlash2-G.md`, `scripts/launch_glm53_w4a16_dflash2_sm121.sh`
- https://github.com/canada-quant/dsv4-flash-w4a16-fp8-mtp — `BENCHMARKS.md`, `README.md`, `requirements-bench.txt`, `benchmarks/phase2/gsm8k_phase2_2026-05-22.json`
- https://github.com/canada-quant/dsv4-flash-w4a16-fp8 — `README.md`, `requirements-bench.txt`
- https://github.com/canada-quant/dsv4-flash-nvfp4-fp8-mtp — `README.md`, `docs/benchmarks/phase6_gsm8k_2026_05_21.md`, `docs/benchmarks/phase6_expanded_2026_05_21.md`
- https://cql.ca/news.html and posts: /news/glm-5-3-w4a16-mtp.html, /news/glm-5-3-flash-h100-nvfp4-vision.html, /news/glm-5-3-flash-dflash2-e.html, /news/hy3-w4a16-mtp.html, /news/glm-5-2-w4a16-mtp.html, /news/canlegal-bench-leaderboard.html
- https://canlegalbench.com (home, /about, /transparency, /tasks, /models/<5 model ids>, /tasks/issue_spotting, /tasks/citation_resolution)
- Not public (404 or "source repo"): GitHub canada-quant/hy3-w4a16-mtp (docs/RUNLOG.md), GLM-5.3 source repo (`docs/VISION_EVALS.md`, `bench/vision/raw/`, `bench/h2h/...`), CanLegal Bench data/harness.
