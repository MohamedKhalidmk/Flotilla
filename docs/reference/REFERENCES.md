# References: what Flotilla borrows, and from whom

Every paper, dataset, model and piece of code Flotilla borrows from. A file that copies or follows one of these names
it near its top in a `Sources:` line with the keys below (`original` = written for Flotilla);
`tests/test_references.py` checks that every key named in a file is listed here. GRAFT keeps its own list
(GRAFT `docs/reference/REFERENCES.md`) for what GRAFT borrows; the Memory routes rely on both.

Licences: "repo" = stated in this repository or in the source's own files we hold; "check" = not yet confirmed from
the source's licence file or dataset card (to do before any publication).

## Methods and papers

| Key | Citation | Link | Licence | What we take | Where (files, IDs) |
|---|---|---|---|---|---|
| `usc` | Chen, Aksitov, Alon, Ren, Xiao, Yin, Prakash, Sutton, Wang, Zhou. Universal Self-Consistency for Large Language Model Generation. arXiv 2311.17311, 2023 | https://arxiv.org/abs/2311.17311 | paper | the tie rule and its prompt wording | `prompts/vote_usc.v1.md`, `flotilla/system.py`, `flotilla/usc_replay.py`; F36, S168 |
| `self-consistency` | Wang, Wei, Schuurmans, Le, Chi, Narang, Chowdhery, Zhou. Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR 2023 (arXiv 2203.11171) | https://arxiv.org/abs/2203.11171 | paper | majority vote over sampled answers | `flotilla/system.py` (vote); F18, F19, F22, F36 |
| `retool` | Feng et al. ReTool: Reinforcement Learning for Strategic Tool Use in LLMs. arXiv 2504.11536, 2025 (cited by the user as ICLR 2026) | https://arxiv.org/abs/2504.11536 | paper | code run inside long reasoning, errors fed back | `prompts/forced_tool.v1.md`, `flotilla/system.py` (forced tool, reasoning kept across rounds); F37-F39 |
| `critic` | Gou, Shao, Gong, Shen, Yang, Duan, Chen. CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing. ICLR 2024 (arXiv 2305.11738) | https://arxiv.org/abs/2305.11738 | paper | answer, check with an interpreter, revise; stop when unchanged | `prompts/self_check.v1.md`, `flotilla/system.py` (`self_check`); F40 |
| `ifeval` | Zhou, Lu, Mishra, Brahma, Basu, Luan, Zhou, Hou. Instruction-Following Evaluation for Large Language Models. arXiv 2311.07911, 2023; checkers in google-research/instruction_following_eval | https://github.com/google-research/google-research/tree/master/instruction_following_eval | Apache-2.0 (repo header) | the official instruction checkers (through `lm-eval`), the IFEval test set | `flotilla/scoring.py`, `flotilla/splits.py`, `flotilla/leakage.py`, `flotilla/ifeval_rules.py`, `prompts/ifeval_rules.v1.md` (constraint_check v2); F39; IFEval benchmark row |
| `longmemeval` | Wu, Wang, Yu, Zhang, Chang, Yu. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. ICLR 2025 (arXiv 2410.10813) | https://github.com/xiaowu0162/LongMemEval | MIT (repo, run log) | the dataset (`xiaowu0162/longmemeval-cleaned`), the judge prompts verbatim, the reader prompt wording | `flotilla/memory_route.py`, `flotilla/longmemeval.py`, `flotilla/strategy_labels.py`, `tests/data/longmemeval_sample.jsonl`; F15-F23, F29-F36; S132-S168; tests 04, 06 |
| `memoryagentbench` | Hu, Wang, McAuley. Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions. ICLR 2026 (arXiv 2507.05257) | https://github.com/HUST-AI-HYZ/MemoryAgentBench | MIT (GRAFT's submodule) | FactConsolidation, the 4,096-token chunk size, the same LongMemEval judge text | `flotilla/memory_route.py`; test 05; PROTOCOL 4.3 |
| `ruler` | Hsieh et al. RULER: What's the Real Context Size of Your Long-Context Language Models? COLM 2024 (arXiv 2404.06654) | https://github.com/NVIDIA/RULER | Apache-2.0 (notes) | the RULER tasks, built through lm-eval's `ruler` group | `flotilla/export_ruler.py`, `flotilla/scoring.py`; RULER rows |
| `gptq` | Frantar, Ashkboos, Hoefler, Alistarh. GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers. ICLR 2023 (arXiv 2210.17323) | https://arxiv.org/abs/2210.17323 | paper | W4A16 weight quantisation (through llm-compressor) | `flotilla/quantize.py`; F01, F04; test 01 |
| `cql` | canada-quant published evaluation settings and quantisation recipes (model cards and cql.ca pages listed in `notes/cql_settings.md`) | https://huggingface.co/canada-quant | check | evaluation settings, the quantisation ignore list | `docs/reference/PROTOCOL.md` section 1.3, `flotilla/quantize.py` |
| `ngram-leakage` | Brown et al. Language Models are Few-Shot Learners. NeurIPS 2020 (13-gram contamination check, appendix C) | https://arxiv.org/abs/2005.14165 | paper | the 13-gram overlap rule of the leakage check | `flotilla/leakage.py`; PROTOCOL section 5 |
| `eig-search` | Lu, Liu, Mills, He, Niu. EiG-Search: Generating Edge-Induced Subgraphs for GNN Explanation in Linear Time. ICML 2024 (arXiv 2405.01762) | https://github.com/sluxsr/EiG-Search | no licence (use cleared by Prof. Lu, PROTOCOL 4.3) | GRAFT's EiG explainer (through GRAFT) | Memory routes' GRAFT options; test 05 |
| `goat` | Lu, Mills, He, Liu, Niu. GOAt: Explaining Graph Neural Networks via Graph Output Attribution. ICLR 2024 (arXiv 2401.14578) | https://github.com/sluxsr/GOAt | no licence file (GRAFT NOTICE) | GRAFT's default explainer (through GRAFT) | `flotilla/memory_route.py` (`explainer: goat`); F20-F23; G08, G35 |

