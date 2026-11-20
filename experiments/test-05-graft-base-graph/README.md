# Test 05 · GRAFT base graph

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 05 | 2026-11-20 | GRAFT mode C | running | [run-02](runs/run-02/run.json) |

## Question

Does a general knowledge graph under the documents (a base layer) help GRAFT, the Memory route's retriever?

## Setup

FactConsolidation multi-hop 262K (100 questions), GRAFT mode C (PPR, 400-node GCN subgraph, EiG or GOAt explainer,
second PPR), Haiku 5.5 answers. A base graph is built from outside data, leakage-checked against the benchmark,
and the documents are written on top. Document entities are linked to base entities by Haiku choosing among the
10 nearest base names. Code and runs: [GRAFT](https://github.com/MohamedKhalidmk/GRAFT), branch graft-linking-hybrid.
Config: [config.yaml](config.yaml).

## Result

| Base | Facts | Entity overlap | Accuracy |
|---|---|---|---|
| None (mode C) | 0 | | [0.38](table.csv) |
| RoG (Freebase) | [20,000](table.csv) | [0.133](table.csv) exact, [0.219](table.csv) Haiku-linked | [0.21](table.csv) |
| T-REx full (Wikidata) | [1,215,416](table.csv) | [0.558](table.csv) exact | running |

The RoG base mostly added hub noise to PPR: gold in the final facts fell to [0.41](table.csv).
[table.csv](table.csv) · [figure.png](figure.png)

## Decision

RoG base not adopted. The full T-REx base is the real test: 3 repeats each with EiG, GOAt and the question layer,
then the same graph with Qwen in place of Haiku for the Memory route.

## Revisions

- 2026-11-20: run-01, baselines and base-graph overlap.
- 2026-11-20: run-02, RoG Haiku-linking result and the full T-REx base build report.
