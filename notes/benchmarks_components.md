# Benchmarks and components: research notes

Checked 2026-11-19 against live sources (URLs per section). Nothing here was run on a cluster. Where a source did not say something, it is listed under "Uncertain / not found" at the end rather than filled in.

Offline reminder for every item: compute nodes have no internet, so every dataset, tokenizer, model, container image and pip wheel below must be fetched on the login node first and pointed to by local path (and `HF_HUB_OFFLINE=1`, `HF_DATASETS_OFFLINE=1` on the compute side).

---

## 1. CanLegal Bench (Canada Quant Labs)

**What it is.** Closed-book Canadian legal-reasoning benchmark with a public leaderboard. Version v0.8.3, scoring version 2026-10-09.

**Size.** 14,547 scored "gold records" (frozen set) across 17 task types and 14 jurisdictions; 30.8% French (10,062 EN / 4,485 FR). Split by tradition: 11,738 common-law, 2,477 civil-law, 332 bijural. Citation Lookup alone is 7,911 records (54%).

**Per-task record counts and answer type / scorer** (from /about and /transparency):

| Task (id) | n | Answer type | Scorer |
|---|---:|---|---|
| Cite Verify (`neutral_cite_verify`) | 495 | classify citation real / fabricated / ambiguous | deterministic |
| Statute QA (`statute_section_qa`) | 557 | free text | LLM judge (qwen3.8-27b semantic) |
| Jurisdiction Router (`jurisdiction_router_open`) | 57 | letter choice (federal, provincial, shared, federal paramountcy) | deterministic |
| Bijural Equivalence (`bijural_equivalence`) | 175 | free text concept mapping | LLM judge (qwen3.8-27b) |
| Case Treatment (`case_treatment_classification`) | 307 | 6 labels (followed ... overruled) | deterministic |
| Case Outcome (`case_outcome_classification`) | 199 | allowed / allowed in part / dismissed | deterministic |
| Standard of Review (`standard_of_review`) | 186 | reasonableness / correctness / palpable and overriding error | deterministic |
| Doctrine Shift (`doctrine_shift_detection`) | 70 | expanded / narrowed / reversed / unchanged | deterministic |
| Regulation QA (`regulation_section_qa`) | 232 | free text (key elements) | LLM judge (qwen3.8-27b) |
| Tribunal QA (`tribunal_decision_qa`) | 77 | free text disposition | LLM judge (qwen3.8-27b) |
| Multi-Doc Reasoning (`multi_doc_reasoning`) | 130 | followed / distinguished / not followed / cited only | deterministic |
| Temporal Reasoning (`temporal_reasoning`) | 218 | dates, years, ordering | deterministic |
| Citation Lookup (`citation_lookup`) | 7,911 | does the citation exist | deterministic |
| Citation Holding (`citation_holding`) | 1,395 | free text holding | LLM judge (claude-sonnet-5) |
| Limitation Periods (`limitation_period_calc`) | 600 | last day to commence (date) | deterministic |
| Issue Spotting (`issue_spotting`) | 438 | list of issues | LLM judge (claude-sonnet-5, set-level) |
| Citation Resolution (`citation_resolution`) | 1,500 | SCC style of cause + year | deterministic, abstention counts as wrong |

**Scoring.**
- Closed-book: no tools, retrieval or web.
- Structured tasks: exact match with bilingual alias-aware matching; word-overlap fallback at threshold 0.45 for multi-word answers.
- Judge tasks: strict accuracy, a record counts only at judge verdict 1.0 (half credit not counted). Issue Spotting counts when every key issue is found; extra issues not penalized. A lenient rate (verdict >= 0.5) is shown beside it as secondary.
- Headline "suite mean" = unweighted macro mean over the 17 tasks (each task 1/17). 95% CI by parametric binomial bootstrap (100,000 replicates). Per-cell Wilson CIs.
- Empty outputs, refusals, token-budget exhaustion and network failures all count as wrong against the frozen denominator.
- LLM-judge human validation is listed as PENDING.

