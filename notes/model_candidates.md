# Model candidates for the compound system (checked 2026-11-19)

Scope: open models that fit one H100 80 GB at W4A16 or 8-bit under vLLM, up to ~35B total parameters, with thinking modes. Data pulled directly from Hugging Face model cards and the HF API on 2026-11-19. "Release" below is the HF repo creation date from the API (`createdAt`) unless the card states a release date. Scores are quoted from the cited card; "n/r" means the card does not report it. Nothing here was run by us.

Benchmarks of interest: GSM8K, MATH-500, AIME 2025, AIME 2026, GPQA-Diamond, IFEval, LiveCodeBench, RULER 32K/64K, Canadian legal, plus MMMU and OCRBench for the VLM slot. No card checked reports RULER or any Canadian legal benchmark, so those must be measured by us.

---

## 1. Qwen candidates (Qwen org, sorted by recency)

Newer Qwen repos that were excluded: `Qwen/Qwen3.8-Flash-Next` (2026-08-24) is 125B total / 6B active plus 51B n-gram embedding (about 180B stored params), too big. `Qwen/Qwen3.8-2.4T-A95B` is far too big. `Qwen/Qwen-AgentWorld-35B-A3B` (2026-06-22) is an agentic-world model, not checked further. `Qwen/Qwen-Drive-1.0-4B` is a driving VLM.

### 1a. Specs

| Repo id | HF release | Params (total / active) | Native context | License | Thinking | vLLM version | Official quants | Community 4-bit / 8-bit quants |
|---|---|---|---|---|---|---|---|---|
| `Qwen/Qwen3.8-27B` | 2026-08-05 | 27B dense (27.78B incl. vision) | 262,144 (YaRN to 1M) | Apache-2.0 | On by default, `enable_thinking`, `reasoning_effort` low/medium/xhigh | Card gives no pin; vLLM recipe page badge links v0.17.0 (inferred minimum); RedHatAI INT4 validated on vLLM 0.28.0 | `Qwen/Qwen3.8-27B-FP8` | `RedHatAI/Qwen3.8-27B-INT4` (W4A16, GPTQ + AWQ smoothing, FP8 KV), `nvidia/Qwen3.8-27B-NVFP4` (Blackwell only, not H100), `cyankiwi/Qwen3.8-27B-AWQ-INT4`, `philbert440/Qwen3.8-27B-W4A16-AWQ`, `Eco-Tech/Qwen3.8-27B-w8a8` (listed on vLLM recipe) |
| `Qwen/Qwen3.6-27B` | 2026-04-21 | 27B dense | 262,144 (to ~1M) | Apache-2.0 | Yes (hybrid) | `vllm>=0.19.0` recommended (card) | `Qwen/Qwen3.6-27B-FP8` | `cyankiwi/Qwen3.6-27B-AWQ-INT4`, `QuantTrio/Qwen3.6-27B-AWQ`, `Intel/Qwen3.6-27B-int4-AutoRound`, `btbtyler09/Qwen3.6-27B-GPTQ-4bit`, `nvidia/Qwen3.6-27B-NVFP4` (Blackwell) |
| `Qwen/Qwen3.6-35B-A3B` | 2026-04-15 | 35B MoE / 3B active | 262,144 (to ~1M) | Apache-2.0 | Yes (hybrid) | `vllm>=0.19.0` recommended (card); RedHatAI FP8 validated on 0.24.0 | `Qwen/Qwen3.6-35B-A3B-FP8` | `RedHatAI/Qwen3.6-35B-A3B-FP8`, `QuantTrio/Qwen3.6-35B-A3B-AWQ`, `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`, `palmfuture/Qwen3.6-35B-A3B-GPTQ-Int4`, `RedHatAI/` and `nvidia/` NVFP4 (Blackwell) |
| `Qwen/Qwen3.5-27B` | 2026-02-24 | 27B dense | 262,144 (to 1.01M) | Apache-2.0 | Yes | Card said install vLLM nightly at release (superseded) | `-FP8`, `-GPTQ-Int4` (official) | many |
| `Qwen/Qwen3.5-35B-A3B` | 2026-02-24 | 35B MoE / 3B active | 262,144 (to 1.01M) | Apache-2.0 | Yes | Same as above | `-FP8`, `-GPTQ-Int4` (official) | many |

All five are native vision-language models (text + image + video). Architecture (Qwen3.5 lineage): hybrid Gated DeltaNet linear attention plus gated full attention every 4th layer, so KV cache at 32K to 64K is small. Easy fit on one H100 at W4A16 (weights roughly 15 to 20 GB) or FP8 (roughly 30 to 36 GB). No Qwen card states a training-data cutoff.

### 1b. Reported scores (quoted from cards)