## Datasets

| Key | Citation | Link | Licence | Where (files, IDs) |
|---|---|---|---|---|
| `gsm8k` | Cobbe et al. Training Verifiers to Solve Math Word Problems. arXiv 2110.14168, 2021 | https://huggingface.co/datasets/openai/gsm8k | check | `flotilla/splits.py`, `flotilla/router_data.py`, `flotilla/leakage.py`; benchmark row 1; router pool |
| `math` | Hendrycks et al. Measuring Mathematical Problem Solving With the MATH Dataset. NeurIPS 2021 D&B (arXiv 2103.03874) | https://huggingface.co/datasets/EleutherAI/hendrycks_math | check | `flotilla/router_data.py`; router pool |
| `math500` | Lightman et al. Let's Verify Step by Step. arXiv 2305.20050, 2023 (MATH-500 subset) | https://huggingface.co/datasets/HuggingFaceH4/MATH-500 | check | `flotilla/eval_math500.py`, `flotilla/splits.py`, `flotilla/leakage.py`; S102-S114; benchmark row 2 |
| `aime-1983-2024` | AIME 1983-2024 problems, compiled by di-zhang-fdu | https://huggingface.co/datasets/di-zhang-fdu/AIME_1983_2024 | check | `flotilla/router_data.py`; router pool |
| `matharena` | Balunović et al. MathArena: Evaluating LLMs on Uncontaminated Math Competitions. arXiv 2505.23281, 2025 (AIME 2025, 2026) | https://huggingface.co/datasets/MathArena/aime_2025 | check | `flotilla/splits.py`, `flotilla/leakage.py`; benchmark rows 3-4 |
| `mmlu-pro` | Wang et al. MMLU-Pro. NeurIPS 2024 D&B (arXiv 2406.01574) | https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro | check | `flotilla/router_data.py`; router pool |
| `gpqa` | Rein et al. GPQA: A Graduate-Level Google-Proof Q&A Benchmark. arXiv 2311.12022, 2023 | https://huggingface.co/datasets/Idavidrein/gpqa | check (gated; the card asks that examples not be published online) | `flotilla/splits.py`, `flotilla/leakage.py`, `tests/data/formats/raw_rows.json`; benchmark row 5 |
| `rlvr-ifeval` | Lambert et al. Tulu 3: Pushing Frontiers in Open Language Model Post-Training. arXiv 2411.15124, 2024 (RLVR-IFeval) | https://huggingface.co/datasets/allenai/RLVR-IFeval | check | `flotilla/router_data.py`; router pool instruction questions; F39 (design) |
| `livecodebench` | Jain et al. LiveCodeBench. arXiv 2403.07974, 2024 | https://huggingface.co/datasets/livecodebench/code_generation_lite | check | `flotilla/splits.py`, `flotilla/router_data.py`, `flotilla/leakage.py`, `flotilla/scoring.py` (our own runner, not `lcb_runner`; PROTOCOL 1.3); benchmark row 10; router pool |
| `mmmu` | Yue et al. MMMU. CVPR 2024 (arXiv 2311.16502) | https://huggingface.co/datasets/lmms-lab/MMMU | check | `flotilla/splits.py`, `flotilla/scoring.py`; benchmark row 7 |
| `ocrbench` | Liu et al. On the Hidden Mystery of OCR in Large Multimodal Models (OCRBench). arXiv 2305.07895, 2023 | https://huggingface.co/datasets/echo840/OCRBench | check | `flotilla/splits.py`, `flotilla/scoring.py`; benchmark row 8 |
| `ultrachat` | Ding et al. Enhancing Chat Language Models by Scaling High-quality Instructional Conversations. arXiv 2305.14233, 2023 (UltraChat 200k) | https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k | check | `flotilla/quantize.py`, `flotilla/calib_pool.py` (GPTQ calibration); F01, F04 |
| `paul-graham-essays` | Paul Graham essays (RULER haystack) | https://huggingface.co/datasets/baber/paul_graham_essays | check | `flotilla/export_ruler.py` |
| `squad` | Rajpurkar, Jia, Liang. Know What You Don't Know: Unanswerable Questions for SQuAD. ACL 2018 | https://rajpurkar.github.io/SQuAD-explorer/ | check | `flotilla/export_ruler.py` (RULER QA) |
| `hotpotqa` | Yang et al. HotpotQA. EMNLP 2018 | https://hotpotqa.github.io/ | check | `flotilla/export_ruler.py` (RULER QA) |
| `t-rex` | Elsahar et al. T-REx: A Large Scale Alignment of Natural Language with Knowledge Base Triples. LREC 2018 | https://huggingface.co/datasets/relbert/t_rex | check | GRAFT's structure guide used by the Memory routes (G35); F20-F23 |
| `dialogue-nli` | Welleck, Weston, Szlam, Cho. Dialogue Natural Language Inference. ACL 2019 | https://huggingface.co/datasets/xksteven/dialogue_nli | check (run log: unknown, research use) | GRAFT G44, G45 (chat guide) |

