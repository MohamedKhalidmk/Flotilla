# Experiments

Each test has a README (Question, Setup, Result, Decision, Revisions), `config.yaml`, `runs/run-NN/` with a
`run.json`, `table.csv` built by `make_table.py` from the runs only, and `figure.png` drawn from that table by
[`docs/design/charts.py`](../docs/design/charts.py). Old runs are never edited: a fix or rerun is a new run-NN and a
Revisions line. New tests start from [`_template/`](_template/).

| Test | Question | Status | Current run | Decision |
|---|---|---|---|---|
| [01 · Quantization](test-01-quantization/README.md) | Does 4-bit lose accuracy? | done | run-01 | Qwen runs 4-bit (W4A16) |
| [02 · Model small test](test-02-model-small-test/README.md) | Which solver models earn a place? | done | run-01 | Command A+ dropped |
| [03 · Router B](test-03-router-b-models/README.md) | Does routing between Qwen and gpt-oss help? | done | run-02 | gpt-oss dropped, Qwen alone |
| [04 · Strategy router](test-04-strategy-router/README.md) | Does picking a route per question beat the best fixed route? | running (labels done) | run-03 | pending |
| [05 · GRAFT base graph](test-05-graft-base-graph/README.md) | Does a base knowledge graph help the Memory route? | done | run-02 | No base graph: RoG and full T-REx both not adopted (T-REx 0.17-0.19 vs 0.347) |
