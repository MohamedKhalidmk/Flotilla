# Experiments

Each test has a README (Question, Setup, Result, Decision, Revisions), `config.yaml`, `runs/run-NN/` with a
`run.json`, `table.csv` built by `make_table.py` from the runs only, and `figure.png` drawn from that table by
[`docs/design/charts.py`](../docs/design/charts.py). Old runs are never edited: a fix or rerun is a new run-NN and a
Revisions line. New tests start from [`_template/`](_template).

Candidate IDs (F01...) and setups (S102...) are in the [registry](../docs/reference/REGISTRY.md).

| Test | Question | Status | Current run | Decision |
|---|---|---|---|---|
| [01 · Quantization](test-01-quantization/README.md) | Does 4-bit lose accuracy? | done | run-01 | F01 (Qwen W4A16, ours) is the served build |
| [02 · Model small test](test-02-model-small-test/README.md) | Which solver models earn a place? | done | run-01 | F08 (Command A+) dropped; F06 (Qwen alone) kept |
| [03 · Router B](test-03-router-b-models/README.md) | Does routing between Qwen and gpt-oss help? | done | run-02 | F07 (gpt-oss) dropped; F13 (router B) +0.4, under the bar; F06 alone |
| [04 · Strategy router](test-04-strategy-router/README.md) | Does picking a route per question beat the best fixed route? | running (pool labels done; LongMemEval labels in progress) | run-03 | pending |
| [05 · GRAFT base graph](test-05-graft-base-graph/README.md) | Does a base knowledge graph help the Memory route? | done | run-02 | No base graph: G25 (RoG) and G27-G29 (full T-REx) not adopted (T-REx 0.17-0.19 vs 0.347); Memory routes use G35 |
| [06 · LLM verifier](test-06-llm-verifier/README.md) | Does verifier v2's LLM check help free-text answers? | running | run-01 | pending |