| Model | AIME 2025 | AIME 2026 | HMMT Feb 26 | MATH-500 | GSM8K | GPQA-D | IFEval | LiveCodeBench v6 | MMMU | OCRBench |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B (Qwen card) | n/r | n/r | n/r | n/r | n/r | 89.2 | n/r (IFBench 79.5) | 90.3 | n/r | n/r (OmniDocBench 1.5: 91.1) |
| Qwen3.8-27B BF16 (RedHatAI eval) | 95.42 (pass@1, 8 seeds) | n/r | n/r | 83.73 (see note) | 95.75 (GSM8K Platinum) | 89.23 | 92.24 (prompt strict) | n/r | n/r | n/r |
| RedHatAI/Qwen3.8-27B-INT4 (W4A16) | 94.17 | n/r | n/r | 83.33 | 96.77 (Platinum) | 87.88 | 91.93 | n/r | n/r | n/r |
| Qwen3.6-27B | n/r | 94.1 | 84.3 | n/r | n/r | 87.8 | n/r | 83.9 | 82.9 | 89.4 |
| Qwen3.6-35B-A3B | n/r | 92.7 | 83.6 | n/r | n/r | 86.0 | n/r | 80.4 | 81.7 | n/r |
| Qwen3.5-27B | n/r | 92.6 (from Qwen3.6 card) | 84.3 | n/r | n/r | 85.5 | 95.0 | 80.7 | 82.3 | 89.4 |
| Qwen3.5-35B-A3B | n/r | 91.0 (from Qwen3.6 card) | 78.7 | n/r | n/r | 84.2 | 91.9 | 74.6 | 81.4 | 91.0 |

