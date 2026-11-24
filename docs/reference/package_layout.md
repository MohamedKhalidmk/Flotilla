# Package layout

The flotilla/ package was split into six subpackages on 2026-11-24 (branch reorganize-package). Each module moved
unchanged apart from its imports; nothing was renamed.

| Subpackage | What it holds |
|---|---|
| `flotilla/core/` | The Flotilla loop: orchestration, tools, verifier rules, traces, scoring, serving and quantization. |
| `flotilla/routers/` | Strategy routers: route labels, the supervised routers and the live RL router (test 04). |
| `flotilla/memory/` | Memory routes: GRAFT facts from a question's own history, LongMemEval items, and the GRAFT bridge. |
| `flotilla/data/` | Datasets, small-test and test splits, leakage checks and benchmark item exports. |
| `flotilla/research/` | Audits and analyses of finished runs: failure causes, oracles, result tables, replays and gates. |
| `flotilla/legacy/` | Router A and router B (tests 02 and 03), kept so their runs can be reproduced; nothing new imports them. |

Dependencies run one way where possible: core is used by everything, routers and memory use core, research reads
the others. Two old links remain and are deliberate: `core/smalltest.py` can still call router A for the old
small-test configs, `data/splits.py` reuses `legacy/router_data.py`'s LiveCodeBench private-test decoder, and
`routers/strategy_items.py` reads router B's held-out split so test 04 never trains on router B's test items.

## Old path to new path

| Old file | New file | Module name |
|---|---|---|
| `flotilla/ifeval_rules.py` | `flotilla/core/ifeval_rules.py` | `flotilla.ifeval_rules` to `flotilla.core.ifeval_rules` |
| `flotilla/quantize.py` | `flotilla/core/quantize.py` | `flotilla.quantize` to `flotilla.core.quantize` |
| `flotilla/scoring.py` | `flotilla/core/scoring.py` | `flotilla.scoring` to `flotilla.core.scoring` |
| `flotilla/serve.py` | `flotilla/core/serve.py` | `flotilla.serve` to `flotilla.core.serve` |
| `flotilla/smalltest.py` | `flotilla/core/smalltest.py` | `flotilla.smalltest` to `flotilla.core.smalltest` |
| `flotilla/system.py` | `flotilla/core/system.py` | `flotilla.system` to `flotilla.core.system` |
| `flotilla/tools.py` | `flotilla/core/tools.py` | `flotilla.tools` to `flotilla.core.tools` |
| `flotilla/trace.py` | `flotilla/core/trace.py` | `flotilla.trace` to `flotilla.core.trace` |
| `flotilla/vendor/` | `flotilla/core/vendor/` |  |
| `flotilla/label_loop.py` | `flotilla/routers/label_loop.py` | `flotilla.label_loop` to `flotilla.routers.label_loop` |
| `flotilla/rl_router.py` | `flotilla/routers/rl_router.py` | `flotilla.rl_router` to `flotilla.routers.rl_router` |
| `flotilla/strategy_items.py` | `flotilla/routers/strategy_items.py` | `flotilla.strategy_items` to `flotilla.routers.strategy_items` |
| `flotilla/strategy_labels.py` | `flotilla/routers/strategy_labels.py` | `flotilla.strategy_labels` to `flotilla.routers.strategy_labels` |
| `flotilla/strategy_router.py` | `flotilla/routers/strategy_router.py` | `flotilla.strategy_router` to `flotilla.routers.strategy_router` |
| `flotilla/graft_bridge.py` | `flotilla/memory/graft_bridge.py` | `flotilla.graft_bridge` to `flotilla.memory.graft_bridge` |
| `flotilla/longmemeval.py` | `flotilla/memory/longmemeval.py` | `flotilla.longmemeval` to `flotilla.memory.longmemeval` |
| `flotilla/memory_route.py` | `flotilla/memory/memory_route.py` | `flotilla.memory_route` to `flotilla.memory.memory_route` |
| `flotilla/supersede_check.py` | `flotilla/memory/supersede_check.py` | `flotilla.supersede_check` to `flotilla.memory.supersede_check` |
| `flotilla/calib_pool.py` | `flotilla/data/calib_pool.py` | `flotilla.calib_pool` to `flotilla.data.calib_pool` |
| `flotilla/data.py` | `flotilla/data/data.py` | `flotilla.data` to `flotilla.data.data` |
| `flotilla/export_ruler.py` | `flotilla/data/export_ruler.py` | `flotilla.export_ruler` to `flotilla.data.export_ruler` |
| `flotilla/full_items.py` | `flotilla/data/full_items.py` | `flotilla.full_items` to `flotilla.data.full_items` |
| `flotilla/leakage.py` | `flotilla/data/leakage.py` | `flotilla.leakage` to `flotilla.data.leakage` |
| `flotilla/splits.py` | `flotilla/data/splits.py` | `flotilla.splits` to `flotilla.data.splits` |
| `flotilla/error_subtypes.py` | `flotilla/research/error_subtypes.py` | `flotilla.error_subtypes` to `flotilla.research.error_subtypes` |
| `flotilla/eval_math500.py` | `flotilla/research/eval_math500.py` | `flotilla.eval_math500` to `flotilla.research.eval_math500` |
| `flotilla/failure_audit.py` | `flotilla/research/failure_audit.py` | `flotilla.failure_audit` to `flotilla.research.failure_audit` |
| `flotilla/model_audit.py` | `flotilla/research/model_audit.py` | `flotilla.model_audit` to `flotilla.research.model_audit` |
| `flotilla/oracle.py` | `flotilla/research/oracle.py` | `flotilla.oracle` to `flotilla.research.oracle` |
| `flotilla/results_table.py` | `flotilla/research/results_table.py` | `flotilla.results_table` to `flotilla.research.results_table` |
| `flotilla/toy_gate.py` | `flotilla/research/toy_gate.py` | `flotilla.toy_gate` to `flotilla.research.toy_gate` |
| `flotilla/usc_replay.py` | `flotilla/research/usc_replay.py` | `flotilla.usc_replay` to `flotilla.research.usc_replay` |
| `flotilla/eval_router.py` | `flotilla/legacy/eval_router.py` | `flotilla.eval_router` to `flotilla.legacy.eval_router` |
| `flotilla/router_a.py` | `flotilla/legacy/router_a.py` | `flotilla.router_a` to `flotilla.legacy.router_a` |
| `flotilla/router_b.py` | `flotilla/legacy/router_b.py` | `flotilla.router_b` to `flotilla.legacy.router_b` |
| `flotilla/router_b_lite.py` | `flotilla/legacy/router_b_lite.py` | `flotilla.router_b_lite` to `flotilla.legacy.router_b_lite` |
| `flotilla/router_data.py` | `flotilla/legacy/router_data.py` | `flotilla.router_data` to `flotilla.legacy.router_data` |
| `flotilla/router_labels.py` | `flotilla/legacy/router_labels.py` | `flotilla.router_labels` to `flotilla.legacy.router_labels` |

## What was not rewritten

Records of what was actually run keep the old module names, because they describe commands as they were typed:
docs/reference/run_log.md, docs/session/PROJECT_HISTORY.md, every file under experiments/*/runs/, reports/ and
results/. Read an old name there with the table above. Everything else (code, tests, scripts, configs, prompts, docs
and the experiment READMEs) uses the new names.
