# Flotilla registry: candidates, setups, runs

Approved by the user 2026-11-21. **IDs are frozen** (user, 2026-11-21): once applied, an ID is never renumbered or reused. New candidates and setups get the next free number; a dropped item keeps its ID with a status. Next free IDs: see the last row of each table.

Three layers (user, 2026-11-21):

- **Candidate** (F01, F02...): the method, defined by its parts (section 2). Two with identical parts share one ID.
- **Setup** (S102 onward; GRAFT has S01-S101, so S IDs are unique across both repos): a candidate plus benchmark,
  item set, scoring, token budget and benchmark settings. Every result points to a setup.
- **Run**: one execution of a setup (a run folder or label shard set). Raw run folders and recorded configs keep their
  old names; this registry maps them.

Built from `configs/systems/`, every run record in `experiments/`, the run log, the router code, and the saved traces
and job logs on Fir and Nibi (Trillium has no open socket here and was not checked). IDs are fixed and never reused.
Outside models and builds keep their own names: Qwen3.8-27B BF16 (official), RedHat Qwen3.8-27B INT4,
Phi-4-reasoning-plus BF16, NVIDIA Phi FP8, AMD Phi W4A16, Phi-4-reasoning BF16, gpt-oss-20b (MXFP4, bare), vLLM
Semantic Router's `vela3-fast`, and published CQL numbers. GRAFT's candidates are G01, G02... ([GRAFT
registry](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/reference/REGISTRY.md)); a Memory route names
the GRAFT candidate it uses.

Status: **scored**, **free check only** (dry run or fake model, no accuracy), **cancelled**, **never run**.

History: in draft 1 the bare gpt-oss checks and Phi were candidates; the saved traces showed they were bare runs of outside models, so draft-1 F10-F30 became F08-F28 before approval.

**"Plain Qwen" for the final benchmarks is F01**, the bare model with no loop, separate from F06 (the same build inside
the Flotilla loop). Its test 01 run and its final-benchmark runs are different setups of F01.

## 1. Candidates