## Code and libraries

| Key | Source | Link | Licence | Where (files, IDs) |
|---|---|---|---|---|
| `vllm` | Kwon et al. Efficient Memory Management for Large Language Model Serving with PagedAttention. SOSP 2023; vLLM 0.32.0 | https://github.com/vllm-project/vllm | Apache-2.0 | `flotilla/serve.py`, `configs/servers*.json`; every served model |
| `lm-eval` | EleutherAI lm-evaluation-harness 0.4.11 | https://github.com/EleutherAI/lm-evaluation-harness | MIT | `flotilla/scoring.py` (IFEval), `flotilla/export_ruler.py` (RULER) |
| `lmms-eval` | EvolvingLMMs-Lab lmms-eval (PROTOCOL pins 0.7.3; the env installs it unpinned) | https://github.com/EvolvingLMMs-Lab/lmms-eval | check | `flotilla/scoring.py` (MMMU utilities), `flotilla/splits.py` (MMMU prompt strings) |
| `llm-compressor` | vLLM project llm-compressor 0.15.0 with compressed-tensors 0.20.1 | https://github.com/vllm-project/llm-compressor | Apache-2.0 | `flotilla/quantize.py`; F01-F04 |
| `math-verify` | Hugging Face Math-Verify, with sympy and latex2sympy2_extended | https://github.com/huggingface/Math-Verify | check | `flotilla/tools.py`, `flotilla/eval_math500.py`, `flotilla/scoring.py` |
| `sympy` | SymPy | https://www.sympy.org | BSD-3-Clause | `flotilla/tools.py` (the sympy tool) |
| `scikit-learn` | scikit-learn | https://scikit-learn.org | BSD-3-Clause | `flotilla/router_b_lite.py`, `flotilla/strategy_router.py`; F14, F26, F31 |
| `anthropic-sdk` | anthropic Python SDK 2.1.0 | https://github.com/anthropics/anthropic-sdk-python | MIT | `flotilla/memory_route.py` (Haiku judge) |
| `openai-sdk` | openai Python SDK | https://github.com/openai/openai-python | Apache-2.0 | `flotilla/system.py` (every solver call) |
| `semantic-router` | vLLM Semantic Router v0.4.0 and its vela3 encoder | https://github.com/vllm-project/semantic-router | Apache-2.0 (notes) | `flotilla/router_a.py`, `scripts/trillium/pull_router_image.sh`; F12, S123 |
| `open-instruct` | AllenAI open-instruct, `open_instruct/if_functions.py` at commit a4cd966 (2026-11-21): the checkers that define RLVR-IFeval's ground-truth rules (vendored unmodified) | https://github.com/allenai/open-instruct | Apache-2.0 (repo LICENSE) | `flotilla/vendor/open_instruct_if_functions.py`, `flotilla/ifeval_rules.py`, `flotilla/label_loop.py` (instruction grading for the full relabel; string choice options are split first) |
| `graft` | GRAFT (our own sister project) | https://github.com/MohamedKhalidmk/GRAFT | Apache-2.0 | `flotilla/graft_bridge.py`, `flotilla/memory_route.py` (price card, cost function, gateway log format); F20-F23, F35 |

