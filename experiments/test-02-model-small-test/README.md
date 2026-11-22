# Test 02 · Model small test

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 02 | 2026-11-20 | protocol-v9 | done | [run-01](runs/run-01/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| F03 | S106 (25 dev items) | Phi-4-reasoning-plus FP8 (ours), cap 30,000 |
| gpt-oss-20b (outside) | S111 | gpt-oss-20b, effort low, cap 32,768 |
| gpt-oss-20b (outside) | S112 | gpt-oss-20b, effort medium, cap 32,768 |
| gpt-oss-20b (outside) | S113 | gpt-oss-20b, effort high, cap 32,768 |

## Question

Which solver models earn a place: Qwen3.8-27B (4-bit), gpt-oss-20b, Command A+?

## Setup

The 5% small test: the same 362 dev questions for every model across 11 benchmarks, through the full Flotilla loop
(solver v1, verifier v2, native tool calls, one sample, 32,768 output tokens). gpt-oss has no image input, so its
mean covers 9 text benchmarks. Config: [config.yaml](config.yaml).

## Result

| Model | Mean over benchmarks |
|---|---|
| Qwen3.8-27B, 4-bit | [0.877](table.csv) |
| gpt-oss-20b | [0.772](table.csv) (9 text) |
| Command A+ | [0.773](table.csv) |
| Perfect router, Qwen + gpt-oss | [0.910](table.csv) |

Qwen leads on 10 of 11 benchmarks; gpt-oss leads on RULER 32K ([0.867 vs 0.697](table.csv), 33 questions).
[table.csv](table.csv) · [rule_4_2.csv](rule_4_2.csv) · [figure.png](figure.png)

## Decision

Rule 4.2: **Command A+ dropped.** Command A+ minus Qwen = [−0.104](rule_4_2.csv), 95% CI [[−0.143, −0.065]](rule_4_2.csv), on 4 GPUs
against Qwen's 1. (The table recomputes the bootstrap with seed 20261119; the original report gave −0.066 as the upper
end. Either way the whole interval is below 0.) gpt-oss went on to test 03.

## Revisions

- 2026-11-22: the 2026-11-20 report (`reports/smalltest_three_models.md`) removed; what it held beyond this README and the tables (builds, Command A+ compute) moved to [runs/run-01/report_2026-11-20.md](runs/run-01/report_2026-11-20.md). The older-models failure audit moved here from `reports/failure_audit/`: [runs/run-02/audit/older_models.md](runs/run-02/audit/older_models.md) (built by `build.py` there, with `hand_checks.json`; markdown only).
- 2026-11-21: **run-01 marked "scored before the grader fixes, audited"** (user; setups S115-S117): scored before the verifier's A-D option fix and the grader fixes (instruction checker, float tolerance, math formats, code fences for gpt-oss); run-02's failure audit rechecked every wrong answer, and the Command A+ and gpt-oss drops stand.
- 2026-11-20: run-01. phi-replacement/ holds the 25-question MATH-500 check that replaced Phi with gpt-oss (protocol-v9).