| ID | What it is | Old names | Tests | Status | Why |
|---|---|---|---|---|---|
| F01 | Qwen3.8-27B W4A16, our GPTQ build, bare (no loop) | "W4A16-ours", "plain Qwen", `math500-qwen-w4a16-ours`, `quant/qwen3.8-27b-w4a16` | 01; final benchmarks | scored | MATH-500 0.984, 0.0 below our FP8, inside rule 4.1's 1 point: the build Flotilla serves, and the plain-Qwen comparison |
| F02 | Qwen3.8-27B FP8, our build, bare | "FP8-ours", `math500-qwen-fp8-ours` | 01 | scored | 0.984; rule 4.1 chose the 4-bit build (F01) |
| F03 | Phi-4-reasoning-plus FP8, our build, bare | `math500-phi-fp8-ours` | 01 | scored | 0.820, 377 of 500 at the 30,000-token cap; Phi dropped (v9) |
| F04 | Phi-4-reasoning-plus W4A16, our build, bare | `math500-phi-w4a16-ours` | 01 | scored | 0.786; Phi dropped (v9) |
| F05 | F02 in the Flotilla loop | `qwen_fp8_alone` | none | never run (inferred) | config written; no trace on Fir or Nibi. The v9 "Qwen FP8 25 of 25" is F02's test 01 run on the 25 dev items (traces confirm) |
| F06 | F01 in the Flotilla loop: thinking on, tools on, 1 sample | **"Qwen alone"**, `qwen_w4a16_alone`, `smalltest-qwen_w4a16_alone-*`, `router-labels-loop-qwen`; **route Deep+Tools**, `qwen_strategy_deep_tools` | 02, 03, 04 | scored | small test 0.877, kept alone (v10); as Deep+Tools 0.943 on the pool |
| F07 | gpt-oss-20b (MXFP4) in the loop, reasoning medium | "gpt-oss", `gptoss_alone`, `smalltest-gptoss_alone-*`, `router-labels-loop-gptoss` | 02, 03 | scored | dropped (v10): router B's gain over F06 was +0.4, under the 1-point bar |
| F08 | Command A+ (official FP8, 4 H100s) in the loop | "Command A+", "cmda", `cmda_local`, `smalltest-cmda_local` | 02 | scored | dropped (rule 4.2): F08 minus F06 = -0.104, 95% CI [-0.143, -0.066] |
| F09 | Command A+ through Cohere's hosted API in the loop | `cmda_alone`, `runs/cmda-smalltest` | 02 | cancelled | screen runs discarded (tool calls rejected with 422, then the trial key's 1,000 calls a month ran out); replaced by F08 (v8) |
| F10 | Phi-4-reasoning-plus FP8 (F03) in the loop | "Phi", "Phi in the loop" | none | never run | Phi was never run in the loop: v9's Phi figure (21 of 25, 24,354 tokens, 18 at the cap) is F03's test 01 run on the 25 dev items (traces confirm) |
| F11 | Qwen + Phi, both solving in the loop | `qwen_phi` | none | never run | the v5 configuration; superseded when Phi was dropped (v9) |
| F12 | Router A: `vela3-fast` task-type classifier + fixed decision table over models | "router A", `flotilla/router_a.py` | protocol 4.5 | scored (routing accuracy) | 0.744 on 500 pool items ([legacy record](../../experiments/legacy/README.md)); not used once Flotilla became one model (v10) |
| F13 | Router B: ModernBERT-base fine-tune choosing F06 or F07 | "router B", `router_b_modernbert` | 03 | scored | +0.4 over F06 on 476 held-out questions, under the 1-point bar; not used |
| F14 | Router B lite: bge-small + logistic regression choosing F06 or F07 | "router B lite", `router_b_lite` | 03 | scored | -0.8 over F06; not used |
| F15 | Route Fast: F01 in the loop, thinking off, no tools | **Fast**, `qwen_strategy_fast` | 04 | scored | pool 0.903; LongMemEval labels done |
| F16 | Route Tools: thinking off, tools | **Tools**, `qwen_strategy_tools` | 04 | scored | pool 0.925 |
| F17 | Route Deep: thinking on, no tools | **Deep**, `qwen_strategy_deep` | 04 | scored | pool 0.952 |
| F18 | Route Vote: thinking on, no tools, 5 samples at 0.6, majority | **Vote**, `qwen_strategy_vote` | 04 | scored | pool 0.967, the best fixed route and the routers' reference |
| F19 | Route Vote+Tools: thinking on, tools, 5 samples | **Vote+Tools**, `qwen_strategy_vote_tools` | 04 | scored | pool 0.963 |
| F20 | Route Memory: F15 + GRAFT G35 facts from the item's own history | **Memory**, `qwen_strategy_memory` | 04 | running | LongMemEval labels in progress |
| F21 | Route Memory+Deep: F17 + G35 | **Memory+Deep**, `qwen_strategy_memory_deep` | 04 | running | as F20 |
| F22 | Route Vote+Memory: F18 + G35 | **Vote+Memory**, `qwen_strategy_vote_memory` | 04 | running | as F20 |
| F23 | Route Deep+Tools+Memory: F06 + G35 | **Deep+Tools+Memory**, `qwen_strategy_deep_tools_memory` | 04 | running | shards done; judge next |
| F24 | Strategy router: ModernBERT label classifier, trained on test 04 run-03 labels | "router i", "label classifier", `--routers label` | 04 | free check only | dry run on the pool labels; the real training on run-04-lme labels will be a new ID |
| F25 | Strategy router: ModernBERT success predictor + dev-tuned threshold, run-03 labels | "router ii", `success` | 04 | free check only | as F24 |
| F26 | Strategy router: bge-small + logistic regression, run-03 labels | "router iii", `bge_lr` | 04 | free check only | as F24 |
| F27 | Strategy router: nearest neighbours on bge-small, run-03 labels | "router iv", `knn` | 04 | free check only | as F24 |
| F28 | Live RL router over route steps, run-03 labels | "router 5", "RL router", `flotilla/rl_router.py` | 04 | free check only | fake-model check (`rl-check`); the real one starts from the best run-04-lme router, a new ID |