## Models

| Key | Model | Link | Licence | Where (IDs) |
|---|---|---|---|---|
| `qwen3.8` | Qwen3.8-27B (our W4A16 and FP8 builds; its tokenizer) | https://huggingface.co/Qwen/Qwen3.8-27B | Apache-2.0 (PROTOCOL 1.4) | F01, F02, F05, F06, F11, F15-F40 |
| `phi-4-reasoning` | Microsoft Phi-4-reasoning and Phi-4-reasoning-plus (and the NVIDIA FP8 and AMD W4A16 builds we compared) | https://huggingface.co/microsoft/Phi-4-reasoning-plus | MIT (PROTOCOL) | F03, F04; S108-S110, S114, S122 |
| `gpt-oss` | OpenAI gpt-oss-20b | https://huggingface.co/openai/gpt-oss-20b | Apache-2.0 (PROTOCOL v9) | F07; S111-S113, S116, S120 |
| `command-a-plus` | Cohere Command A+ (05-2026) | https://huggingface.co/CohereLabs | check | F08, F09; S117, S118 |
| `claude-haiku` | Anthropic Claude Haiku 5.5 (API) | https://www.anthropic.com | Anthropic commercial terms | LongMemEval judge: S132-S141, S159-S170; reasoning-error sub-types (`flotilla/error_subtypes.py`) |
| `claude-sonnet` | Anthropic Claude Sonnet 5.5 (API) | https://www.anthropic.com | Anthropic commercial terms | tiebreak verdict on split Haiku judge groups (`flotilla/memory_route.py` tiebreak) |
| `modernbert` | Warner et al. ModernBERT. arXiv 2412.13663, 2024 (answerdotai/ModernBERT-base) | https://huggingface.co/answerdotai/ModernBERT-base | Apache-2.0 | `flotilla/router_b.py`, `flotilla/strategy_router.py`; F13, F24, F25, F29, F30 |
| `bge-small` | Xiao et al. C-Pack: Packaged Resources To Advance General Chinese Embedding. arXiv 2309.07597, 2023 (BAAI/bge-small-en-v1.5) | https://huggingface.co/BAAI/bge-small-en-v1.5 | MIT | `flotilla/router_b_lite.py`, `flotilla/strategy_router.py`, `flotilla/leakage.py`; F14, F26, F27, F31, F32; GRAFT's embedder |
| `vela3` | vllm-sr vela3-fast decision encoder | https://huggingface.co/vllm-sr | Apache-2.0 (PROTOCOL 4.5) | `flotilla/router_a.py`; F12 |

Surveyed in `notes/` but never run (no credit needed beyond the notes): other Qwen3.x and Phi-4 variants, Gemma 4,
Mage-VL, canada-quant GLM/Hy3/DeepSeek builds, vllm-sr Decision models, and code-graph tools (CodeGraph,
codebase-memory-mcp, Serena, Graphify).

## Open points (before publishing)

- `tests/data/formats/raw_rows.json` holds real GPQA rows, which GPQA's card asks not to publish online; the repo is
  public, so the GPQA sample should be replaced by a made-up row in GPQA's format (needs the user's yes).
- Every licence marked "check".