Notes:
- Qwen3.8-27B card's text table covers agentic coding, IFBench, GPQA-D, HLE (30.8), LiveCodeBench v6; it has no AIME or MATH row. The AIME 2025 / MATH-500 / IFEval / GSM8K numbers come from RedHatAI's own BF16 vs INT4 evaluation (lighteval / lm-eval-harness, vLLM, 3 seeds; 8 for AIME).
- The 83.7 MATH-500 from RedHatAI looks low next to 95 on AIME 2025. It is probably an answer-extraction artifact of their harness, not a true ceiling. Treat as unverified until we run it ourselves.
- Qwen3.6 cards report "AIME26" on the full AIME 2026 I and II.
- Qwen3.5 IFEval values are from the Qwen3.5 cards (thinking mode, Qwen's harness).

---

## 2. Microsoft Phi candidates

No Phi-5 or newer text reasoning model exists on `huggingface.co/microsoft` as of 2026-11-19. The newest Phi-branded repos are `Phi-4-reasoning-vision-15B` (2026-01-23 repo, card release date March 4, 2026) and `Phi-Ground-Any` (GUI grounding). The text reasoning family is still the April to June 2025 Phi-4-reasoning line.

### 2a. Specs

| Repo id | Release (card) | Params | Context | License | Stated cutoff | vLLM | Quants |
|---|---|---|---|---|---|---|---|
| `microsoft/Phi-4-reasoning-plus` | April 30, 2025 | 14B dense (14.66B) | 32K (card notes experiments to 64K) | MIT | "cutoff dates of March 2025 and earlier for publicly available data"; training Jan to Apr 2025 | `vllm serve ... --reasoning-parser deepseek_r1` (no pin; standard Phi3 arch) | `nvidia/Phi-4-reasoning-plus-FP8`, `amd/Phi-4-reasoning-plus-w4a16-llmcompressor` (W4A16 GPTQ, vLLM 0.26.0), `amd/...-w8a8-llmcompressor`, `cortecs/Phi-4-reasoning-plus-FP8-Dynamic` |
| `microsoft/Phi-4-reasoning` | April 30, 2025 | 14B dense | 32K | MIT | March 2025 | same | `RedHatAI/Phi-4-reasoning-FP8-dynamic` (validated vLLM 0.13.0) |
| `microsoft/Phi-4-mini-flash-reasoning` | June 2025 | 3.8B (SambaY hybrid SSM) | 64K | MIT | February 2025 | needs vLLM PR #23996 (V1) | none official |
| `microsoft/Phi-4-reasoning-vision-15B` | March 4, 2026 | 15B | 16,384 | MIT | Training dates Feb 3, 2025 to Feb 21, 2026 | `vllm >= 0.15.2` | `RedHatAI/Phi-4-reasoning-vision-15B`, `inference-optimization/...-FP8-dynamic` |

Phi-4-reasoning(-plus) at BF16 is about 29 GB, so it fits one H100 even unquantized; FP8 about 15 GB.

### 2b. Reported scores (quoted from cards)

| Model | AIME 2024 | AIME 2025 | MATH-500 | GSM8K | GPQA-D | IFEval strict | LiveCodeBench | MMMU | OCRBench |
|---|---|---|---|---|---|---|---|---|---|
| Phi-4-reasoning-plus | 81.3 | 78.0 | n/r | 87.04 (5-shot, AMD BF16 baseline) | 68.9 | 84.9 | 53.1 (8/1/24 to 2/1/25 window) | - | - |
| Phi-4-reasoning-plus W4A16 (AMD) | n/r | n/r | n/r | 86.88 | n/r | n/r | n/r | - | - |
| Phi-4-reasoning | 75.3 | 62.9 | n/r | n/r | 65.8 | 83.4 | 53.8 | - | - |
| Phi-4-reasoning (RedHatAI BF16 re-eval) | n/r | 61.25 | 90.01 | n/r | 64.65 | n/r | n/r | - | - |
| Phi-4-reasoning-FP8-dynamic (RedHatAI) | n/r | 64.58 | 88.60 | n/r | 66.50 | n/r | n/r | - | - |
| Phi-4-mini-flash-reasoning | 52.29 | 33.59 | 92.45 | n/r | 45.08 | n/r | n/r | - | - |
| Phi-4-reasoning-vision-15B | n/r | n/r | n/r | n/r | n/r | n/r | n/r | 54.3 (MMMU_VAL) | 76.0 |

No Phi card reports AIME 2026.

---

## 3. Small VLM fallback (if Cohere Command A+ is dropped)

| Model | Params | MMMU | OCRBench | Context | License | Source |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3.6-27B` | 27B dense | 82.9 | 89.4 | 262K | Apache-2.0 | Qwen3.6-27B card |
| `Qwen/Qwen3.5-27B` | 27B dense | 82.3 | 89.4 | 262K | Apache-2.0 | Qwen3.5-27B card |
| `Qwen/Qwen3.6-35B-A3B` | 35B / 3B active | 81.7 | n/r | 262K | Apache-2.0 | Qwen3.6-35B-A3B card |
| `Qwen/Qwen3.5-35B-A3B` | 35B / 3B active | 81.4 | 91.0 | 262K | Apache-2.0 | Qwen3.5 card |
| `google/gemma-4-31B-it` | 30.7B dense | 80.4 (reported in Qwen3.6 card, not Google's) | 86.1 (same, Qwen-reported) | 256K | Apache-2.0 | Qwen3.6 card; Google card gives MMMU-Pro 76.9 only |
| `Qwen/Qwen3.8-27B` | 27B dense | n/r | n/r (OmniDocBench 1.5: 91.1, CharXiv RQ 83.7) | 262K | Apache-2.0 | Qwen3.8 card |
| `microsoft/Phi-4-reasoning-vision-15B` | 15B | 54.3 (VAL) | 76.0 | 16K | MIT | Phi card |
| `microsoft/Mage-VL` | 4.7B | n/r | 81.8 | - | Apache-2.0 | Mage-VL card |

Phi's VLM is far behind Qwen on both MMMU and OCRBench.

---

## 4. Contamination check (AIME 2025 held Feb 2025; AIME 2026 held Feb 2026)

| Model | Release | Stated data cutoff | AIME 2025 risk | AIME 2026 risk |
|---|---|---|---|---|
| Qwen3.8-27B | 2026-08-05 | Not stated | High (released 18 months after) | High (released ~6 months after) |
| Qwen3.6-27B / 35B-A3B | 2026-04-15/21 | Not stated | High | Possible (released ~2 months after; Qwen reports AIME26 as an eval, which suggests they tried to hold it out, unverified) |
| Qwen3.5-27B / 35B-A3B | 2026-02-24 | Not stated | High | Possible (released ~2 weeks after the exams; pretraining likely earlier, post-training data unknown) |
| Phi-4-reasoning(-plus) | 2025-04-30 | March 2025 | Possible (cutoff is after Feb 2025 exam; Microsoft reports AIME 25 as eval) | Clean (cutoff predates exam) |
| Phi-4-mini-flash-reasoning | June 2025 | February 2025 | Borderline | Clean |
| Phi-4-reasoning-vision-15B | 2026-03-04 | Training through Feb 21, 2026 | Possible | Possible |
| Gemma 4 31B | 2026-03-11 | Pre-training cutoff January 2025 | Low for pretraining, post-training unknown | Low for pretraining, post-training unknown |

Practical flag: every current Qwen model may have seen AIME 2025 and, for 3.6/3.8, AIME 2026. Only Phi-4-reasoning(-plus) is provably clean on AIME 2026 by stated cutoff.

---

## 5. Recommendation

**Qwen: `Qwen/Qwen3.8-27B`, served as `RedHatAI/Qwen3.8-27B-INT4` (W4A16) or `Qwen/Qwen3.8-27B-FP8`.**
- Newest and strongest Qwen that fits: GPQA-D 89.2, LiveCodeBench v6 90.3 (Qwen card); AIME 2025 95.4, IFEval 92.2 (RedHatAI BF16 eval).
- W4A16 recovery is 98.5 to 99.7% on IFEval, MATH-500, GPQA-D, AIME 2025 (RedHatAI), validated on vLLM 0.28.0.
- 262K native context with linear-attention layers, so RULER 32K/64K fits on one H100 with room for KV.
- Apache-2.0, thinking on/off and `reasoning_effort` per request.
- Caveats: no official AIME/MATH numbers on its card; dense 27B is slower per token than 35B-A3B. If throughput matters more than accuracy, use `Qwen/Qwen3.6-35B-A3B-FP8` (3B active; AIME26 92.7, GPQA-D 86.0, LCB 80.4).

**Phi: `microsoft/Phi-4-reasoning-plus`, served as `nvidia/Phi-4-reasoning-plus-FP8` (or BF16; it fits).**
- Best Phi on math: AIME 2025 78.0, AIME 2024 81.3, GPQA-D 68.9, IFEval 84.9.
- Clean on AIME 2026 by stated March 2025 cutoff.
- Honest assessment: Phi is clearly weaker than Qwen3.8-27B on every overlapping benchmark (AIME 2025 78.0 vs 95.4, GPQA-D 68.9 vs 89.2, IFEval 84.9 vs 92.2, LiveCodeBench 53.1 vs 90.3 on different versions). Its 32K context also rules it out of RULER 64K. On accuracy alone it does not earn a math/reasoning slot; routing math to Phi would lower scores. It could only justify a GPU as (a) an independent verifier or voter for diversity, (b) a contamination-clean AIME 2026 reference, or (c) a cheap fast path for easy GSM8K-style items. Otherwise the second GPU is better spent on a second Qwen (for example Qwen3.6-35B-A3B as a fast drafter/voter, or a second Qwen3.8-27B for self-consistency).

**VLM fallback: `Qwen/Qwen3.6-27B` (FP8 official, or AWQ/AutoRound 4-bit community).**
- Best verified small VLM scores found: MMMU 82.9, OCRBench 89.4. If OCRBench matters most, `Qwen/Qwen3.5-35B-A3B` has OCRBench 91.0 / MMMU 81.4 with official GPTQ-Int4.
- Qwen3.8-27B is itself a native VLM, so the Qwen text GPU may be able to handle MMMU/OCRBench with no extra slot, but its card reports no MMMU or OCRBench numbers. Unverified; worth a quick check on our side before spending a GPU.

---

## 6. Things not verified

- vLLM minimum for Qwen3.8-27B: inferred from the v0.17.0 badge on the vLLM recipe page; the model card gives no number.
- Qwen3.8-27B release date is HF repo creation (2026-08-05); the official public announcement date was not checked.
- RedHatAI MATH-500 of 83.7 for Qwen3.8-27B is likely a harness artifact.
- Gemma 4 31B MMMU / OCRBench are Qwen-reported, not Google-reported.
- No card reports RULER or a Canadian legal benchmark; Phi-4-reasoning-plus cannot run RULER 64K at its 32K native context.
- Qwen training-data cutoffs are not published.

---

## Sources

- Qwen org listing: https://huggingface.co/Qwen (HF API `?author=Qwen&sort=createdAt`)
- https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/Qwen/Qwen3.8-27B-FP8
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- https://huggingface.co/RedHatAI/Qwen3.8-27B-INT4
- https://huggingface.co/Qwen/Qwen3.6-27B
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- https://huggingface.co/RedHatAI/Qwen3.6-35B-A3B-FP8
- https://huggingface.co/Qwen/Qwen3.5-27B
- https://huggingface.co/Qwen/Qwen3.5-35B-A3B
- Microsoft org listing: https://huggingface.co/microsoft (HF API `?author=microsoft&search=phi`)
- https://huggingface.co/microsoft/Phi-4-reasoning-plus
- https://huggingface.co/microsoft/Phi-4-reasoning
- https://huggingface.co/microsoft/Phi-4-mini-flash-reasoning
- https://huggingface.co/microsoft/Phi-4-reasoning-vision-15B
- https://huggingface.co/RedHatAI/Phi-4-reasoning-FP8-dynamic
- https://huggingface.co/amd/Phi-4-reasoning-plus-w4a16-llmcompressor
- https://huggingface.co/nvidia/Phi-4-reasoning-plus-FP8
- https://huggingface.co/google/gemma-4-31B-it
- https://huggingface.co/microsoft/Mage-VL
