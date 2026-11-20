# Run log: decisions and API spend

One line per decision, with its reason. Times are America/Vancouver unless marked. API spend is Anthropic
(Haiku 5.5, GRAFT answers) unless marked; Cohere trial calls were free.

## 2026-11-20

### Decisions
- Qwen3.8-27B served as W4A16 (ours). Reason: rule 4.1, MATH-500 0.984 = FP8 0.984, inside the 1.0-point margin.
- Phi dropped, gpt-oss-20b (medium) in its place. Reason: user decision (protocol-v9), from the MATH-500 small set (24/25 vs 21/25, a tenth of the tokens).
- All models use native tool calls, native-tool prompt wording, no tools on the forced last round. Reason: smoke checks showed text tool lines failing for gpt-oss and Qwen (protocol-v9 addenda 1-2).
- Smoke check allows "no answer at the token cap" and "no final text after the tool budget", reported per item. Reason: both are the model running out, not a pipeline fault; such items score wrong for every model.
- Calibration data kept (ultrachat_200k, 512 conversations). Reason: leakage check flagged 0 of 3,132 messages.
- GRAFT: GOAt stays the default explainer, not EiG. Reason: rule 4.3, EiG 36% < 37% (one question), though 2.6x faster.
- GRAFT: embedding entity linking (link_embed_k 5) rejected. Reason: free check gold-present fell from 51% to 22-25%.
- GRAFT: 50/50 hybrid not adopted. Reason: gold-present up (51 -> 54-55%) but 3 paid repeats each gave 32.0% mean accuracy vs mode C's 38%.
- GRAFT: bigger subgraphs (800, 1,600 nodes) not adopted with the 400-node GNN. Reason: gold-in-subgraph 63 -> 71 -> 79% but gold-in-final-50 flat (53-54%), query time 0.2 -> 2.3 s.
- GRAFT: LLM entity linking not tested. Reason: only 1 of 100 questions hits the no-link fallback (user's condition was "more than a few").
- GRAFT top-k hybrid: k=5 not paid (gold-present 51% = baseline 51%, does not beat it); k=10 qualifies for 3 paid repeats (53% > 51%). Paid repeats wait for the API key (user away; the key is never stored).
- Command A+ kept in the test. Reason: third attempt passed the smoke check on Fir (9 items, no pipeline problem); the first two failures were the old final-round bug and a long load on Nibi scratch.
- Router-B labels: (superseded below) cause found (the label script makes one call with a tools-offering prompt and no tool loop, so 22 of 34 checked Qwen labels end at a TOOL line with no answer); relabelling deferred. Reason: correct labels need the full loop over 4,856 questions per model (~30 GPU-h per 1-GPU model, far more for Command A+); first see whether the three-model oracle on the small test shows a routing gain worth it.
- GRAFT question-graph option: built now, run when the API key is available. Reason: it needs a real Haiku call per question to parse the question (a fake gateway fakes every call), so no free check is possible.
- Smoke check: "stopped with no answer text" now covers any sample that ends with a normal stop and no answer text, not only the forced last round. Reason: Qwen spent 29K and 19K tokens thinking on the LiveCodeBench smoke item, stopped mid-thought where it said it would run code (likely a tool call attempted inside its thinking, which the template does not support), and gave no answer; that is model behaviour, scored wrong. Limitation noted: this may cost Qwen some LiveCodeBench items.
- GRAFT question-graph plumbing check passed (fake gateway, empty parse): gold-in-subgraph 63%, gold-in-final 51%, identical to mode C, so the parse-before-fork path works; the real run waits for the key.
- GRAFT 1,600-node GNN (gnn_bge_1600w, same data and settings, 35 min on one H100, val recall@10 0.590 vs 0.586) not adopted, no paid runs. Reason: free check gold-in-final 48% < 51% (gold in subgraph 79% vs 63%), query time 2.25 s vs 0.20 s.
- GRAFT paid batch 1 (6 jobs): 3 died at start without spending (jobs starting in the same second got the same run folder); the first question-graph run crashed after its 100 parse calls (texts not embedded before workers fork; fixed with a test that fails on the old code). Reruns: question graph as one job with repeats: 3, plus one more top-10 repeat. Reason: complete 3 repeats each, one job per config so folders cannot clash.
- Router-B labels un-deferred (user): rerun through the real Flotilla loop (flotilla/label_loop.py: same prompts, native tools, verifier, retry) on the 4,760 clean pool questions, 16 shards of about 300, for Qwen (W4A16) and gpt-oss-20b (user OK); Command A+ only if it passes rule 4.2. Old labels kept as router-labels-v1-broken-{qwen,phi}. Reason: routing happens either way, so the data must exist; v1 ran no tool loop.
- Label path tested first on 16 pool questions per model (4 per task type) before the 32 shard jobs. Reason: test small before big.
- Router B: ModernBERT-base (pretrained, fully fine-tuned, two heads) stays the main router; a cheap baseline is added (bge-small question embeddings + logistic regression per head). Both train on the clean pool only and are compared on the same held-out 10%; the simple one is used if about as good (user).
- GRAFT question graph not adopted. Reason: 3 paid repeats 39/37/35 (mean 37.0) vs mode C 38 (single GOAt run); gold-in-final 50% vs 51%; parse worked (edges for 100/100 questions, 99 matched a graph entity) but adds a Haiku call per question for no gain.
- GRAFT top-10 hybrid not adopted. Reason: 3 paid repeats 33/31/29 (mean 31.0) vs 38; gold-in-final 53-54% but embedding near-misses distract the answer model (same as the 50/50 hybrid).
- Open: the 38 baseline is one GOAt run while the variants are EiG; 3 EiG baseline repeats (about $0.08) would make the comparison exact. Waits for the key.
- Label grader fixed: code answers have their markdown fences stripped before tests run, as the small-test scorer does. Reason: gpt-oss fences its code, so every fenced answer failed (0/4 -> 3/4 on the label test); the v1 labels had the same bug.
- Label test passed (16 questions per model, real loop): Qwen 14/16, gpt-oss 12/16 (one gpt-oss item: no JSON answer block on the retry, a model format failure, scored wrong). 32 label shards (16 per model, about 300 questions each) submitted as three-cluster twins without a per-shard smoke check. Reason: the test already proved the path; limits Qwen 3:30:00, gpt-oss 2:30:00 from measured throughput (+50%).
- Command A+ dropped. Reason: rule 4.2 (v9), Command A+ alone minus Qwen alone = -0.104 mean over 11 benchmarks, 95% bootstrap CI [-0.143, -0.066]; it is right on only 3 of 362 items that neither other model gets, at 4 GPUs vs 1. No Command A+ labels.
- Vision stays with Qwen3.8 (no fallback model needed). Reason: Qwen reads images itself (MMMU 0.756, OCRBench 0.88); the vision fallback in 4.2 was for the case Qwen could not.
- Router B goes ahead on Qwen + gpt-oss labels. Reason: perfect Qwen/gpt-oss router 0.910 vs Qwen alone 0.877 (+3.3 points), mostly RULER 32K (+0.20, gpt-oss 0.867 vs Qwen 0.697). Report: reports/smalltest_three_models.md.

### API spend (Anthropic)
| When | What | Runs | Cost |
|---|---|---|---|
| 2026-11-19/20 | GRAFT EiG variant A, real | 1 | $0.027 |
| 2026-11-20 | GRAFT mode C + 50/50 hybrid, GOAt and EiG (3 runs each; 2 of the 3 per variant came from re-run commands) | 6 | $0.163 |
| 2026-11-20 | GRAFT top-10 hybrid, EiG (2 of 3 repeats; 33%, 31%) | 2 | $0.054 |
| 2026-11-20 | GRAFT question graph, first try: 100 parse calls, crashed before answering | 1 | $0.010 |
| 2026-11-20 | GRAFT question graph, 3 repeats (incl. 300 parse calls) | 1 job | $0.110 |
| 2026-11-20 | GRAFT top-10 hybrid, 3rd repeat (29%) | 1 | $0.027 |
| | **Total today so far** | | **$0.39** |