**License.** No license stated anywhere on canlegalbench.com or the cql.ca announcement.

**Is the test set public / downloadable?** No. The announcement says plainly that until the "open evaluation release" ships, "the data, harness and scoring code are not public". The live site (checked today) still lists the open release as "Coming next", with a "Notify me" signup. The site mentions an API with per-cell fields (ci95, networkFailures) for leaderboard data, not for the records. Nothing found on Hugging Face or GitHub under the CanLegal Bench name (the similarly named UBC "CanLegalRAGBench" is a different, unrelated dataset).

**How to run it.** Not possible today for outside users: no data, harness or scorer published. Only route is to contact partnerships@cql.ca (listed on the post for "questions and partnerships").

**Leaderboard (live, v0.8.3, scoring version 2026-10-09):**

| Rank | Model | Suite mean | 95% CI | Legacy 11-task |
|---|---|---:|---|---:|
| 1 | Claude Fable 5 | 80.4 | 79.2-81.6 | 84.8 |
| 2 | GPT-5.6 Sol | 78.2 | 77.0-79.3 | 84.6 |
| 3 | Gemini 3.1 Pro | 77.5 | 76.4-78.6 | 84.5 |
| 4 | Grok 4.5 | 71.6 | 70.3-72.9 | 78.4 |
| 5 | Cohere Command A+ | 49.8 | 48.2-51.3 | 53.0 |

The 8 Oct 2026 blog snapshot had slightly different numbers (Fable 5 80.1, GPT-5.6 Sol 78.1, Gemini 77.5, Grok 71.7, Command A+ 49.5); the site says the live board is authoritative. Retired rows (30 Sep 2026): Claude Opus 4.8, GPT-5.5, Grok 4.3.

**canada-quant model rows: none.** No Canada Quant Labs (Hugging Face org `canada-quant`) model appears on the board. The only Canadian-built model is Cohere Command A+, which the site says is self-hosted and decoded at vendor-recommended sampling (temperature 0.6, top_p 0.95). The cql.ca models page lists CanLegal Bench under "In flight / Leaderboard live" and does not report any CanLegal score for its own checkpoints.

Hardest tasks (best model below 60%): Citation Resolution (47.1), Citation Holding (56.0), Bijural Equivalence (57.1), Issue Spotting (58.7). Regulation QA tops out at 62.9.

Sources: https://cql.ca/news/canlegal-bench-leaderboard.html , https://canlegalbench.com , https://canlegalbench.com/about , https://canlegalbench.com/transparency , https://cql.ca/models.html

---

## 2. RULER (NVIDIA long-context benchmark)

**Paper.** "RULER: What's the Real Context Size of Your Long-Context Language Models?" https://arxiv.org/abs/2404.06654 . Repo https://github.com/NVIDIA/RULER (Apache-2.0; last commit 3 Nov 2026).

**13 tasks in 4 categories** (official `synthetic` benchmark, `scripts/config_tasks.sh`):
- Retrieval (NIAH, 8): `niah_single_1` (repeat haystack, word key, number value; passkey-like), `niah_single_2` (essay haystack; vanilla NIAH), `niah_single_3` (essay, uuid value), `niah_multikey_1` (4 keys), `niah_multikey_2` (needle haystack; line retrieval), `niah_multikey_3` (uuid keys and values; KV retrieval), `niah_multivalue` (4 values), `niah_multiquery` (4 queries).
- Multi-hop tracing: `vt` (variable tracking).
- Aggregation: `cwe` (common words extraction), `fwe` (frequent words extraction).
- QA: `qa_1` (SQuAD), `qa_2` (HotpotQA).

**Standard context lengths.** 4K, 8K, 16K, 32K, 64K, 128K (official `SEQ_LENGTHS` = 131072, 65536, 32768, 16384, 8192, 4096). The README table reports those six columns plus Avg and two weighted averages; "effective length" = longest length scoring above the Llama-2-7B 4K baseline of 85.6.