| F29 | Strategy router: ModernBERT label classifier, trained on run-04-lme | "router i" on run-04-lme | 04 | scored | dev 0.904 (Vote 0.966): dropped by the keep rule |
| F30 | Strategy router: ModernBERT success predictor + dev threshold, run-04-lme | "router ii" | 04 | scored | dev 0.959 at 72% of Vote's GPU-seconds: kept (within 1 point, less compute) |
| F31 | Strategy router: bge-small + logistic regression, run-04-lme | "router iii" | 04 | scored | dev 0.963 at 91% of Vote's GPU-seconds: kept; best dev accuracy |
| F32 | Strategy router: nearest neighbours on bge-small, run-04-lme | "router iv" | 04 | scored | dev 0.952: dropped by the keep rule |
| F33 | Route Fast (F15) + verifier v2's LLM check where no exact check exists (Qwen checker, thinking off) | "Fast + LLM check", `qwen_strategy_fast_llmv` | 06 | running | baseline F15 |
| F34 | Route Deep (F17) + the same LLM check | "Deep + LLM check", `qwen_strategy_deep_llmv` | 06 | running | baseline F17 |
| F35 | Reasoning-graph route: Qwen answers in planned steps and writes question, steps, results and notes into an empty GRAFT graph (C v2's work layer, no documents) | "reasoning graph", `reason_graph` | none yet | never run | design: [reasoning_graph_route_design.md](../design/reasoning_graph_route_design.md); pilot against Deep and Fast |
Not candidates: `qwen_alone.json` (the v5 placeholder with quant "TBD", replaced by F06's config, never run as
such); the oracle ("some route right", a ceiling); the always-wrong audits.

## 2. Candidate parts

| ID | Model and build | Loop | Thinking | Tools | Samples | Memory | Picks between | Trained on (labels) |
|---|---|---|---|---|---|---|---|---|
| F01 | Qwen3.8-27B W4A16 (ours) | none (bare) | on | - | 1 | - | - | - |
| F02 | Qwen3.8-27B FP8 (ours) | none | on | - | 1 | - | - | - |
| F03 | Phi-4-reasoning-plus FP8 (ours) | none | on | - | 1 | - | - | - |
| F04 | Phi-4-reasoning-plus W4A16 (ours) | none | on | - | 1 | - | - | - |
| F05 | Qwen3.8-27B FP8 (ours) | Flotilla | on | yes | 1 | - | - | - |
| F06 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | yes | 1 | - | - | - |
| F07 | gpt-oss-20b MXFP4 | Flotilla | medium | yes | 1 | - | - | - |
| F08 | Command A+ FP8 (official) | Flotilla | on | yes | 1 | - | - | - |
| F09 | Command A+ (Cohere API) | Flotilla | high | yes | 1 | - | - | - |
| F10 | Phi-4-reasoning-plus FP8 (ours) | Flotilla | on | yes | 1 | - | - | - |
| F11 | Qwen W4A16 + Phi FP8 | Flotilla | on | yes | 1 each | - | - | - |
| F12 | `vela3-fast` + decision table | router | - | - | - | - | models by task type | none (off the shelf) |
| F13 | ModernBERT-base fine-tune | router | - | - | - | - | F06, F07 | test 03 run-02 router-B labels |
| F14 | bge-small + logistic regression | router | - | - | - | - | F06, F07 | test 03 run-02 router-B labels |
| F15 | Qwen3.8-27B W4A16 (ours) | Flotilla | off | - | 1 | - | - | - |
| F16 | Qwen3.8-27B W4A16 (ours) | Flotilla | off | yes | 1 | - | - | - |
| F17 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | - | 1 | - | - | - |
| F18 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | - | 5 (0.6, majority) | - | - | - |
| F19 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | yes | 5 (0.6, majority) | - | - | - |
| F20 | Qwen3.8-27B W4A16 (ours) | Flotilla | off | - | 1 | G35 | - | - |
| F21 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | - | 1 | G35 | - | - |
| F22 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | - | 5 (0.6, majority) | G35 | - | - |
| F23 | Qwen3.8-27B W4A16 (ours) | Flotilla | on | yes | 1 | G35 | - | - |
| F24 | ModernBERT-base, label classifier | router | - | - | - | - | F06, F15-F19 | test 04 run-03 |
| F25 | ModernBERT-base, success predictor | router | - | - | - | - | F06, F15-F19 | test 04 run-03 |
| F26 | bge-small + logistic regression | router | - | - | - | - | F06, F15-F19 | test 04 run-03 |
| F27 | bge-small + kNN | router | - | - | - | - | F06, F15-F19 | test 04 run-03 |
| F28 | RL policy over route steps, with a stop action | router | - | - | - | - | chains of F06, F15-F19 | test 04 run-03 (prior) |
| F33 | Qwen3.8-27B W4A16 (ours) | Flotilla, verifier v2 with LLM check | off | - | 1 | - | - | - |
| F34 | Qwen3.8-27B W4A16 (ours) | Flotilla, verifier v2 with LLM check | on | - | 1 | - | - | - |
| F35 | Qwen3.8-27B W4A16 (ours) | plan, up to 6 steps, final, written into an empty GRAFT work graph | off | - | 1 | GRAFT work layer only | - | - |

Flotilla loop = solver prompt v1, verifier v2 with one retry, up to 3 native tool rounds when tools are on, 32,768
output tokens; one sample runs at temperature 0.

## 3. Setups

| Setup | Candidate | Benchmark and items | Scoring | Budget and settings | Runs | Status |
|---|---|---|---|---|---|---|
| S102 | F01 | MATH-500, all 500 | math-verify | 131,072 tokens, greedy (`eval_math500.py`) | `math500-qwen-w4a16-ours` (Nibi 28087948) | scored 0.984 |
| S103 | F02 | MATH-500, all 500 | math-verify | as S102 | `math500-qwen-fp8-ours` | scored 0.984 |
| S104 | Qwen3.8-27B BF16 (outside) | MATH-500, all 500 | math-verify | as S102 | `math500-qwen-bf16` | scored 0.978 |
| S105 | RedHat Qwen INT4 (outside) | MATH-500, all 500 | math-verify | as S102 | `math500-qwen-int4-redhat` | scored 0.988 |
| S106 | F03 | MATH-500, all 500 | math-verify | 30,000 tokens, greedy | `math500-phi-fp8-ours` | scored 0.820 |
| S107 | F04 | MATH-500, all 500 | math-verify | as S106 | `math500-phi-w4a16-ours` | scored 0.786 |
| S108 | Phi-4-reasoning-plus BF16 (outside) | MATH-500, all 500 | math-verify | as S106 | `math500-phi-bf16` | scored 0.824 |
| S109 | NVIDIA Phi FP8 (outside) | MATH-500, all 500 | math-verify | as S106 | `math500-phi-fp8-nvidia` | scored 0.818 |
| S110 | AMD Phi W4A16 (outside) | MATH-500, all 500 | math-verify | as S106 | `math500-phi-w4a16-amd` | scored 0.776 |
| S111 | gpt-oss-20b, reasoning low (outside, bare) | MATH-500, 25 dev items | math-verify | 32,768 tokens | `st-math500-gptoss20b-low` | scored 23/25 |
| S112 | gpt-oss-20b, reasoning medium (outside, bare) | MATH-500, 25 dev items | math-verify | 32,768 | `st-math500-gptoss20b-medium` | scored 24/25 |
| S113 | gpt-oss-20b, reasoning high (outside, bare) | MATH-500, 25 dev items | math-verify | 32,768 | `st-math500-gptoss20b-high` | scored 21/25 |
| S114 | Phi-4-reasoning BF16, not "plus" (outside, bare) | MATH-500, 25 dev items | math-verify | 24,576 | `st-math500-phi4-reasoning` (Nibi 28075001) | scored 21/25, 20 cut at the cap; not the figure v9 quotes |
| S115 | F06 | small test, 5% dev of 11 benchmarks (362 items) | each benchmark's own metric (protocol 1.3) | loop, 32,768 | `smalltest-qwen_w4a16_alone-{math,mixed,ruler,vision}` | scored 0.877 |
| S116 | F07 | small test, 9 text benchmarks | as S115 | loop, 32,768 | `smalltest-gptoss_alone-{math,mixed,ruler}` | scored 0.772 |
| S117 | F08 | small test, 11 benchmarks | as S115 | loop, 32,768, 4 H100s | `smalltest-cmda_local` (Fir 4631004) | scored 0.773 |
| S118 | F09 | small test (screen) | as S115 | loop, hosted API, 20 calls a minute | `runs/cmda-smalltest` | cancelled, discarded |
| S119 | F06 | router pool, 4,760 clean questions | router-label graders | loop | `router-labels-loop-qwen` (16 shards) | scored |
| S120 | F07 | router pool, 4,760 | router-label graders | loop | `router-labels-loop-gptoss` | scored |
| S121 | Qwen3.8-27B BF16 (outside), one call | router pool, 4,856 | router-label graders | one call, no tool loop, 16,384 tokens | `router-labels-v1-broken-qwen` | invalid (section 5) |
| S122 | Phi-4-reasoning-plus BF16 (outside), one call | router pool, 4,856 | router-label graders | as S121 | `router-labels-v1-broken-phi` | invalid (section 5) |
| S123 | F12 | 500 clean router-pool items with known task types | routing accuracy | `vela3-fast` | [`experiments/legacy/router_a_pool500.json`](../../experiments/legacy/router_a_pool500.json) | scored |
| S124 | F13 | router pool held-out, 476 | accuracy of the picked model's S119/S120 answer | | `router/router_b_modernbert` | scored 0.899 |
| S125 | F14 | router pool held-out, 476 | as S124 | | `router/router_b_lite` | scored 0.887 |
| S126 | F15 | strategy pool, 1,450 (plus the 50-question pilot) | router-label graders, fixed (run-03) | loop, 32,768, H100 | test 04 run-01 pilot, run-02 shards, run-03 reruns | scored 0.903 |
| S127 | F16 | strategy pool, 1,450 | as S126 | as S126 | as S126 | scored 0.925 |
| S128 | F17 | strategy pool, 1,450 | as S126 | as S126 | as S126 | scored 0.952 |
| S129 | F06 | strategy pool, 1,450 | as S126 | as S126 | as S126 | scored 0.943 |
| S130 | F18 | strategy pool, 1,450 | as S126 | as S126 | as S126 | scored 0.967 |
| S131 | F19 | strategy pool, 1,450 | as S126 | as S126 | as S126 | scored 0.963 |
| S132 | F15 | LongMemEval (cleaned `_s`), 500 | official judge prompts, Claude Haiku 5.5 judge, Haiku check first | whole history in the prompt, 163,840-token window, 3g.40gb slice | `lme/runs/fast/lme_00_mig`, `lme_01..19` | answers done, judge next |
| S133 | F16 | LongMemEval, 500 | as S132 | as S132 | `lme/runs/tools/*` | answers done, judge next |
| S134 | F17 | LongMemEval, 500 | as S132 | as S132 | `lme/runs/deep/*` | answers done, judge next |
| S135 | F06 | LongMemEval, 500 | as S132 | as S132 | `lme/runs/deep_tools/*` | answers done, judge next |
| S136 | F18 | LongMemEval, 500 | as S132 | as S132 | `lme/runs/vote/*` | answers done, judge next |
| S137 | F19 | LongMemEval, 500 | as S132 | as S132 | `lme/runs/vote_tools/*` | answers done, judge next |
| S138 | F20 | LongMemEval, 500 | as S132 | G35 graph per history, written by Qwen W4A16 (local), one chunk per session (up to 4,096 tokens), 50 facts; `lme/graft_cache` from `lme/runs/prepare/lmem_*` | `lme/runs/memory/lmem_*` | running |
| S139 | F21 | LongMemEval, 500 | as S132 | as S138 | `lme/runs/memory_deep/lmem_*` | running |
| S140 | F22 | LongMemEval, 500 | as S132 | as S138 | `lme/runs/vote_memory/lmem_*` | running |
| S141 | F23 | LongMemEval, 500 | as S132 | as S138 | `lme/runs/deep_tools_memory/lmem_*` | answers done, judge next |
| S142 | F24 | strategy pool dev, 217 | accuracy of the picked route's label | dry run (48 questions, 6 steps) | `runs/strategy-router/dryrun-20261121`, `dryrun-20261121b` | free check only |
| S143 | F25 | as S142 | as S142 | as S142 | as S142 | free check only |
| S144 | F26 | as S142 | as S142 | as S142 | as S142 | free check only |
| S145 | F27 | as S142 | as S142 | as S142 | as S142 | free check only |
| S146 | F28 | strategy pool, 20 train questions | label grader | fake Qwen | Fir job `rl-check` (`rl_check.sbatch`, output folder inferred) | free check only |

| S147 | F29 | strategy pool + LongMemEval dev, 293 | accuracy of the picked route's label | trained on run-04-lme train (1,365), tuned on dev | `runs/strategy-router/run04lme-full` | scored 0.904 |
| S148 | F30 | as S147 | as S147 | as S147 | as S147 | scored 0.959 |
| S149 | F31 | as S147 | as S147 | as S147 | as S147 | scored 0.963 |
| S150 | F32 | as S147 | as S147 | as S147 | as S147 | scored 0.952 |
| S151-S154 | F29-F32 | as S147 | as S147 | trained on a nested 50% of train (3 draws) | `run04lme-frac0.5-s20261121..23` | scored (learning curve) |
| S155-S158 | F29-F32 | as S147 | as S147 | trained on a nested 75% of train (3 draws) | `run04lme-frac0.75-s20261121..23` | scored (learning curve) |
| S159 | F15 | LongMemEval dev, 76 (router split) | official judge prompts, Claude Haiku 5.5, Haiku check first | as S132; 3 repeats, same day as S160-S162 | `lme_llmv/runs/fast/lme_dev_r0..2` | running (test 06) |
| S160 | F33 | as S159 | as S159 | as S159; checker Qwen, thinking off, 1,024 tokens | `lme_llmv/runs/fast_llmv/lme_dev_r0..2` | running (test 06) |
| S161 | F17 | as S159 | as S159 | as S159 | `lme_llmv/runs/deep/lme_dev_r0..2` | running (test 06) |
| S162 | F34 | as S159 | as S159 | as S160 | `lme_llmv/runs/deep_llmv/lme_dev_r0..2` | running (test 06) |
The final-benchmark setups of F01 (plain Qwen), the full system and the best single route get S IDs when they are
configured.

## 4. Runs

A run is one run folder or shard set (`runs/<name>/`, `lme/runs/<route>/<shard>`, a test's `runs/run-NN/`). Its setup
is the row above that names it. After approval each test's table gains a setup column.

## 5. Pre-fix runs (marked under each test's Revisions, 2026-11-21)

| Runs | Setups | Bug (fixed, no config switch) | Mark |
|---|---|---|---|
| test 03 run-01 (`router-labels-v1-broken-*`) | S121, S122 | one call with tools offered but no tool loop (Phi 0 of 4,856 answered); code graded without stripping fences | invalid; already superseded by run-02 |
| test 04 run-02 labels on the 263 affected questions | S126-S131 | verifier accepted only options A-D (MMLU-Pro goes to J); instruction checker misread rules; float and math-format grading | invalid for those 263 questions; run-03 replaced them |
| test 02 run-01 small-test scores | S115-S117 | the same grader and verifier bugs, plus code fences for gpt-oss | scored before the grader fixes, audited (user) |
| test 03 run-02 router-B labels and router B | S119, S120, S124, S125 | as above (gpt-oss lost 227 answers to bugs) | scored before the grader fixes, audited (user) |

## 6. Conventions and open item

- Next free IDs: F36, S168 (S shared with GRAFT; S163-S167 are GRAFT's LongMemEval retrieval comparison).
- F06 checked against the saved runs (2026-11-22): test 02's small test (`qwen_w4a16_alone`, Fir and Nibi), test 03's labels
  (Trillium `labels-qwen_w4a16_alone`) and the Deep+Tools route (`strategy-labels/deep_tools`) served the same build
  (`quant/qwen3.8-27b-w4a16`) with the same vLLM settings (qwen3_coder tool parser, qwen3 reasoning parser, seed 20261119,
  131,072 context) and native tools. Temperature is the same too: one sample always runs at 0.0 (`flotilla/system.py`, since
  09d3c93 of 2026-11-19, before test 02); Deep+Tools' `temperature: 0.6` applies only to several samples, and `qwen_w4a16_alone`
  leaves it at the default, also 0.6, also unused. Test 02's RULER and vision groups ran without the tool parser, but those
  groups offer no tools in either configuration. Only the protocol label differs (v9 vs v10). F06 stays one candidate.
- Phi and Qwen FP8 "in the loop" (F05, F10): confirmed never run on Fir and Nibi; Trillium not checked.
- Outside bare runs (S104, S105, S108-S114, S121, S122) have setups but no candidate ID.
- Test 02 run-01 and test 03 run-02 are marked "scored before the grader fixes, audited" (user, 2026-11-21).
