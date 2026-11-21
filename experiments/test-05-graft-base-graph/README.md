# Test 05 · GRAFT base graph

| Test | Date | Protocol | Status | Current run |
|---|---|---|---|---|
| 05 | 2026-11-21 | GRAFT mode C | done | [run-02](runs/run-02/run.json) |

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
| T-REx full (Wikidata) | [1,215,416](table.csv) | [0.558](table.csv) exact, 0.628 Haiku-linked | 0.177 EiG, 0.190 GOAt, 0.170 question layer (3 repeats; [GRAFT test 04](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/README.md)) |

The RoG base mostly added hub noise to PPR: gold in the final facts fell to [0.41](table.csv). The full T-REx base did
worse: T-REx sentences took about two thirds of the 50 fact slots, pushed out the documents' edited facts (7 of 10
checked failures) and sometimes contradicted the gold (2 of 10). Gold in the final facts was 0.28 to 0.34, against 0.51
without a base. Mode C without a base scores 0.347 over 3 repeats on 2026-11-20/21. The 0.38 above is one run from
2026-11-13, and the same prompts now score about 0.34 on Haiku (drift on the API side; GRAFT
[baseline check](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/baseline_check.md)).
The T-REx rows are not in table.csv yet (those runs live in the GRAFT repo).
[table.csv](table.csv) · [figure.png](figure.png)

## Decision

No base graph. RoG and full T-REx are both not adopted. The Memory route's GRAFT builds its graph from each item's own
history (empty start, mode C), on Qwen. GRAFT test 06 tests T-REx in roles where none of its facts become memories
(a structure guide, a walk-only bridge, labelled background).

## Revisions

- 2026-11-21: full T-REx answer passes done (not adopted); Memory routes use no base graph.
- 2026-11-20: run-01, baselines and base-graph overlap.
- 2026-11-20: run-02, RoG Haiku-linking result and the full T-REx base build report.