**Samples.** Official default `NUM_SAMPLES=500` per task per length. lm-eval also hard-codes `num_samples=500` in each NIAH generator. 13 tasks x 6 lengths x 500 = 39,000 prompts for a full run.

**Decoding.** Official defaults: greedy (temperature 0.0, top_p 1.0, top_k 32).

**Scoring.** String match, case-insensitive substring. `string_match_all` (fraction of reference strings present in the output; used by most tasks) and `string_match_part` (best single match; used for QA). Score per length = mean over samples, reported x100. Task average per length, then average across lengths.

**How it is usually run.**
- Official repo: data is generated per tokenizer and length (`data/prepare.py`), then the model is called through a server (`pred/call_api.py`, supports vllm, trtllm, sglang, openai, gemini), then `eval/evaluate.py`. Command: `bash run.sh MODEL_NAME synthetic`. The README marks the old Docker flow as deprecated and points to branches `rulerv1-ns` and `rulerv2-ns` ("latest pipeline", NeMo-Skills based) for current RULER v1 and the newer RULER v2.
- lm-eval-harness: group `ruler` (all 13), tag `longcxt`. Task names: `niah_single_1`, `niah_single_2`, `niah_single_3`, `niah_multikey_1`, `niah_multikey_2`, `niah_multikey_3`, `niah_multiquery`, `niah_multivalue`, `ruler_vt`, `ruler_cwe`, `ruler_fwe`, `ruler_qa_hotpot`, `ruler_qa_squad`. Default length is only 4096; pass lengths with `--metadata='{"max_seq_lengths":[4096,8192,16384,32768,65536,131072]}'` and set `max_length` in `--model_args`. A tokenizer is required (from `tokenizer`, `pretrained` or `model` arg).

**Offline note.** Data is synthesized at run time from Paul Graham essays (NIAH haystack) and SQuAD / HotpotQA. In the official repo these are downloaded by `scripts/data/synthetic/json/download_paulgraham_essay.py` and `download_qa_dataset.sh`; do this on the login node. Same for the tokenizer.

Sources: https://github.com/NVIDIA/RULER , https://raw.githubusercontent.com/NVIDIA/RULER/main/scripts/config_tasks.sh , https://raw.githubusercontent.com/NVIDIA/RULER/main/scripts/config_models.sh , https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/ruler/README.md , https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/ruler/niah_utils.py , https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/ruler/common_utils.py

---

## 3. LiveCodeBench

**Current version: `release_v6`** is still the newest release listed in the official repo README (no v7 found). Problems come from LeetCode, AtCoder and Codeforces. Repo https://github.com/LiveCodeBench/LiveCodeBench (MIT; last commit Jul 2025).

**Problem counts (cumulative from May 2023):**

| Release | Window | Problems | Added |
|---|---|---:|---:|
| release_v1 | May 2023 - Mar 2024 | 400 | 400 |
| release_v2 | to May 2024 | 511 | 111 |
| release_v3 | to Jul 2024 | 612 | 101 |
| release_v4 | to Sep 2024 | 713 | 101 |
| release_v5 | to Jan 2025 | 880 | 167 |
| release_v6 | to Apr 2025 | 1,055 | 175 |

Fine-grained tags exist (`v1`, `v2`, `v1_v3`, `v4_v5`, presumably `v6`) to select only the problems added in a given release. `release_latest` is the default.

**Recommended date window.** The official leaderboard default for v6 is **2024-08-01 to 2025-05-01 = 454 problems**, reported as Pass@1 overall plus Easy / Medium / Hard. Many technical reports instead use the Jan-Apr 2025 slice (e.g. the vLLM semantic-router evalscope config uses v6 with `start_date 2025-01-01`, `end_date 2025-04-30`, 175 problems, which equals the v6-only additions). Pick the window by your models' training cutoffs: the newest problems are from April 2025, which is older than most 2026 models' cutoffs, so contamination control is weak for current models.

**Release dates for contamination control.** Yes. Every problem is tagged with a contest/release date and difficulty; `lcb_runner/evaluation/compute_scores.py --start_date YYYY-MM-DD --end_date YYYY-MM-DD` scores any window.

**Scoring.** pass@1 and pass@5 using a modified APPS checker. Official generation default n=10, temperature 0.2 (pass@1 estimated from the 10). Each problem has public examples in the statement plus hidden tests; the score is on the hidden tests (the HF card: "input/output examples, and hidden test cases"). The default `code_generation_lite` set has pruned test cases; `--not_fast` uses the original full tests. Timeouts can shift scores by < 0.5 points; lower `--num_process_evaluate` or raise `--timeout` if results look unstable.

**How it is run.**
- Official: `uv venv --python 3.11; uv pip install -e .`, then `python -m lcb_runner.runner.main --model {name} --scenario codegeneration --evaluate --release_version release_v6` (uses vLLM for local models; `--local_model_path` for a local checkpoint; `--tensor_parallel_size`). Models must be registered in `lcb_runner/lm_styles.py`. Generated outputs can also be scored with `lcb_runner.runner.custom_evaluator --custom_output_file`, which suits a compound system served behind an OpenAI-compatible endpoint. Other scenarios: `selfrepair`, `testoutputprediction`, `codeexecution`.
- lm-eval-harness: no confirmed built-in task. Open feature requests (#2766, #2944, #3326, #3396; #3396 still asking for updates in Apr 2026). Alternatives with LCB tasks: HF lighteval (`lcb`, dataset `lighteval/code_generation_lite`) and ModelScope evalscope (`live_code_bench`, sandboxed execution).

**Offline note.** The HF dataset `livecodebench/code_generation_lite` (4.49 GB total) is a loading-script dataset; the Hub viewer reports "Dataset scripts are no longer supported" with current `datasets`. Either pin an older `datasets` that still runs scripts, or download the raw JSONL files on the login node and load them directly. Execution of generated code needs a sandbox on the compute node.

Sources: https://github.com/LiveCodeBench/LiveCodeBench , https://huggingface.co/datasets/livecodebench/code_generation_lite , https://livecodebench.github.io/leaderboard.html , https://github.com/eleutherai/lm-evaluation-harness/issues/3396 , https://github.com/vllm-project/semantic-router/blob/922020e98299dc1575968be8fdda7be5d6ff47cc/bench/router_flow/real_eval/evalscope_suite.yaml

---

## 4. MMMU (val, n=900) and OCRBench (n=1000) in lmms-eval 0.7.3

lmms-eval v0.7.3 exists (released 28 Aug 2026). Newer v0.7.4 came out 30 Oct 2026. Relevant fixes: v0.7.3 "fix(mmmu): preserve full candidate list for open-ended eval_open scoring" (#1471) and "normalize fullwidth ASCII in OCRBench scoring" (#1415). v0.7.4 adds an MMMU fix for images referenced twice (#1589), so 0.7.3 and 0.7.4 MMMU numbers may differ slightly. Pin the version.

**MMMU val**
- Task name: `mmmu_val` (group/tag also includes it in `public_eval_qwen3_5_family`, `public_eval_gpt5_family`).
- Dataset: `lmms-lab-encoder/MMMU`, split `validation` (900 questions).
- Output type `generate_until`. Default prompt: "Answer with the option's letter from the given choices directly." for multiple choice; "Answer the question using a single word or phrase." for open-ended. Model-specific variants exist (e.g. `qwen3_vl`).
- Metric `mmmu_acc`: multiple choice parsed with the official MMMU parser (`parse_mmmu_multi_choice_response`); open-ended via `parse_open_response` + `eval_open` (normalized string containment, exact match for numbers). Aggregate = instance-level (micro) accuracy over all 900, with per-subject breakdown printed. Reported as a fraction (e.g. 0.747 = 672/900).

**OCRBench**
- Task name: `ocrbench`. Dataset `echo840/OCRBench`, split `test` (1,000 items; `dataset_kwargs: token: True`, so an HF token may be needed when downloading).
- Generation: max_new_tokens 128, temperature 0, greedy.
- Scoring: a sample scores 1 if the ground-truth string (any of the list) is a substring of the prediction. Normal items: fullwidth ASCII folded, lowercased, stripped, newlines to spaces. HME100k (handwritten math) items: newlines and all spaces removed, no lowercasing.
- Metric `ocrbench_accuracy` = Final_score / 1000 (reported publicly as an integer score out of 1000, e.g. 888). Per-category breakdown written to `ocrbench_results.txt`.

Example of these exact numbers in the wild: canada-quant reports MMMU val 0.747 (672/900) and OCRBench 888 for GLM-5.3-Flash-W4A16-MTP (cql.ca/models.html).

Sources: https://github.com/EvolvingLMMs-Lab/lmms-eval/releases , https://raw.githubusercontent.com/EvolvingLMMs-Lab/lmms-eval/v0.7.3/lmms_eval/tasks/mmmu/mmmu_val.yaml , https://raw.githubusercontent.com/EvolvingLMMs-Lab/lmms-eval/v0.7.3/lmms_eval/tasks/mmmu/utils.py , https://raw.githubusercontent.com/EvolvingLMMs-Lab/lmms-eval/v0.7.3/lmms_eval/tasks/ocrbench/ocrbench.yaml , https://raw.githubusercontent.com/EvolvingLMMs-Lab/lmms-eval/v0.7.3/lmms_eval/tasks/ocrbench/utils.py

---

## 5. vLLM Semantic Router (vLLM-SR)

**What it is.** Still at https://github.com/vllm-project/semantic-router (Apache-2.0; docs at https://vllm-sr.ai). Describes itself as "an open, programmable decision layer for models and compute": one OpenAI-compatible API in front of many models; it picks or combines models per request based on signals (domain, context length, etc.) and policy (quality, latency, cost, location). Your harness keeps the agent loop and tools. Latest stable release v0.4.0 "Hermes" (27 Sep 2026); docs on `main` describe a newer "standalone mode" and a "built-in model runtime" available only on the dev channel. Mostly Go.

**Decision 1.0 models** (announced 22 Sep 2026, HF collection `vllm-sr/decision-10`). They are not text generators: given a `state`, named `questions` and caller-supplied candidates they return typed probability distributions. Three answer types: **Choice** (pick one candidate, e.g. route, tool, team), **Noul** (probability a condition is true), **Score** (level distribution on an ordered rubric). Request format is "System One" (`state`, `model`, `questions`).

| Model | Built for | Input budget | Architecture |
|---|---|---|---|
| Decision-1.0-Kai-0.6B | general routing / conditions / action selection | 1,024 tokens | 3-path bidirectional encoder on Vela-1.0-Encoder-307M (from mmBERT-base) |
| Decision-1.0-Lex-0.6B | operational: support, invoices, security incidents, agent traces | 1,024 | same as Kai |
| Decision-1.0-Eos-0.8B | smallest hybrid decoder, longer evidence | 16,384 | Qwen3.5 text backbone (Gated DeltaNet + full attention) + shared candidate head |
| Decision-1.0-Sol-2B | more capacity | 16,384 | as Eos |
| Decision-1.0-Nox-4B | combining conditions, rules, actions | 16,384 | as Eos |
| Decision-1.0-Lux-9B | largest, best overall | 16,384 | as Eos (32 layers) |

Published scores on their own 54-task, 3,766-question suite: Lux 76.94, Nox 73.09, Sol 66.32, Eos 61.89, Kai 53.52. Since then Decision 2.0 / 3.0 and Vela 2.0 collections have been released (Oct 2026), and the docs name `vela3-fast` as the router's default decision model, so Decision 1.0 is no longer the newest.

**License.** Repo Apache-2.0. Decision models: "Decision's contributions use Apache 2.0, with retained upstream terms documented in each repository" (each model repo has NOTICE and LICENSING_STATUS.md). Check the upstream terms per model (mmBERT, Qwen3.5) before redistribution.

**Install and run alongside vLLM.**
- `curl -fsSL https://vllm-sr.ai/install.sh | bash -s -- --channel stable` (or `--channel dev` for current docs), or `pip install --pre vllm-sr` / `uv tool install vllm-sr`. Then `vllm-sr serve` (`--platform cuda` for NVIDIA). Runs as Docker (Linux can use Podman): Router on port 8899 (OpenAI-compatible), Dashboard on 8700, internal model runtime. Optional `--gateway extproc` puts Envoy in front.
- Your vLLM servers stay separate; you register them as backends in `config.yaml` (`providers.models[].backend_refs[]` with `provider: vllm`, `endpoint: host:8000`). Clients call `model: "vllm-sr/auto"`; response headers `x-vsr-selected-decision` and `x-vsr-selected-model` show what was chosen.
- Decision models can also run standalone without the router: `AutoModel.from_pretrained("vllm-sr/Decision-1.0-Kai-0.6B", trust_remote_code=True)` then `model.system_one(...)` (transformers >= 4.57).

**Routing to local OpenAI-compatible endpoints.** Yes. Providers listed: vLLM, Ollama, OpenAI Compatible, Anthropic; `api_format` can be `openai`, `responses`, `anthropic`; multiple replicas per model with load balancing, retries, health checks and cross-model fallback.

**Routing to non-LLM tools.** Partly. Backends are model endpoints; the config accepts non-chat model types with declared capabilities (e.g. `api_format: images`, `capabilities: [image_generation]`), and the Decision models can choose "a tool, a backend, or an available game action" when you call them yourself. I found no documented first-class way for the router to dispatch a request to an arbitrary non-model tool (e.g. a GNN service) other than wrapping that tool behind an OpenAI-compatible endpoint. Treat this as unconfirmed.

**Hardware.** Linux/macOS/WSL2, Docker, Python >= 3.10, about 5 GB disk for images plus 1-1.5 GB per built-in model. CPU-only works: the default decision model (vela3-fast) holds about 7 GB RAM, so give the router about 12 GiB; the 307M embedding model adds about 1.3 GB. NVIDIA needs the NVIDIA Container Toolkit and `--platform cuda` (validated on H200, A100, T4); AMD MI300X/MI325X via ROCm image. Kai/Lex run in FP32 on GPU or CPU. Hardware for Eos-Lux 9B not stated on the pages read.

**Offline note.** `vllm-sr serve` pulls container images and model weights on first start; the docs describe an air-gapped path: run once with `--download-only` (or `hf download`) where there is internet, ship the `models/` directory as the router's model volume (`/app/models`) and set `HF_HUB_OFFLINE=1`. Images must be pulled/saved on the login node.

Sources: https://github.com/vllm-project/semantic-router , https://vllm-sr.ai/blog/decision-models/ , https://huggingface.co/vllm-sr/Decision-1.0-Kai-0.6B , https://vllm-sr.ai/docs/installation/ , https://vllm-sr.ai/docs/installation/model-configuration

---

## 6. EiG-Search (Lu et al., ICML 2024)

**Paper.** "EiG-Search: Generating Edge-Induced Subgraphs for GNN Explanation in Linear Time", Shengyao Lu, Bang Liu, Keith G. Mills, Jiao He, Di Niu. ICML 2024 (PMLR v235). arXiv https://arxiv.org/abs/2405.01762 ; OpenReview https://openreview.net/forum?id=HO0g6cHVZx ; PDF https://raw.githubusercontent.com/mlresearch/v235/main/assets/lu24g/lu24g.pdf

**Official code: yes, it exists.** https://github.com/sluxsr/EiG-Search (linked from the author's page https://sluxsr.github.io/posts/eigsearch/). Single contributor, 19 commits, last commit 3 Feb 2025, 7 stars. **No LICENSE file and no license shown on the repo**, so by default it is all-rights-reserved; ask the authors before redistributing or vendoring. (The paper itself on arXiv is CC BY 4.0.)

**What it outputs.** Subgraph-level explanations: an edge-induced subgraph per instance, obtained by ranking edges by importance and then searching for the best size. So the primary output is edge importance scores plus the selected edge set; node importance is not a direct output (nodes are implied by the selected edges). The paper argues edge induction avoids disconnected nodes that node-induced explainers produce, and that explanation size should be chosen per instance.

**Method.** Training-free, two phases:
1. Edge importance via "Linear Gradients": gradients along the straight line from a baseline (all edge weights 0) to the real graph, to avoid gradient saturation.
2. Linear-time search over edge-induced subgraphs built from the ranked edges (`--linear_search 1`), choosing the subgraph size per instance.
Stated complexity: O(|E|) for phase 1 and O(|E|) overall.

**Runtime vs GOAt.** GOAt ("GOAt: Explaining Graph Neural Networks via Graph Output Attribution", Lu, Mills, He, Liu, Niu, ICLR 2024; arXiv https://arxiv.org/abs/2401.14578 ; code https://github.com/sluxsr/GOAt) gives node and edge importance by analytically expanding the GNN output into contributions; it states no Big-O, only measured times. The EiG-Search paper does not benchmark against GOAt; it only notes in Appendix B.1 that GOAt needs architecture-specific attribution equations while EiG-Search applies to any GNN. Published per-instance times on comparable synthetic node-classification sets (different papers, different hardware, so only indicative):

| Dataset | GOAt (GCN, its Table 3) | EiG-Search (its Table 2) |
|---|---:|---:|
| BA-Shapes | 0.36 s | 0.006 s |
| BA-Community | 0.50 s | 0.007 s |
| Tree-Grid | 0.05 s | 0.003 s |
| BA-2Motifs (graph) | 0.46 s | 0.089 s |
| Mutagenicity (graph) | 0.60 s | 0.14 s |

Both are training-free and fast; for a ~400-node graph either should be well under a second per node.

**Using it in place of GOAt for a 3-layer GCN node classifier on ~400 nodes.**
- Supported setting: the repo supports node classification (datasets `ba_shape`, `ba_community`, `tree_grid`; GNNs `gin`, `gcn`, `sage`). For node classification you choose `topk` (an even number of directed edges, e.g. 12 = top 6 undirected edges) rather than a sparsity; the paper's node-classification experiments used 3-layer GNNs.
- Inputs needed: the trained model, node features `x`, `edge_index` (COO), the target node index, and the predicted class/logits. Everything is PyTorch Geometric-based: environment pins `pyg 2.1.0`, `pytorch 1.11.0`, CUDA 11.3, python 3.9, `torch-scatter`, `torch-sparse`, `torch-cluster`, `networkx`.
- Main practical work: in the released `main.py` the node-classification path calls the repo's own model classes in `GNN_Models/`, using `gnn_model(x, edge_index)` for logits and a custom `gnn_model.fwd(x, edge_index, de=e, epsilon=epsilon)` to score each edge, then `torch.topk` over the per-edge scores. So a stock PyG `GCNConv` model will not plug in as-is: either (a) port your trained weights into the repo's GCN class (if layer shapes match), or (b) reimplement the edge-importance step for your model, e.g. make the GCN accept an `edge_weight` and compute Linear-Gradient attributions of the target logit w.r.t. edge weights interpolated from 0 to 1, then apply the linear search. Restrict to the target node's 3-hop computation subgraph (PyG `k_hop_subgraph`), which on 400 nodes is small.
- Expect to modernize dependencies: the pinned torch 1.11 / PyG 2.1 stack is old; on H100 (needs CUDA >= 11.8 builds) you will likely run it on current torch + PyG and fix API drift, or run it on CPU (cheap at this graph size).
- Output to report: per-edge importance scores and the selected edge set per explained node; if you need node scores comparable to GOAt's, derive them (e.g. sum of incident edge scores), which is your own choice, not part of EiG-Search.

Sources: https://arxiv.org/abs/2405.01762 , https://arxiv.org/html/2405.01762v2 , https://github.com/sluxsr/EiG-Search , https://raw.githubusercontent.com/sluxsr/EiG-Search/main/main.py , https://sluxsr.github.io/posts/eigsearch/ , https://arxiv.org/abs/2401.14578 , https://arxiv.org/html/2401.14578v1

---

## 7. Repo / code-graph tools for LLMs (brief)

All parse a repository (mostly tree-sitter) into a graph of files/symbols/calls/imports and expose it to agents, usually via MCP; all run locally.

- **CodeGraph**: https://github.com/colbymchenry/codegraph . MIT. SQLite graph in `.codegraph/`, file watcher, one default MCP tool `codegraph_explore` (more via `CODEGRAPH_MCP_TOOLS`). `npm i -g @colbymchenry/codegraph; codegraph install; codegraph init`.
- **codebase-memory-mcp**: https://github.com/DeusData/codebase-memory-mcp . MIT. Single native C binary with vendored tree-sitter grammars; call tracing, impact analysis, architecture queries over MCP.
- **Serena**: https://github.com/oraios/serena . Uses real language servers (LSP) for symbol-level search and edits rather than a stored graph. License changed in Sep 2026 to component-based licensing with Serena under GPL-3.0-or-later (older third-party pages still say MIT).
- **Graphify**: https://github.com/Graphify-Labs/graphify . Builds one knowledge graph from code plus docs, SQL schemas, PDFs and more; `/graphify` skill or MCP server. License reported inconsistently by third parties (MIT vs Apache-2.0), check the repo.
- (Avoid for work use without a license: GitNexus is PolyForm Noncommercial per comparison pages.)

Sources: https://github.com/colbymchenry/codegraph , https://github.com/DeusData/codebase-memory-mcp , https://github.com/oraios/serena , https://github.com/Graphify-Labs/graphify , https://repowise.dev/blog/comparisons/best-code-graph-mcp-servers

---

## Uncertain / not found

1. CanLegal Bench license: not stated anywhere.
2. CanLegal Bench release date for data/harness/scorer: none given; only "coming next" with a notify-me signup.
3. CanLegal prompts, max token budgets and judge prompts for outside reproduction: not published. Two judge families are named (qwen3.8-27b variants, claude-sonnet-5) but not their prompts.
4. Whether canada-quant has evaluated its own checkpoints on CanLegal Bench privately: not found; no public row.
5. RULER: current recommended pipeline is said to be the `rulerv1-ns` / `rulerv2-ns` branches; I did not read those branches, so their exact sample counts and RULER v2 task list are unverified.
6. LiveCodeBench: whether a v7 release is planned or exists outside the README; whether lm-eval-harness has merged a LiveCodeBench task (a commit "feat(tasks): add LiveCodeBench code-generation benchmark" is referenced on issue #2766 but I did not confirm it landed in a release).
7. LiveCodeBench: exact count of problems with hidden tests vs public-only is not documented; the HF card says each problem has hidden test cases.
8. lmms-eval MMMU: whether the multiple-choice parser falls back to a random option when no letter is parsed (the original MMMU code does; the lmms-eval wrapper delegates to `mmmu_mcq_utils`, which I did not read). Matters for reproducibility across seeds.
9. vLLM-SR: hardware requirements for Decision-1.0 Eos/Sol/Nox/Lux (only Kai/Lex FP32 CPU-or-GPU behaviour confirmed); whether Decision 1.0 models are now natively wired into the router (blog of 22 Sep said "planned next"; a later Makefile commit mentions "Built-in model runtime: Decision 1.0, Vela 1.0 and 2.0", and the docs name vela3-fast as default).
10. vLLM-SR routing to non-LLM tools: no documented first-class mechanism found beyond model endpoints with declared capabilities.
11. EiG-Search: no license; exact number of interpolation steps for Linear Gradients and the precise node-classification code path (k-hop restriction) not confirmed from the code excerpt I read. Released `main.py` appears to score edges by per-edge perturbation through a custom `fwd` method; how that maps to the paper's Linear Gradient formula was not verified line by line.
12. GOAt: no formal complexity stated in the paper; runtime comparison above is across two papers, not a head-to-head.
