# Reasoning-graph route (design, 2026-11-22)

> Idea from the user, 2026-11-22. New candidate **F35** in the [registry](../reference/REGISTRY.md). Status row 9 in
> [STATUS.md](../session/STATUS.md). Design only: nothing is built yet, and this work never delays the Memory work
> (writer v2, user node, chat guide).

## Question

Deep thinks in one hidden pass. If Qwen instead answers in explicit steps and writes its work into a graph as it
goes (the question, its sub-steps, partial results and notes), does it reach Deep's accuracy, or beat it, at the
same compute or less? This is GRAFT's working memory (C v2, G33) with no documents: the graph starts empty and holds
only Qwen's own work.

## The route (F35)

Thinking off on every call, no tools, temperature 0, solver prompt v1's answer format. Per question:

1. **Plan** (1 call, at most 1,024 tokens). Qwen breaks the question into at most 6 sub-steps, each with what it
   depends on: JSON `{"steps": [{"id": "s1", "ask": "...", "uses": []}, {"id": "s2", "ask": "...", "uses": ["s1"]}]}`.
   No usable plan: one step, the whole question.
2. **Each step** (1 call per step, at most 1,024 tokens). The prompt is the question, then the work graph read back for
   this step, then the step. Read-back follows the graph: the results and notes of the steps this step `uses`, and
   of the steps those use (two hops), plus the question. Reply: `{"result": "...", "note": "at most 40 words",
   "check": "ok" | "doubt"}`. The result, note and edges go into the graph.
3. **Final** (1 call, at most 2,048 tokens). The question, the whole work graph as text (steps in order with their
   results, notes and checks), then solver prompt v1's final-answer instruction. The answer goes through verifier v2
   as on every route (exact checks for maths and letters; one retry on reject).

At most 1 + 6 + 1 calls (plus a verifier retry). The step and final caps are set now, before any run.

## The graph

GRAFT's `GraphStore` with an empty base and the work layer of [GRAFT's working-memory design](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/design/graft_working_memory_design.md):

| Node | Content |
|---|---|
| `W:q` | the question |
| `W:s1..sK` | a sub-step's ask |
| `W:r1..rK` | its result |
| `W:n1..nK` | its note (and its check flag) |
| `W:a` | the final answer |

Edges: `has_step` (q to s), `next` (step order), `uses` (s_j to s_i: a step builds on another's result), `answer`
(s to r, q to a), `note` (s to n). The graph is saved whole per question (`work_graph.jsonl`) and removed after it;
nothing carries over between questions.

Code: a new plan prompt and an empty-graph mode in GRAFT's `my_method/working_memory.py` (the question-layer parse
is for questions about stored facts; maths needs Qwen's own plan), called from Flotilla through
`flotilla/graft_bridge.py` as route `reason_graph`, with Qwen on the job's own vLLM server.

## Pilot (free, Qwen)

- **Items:** 100 pool **train** questions (dev and held-out untouched): 50 maths (25 AIME, 25 MATH; GSM8K left out,
  Deep and Fast are near the ceiling there) and 50 science multiple choice (MMLU-Pro, the pool's only GPQA-style
  source; GPQA itself is a test set). Drawn at random within each source, seed 20261122, before any run.
- **Arms, same day:** F35, Deep (F17) and Fast (F15), as configured in test 04.
- **Compute fair by design:** each job runs all three arms one after another on one vLLM server on one H100, so the
  GPU-seconds compare on the same hardware. 3 jobs = 3 repeats (Fir and Nibi twins, the later one cancelled).
- **Reported:** accuracy per arm and per type (maths, science), with the spread over repeats; GPU-seconds per question
  (median and total); calls and tokens per question; how often the plan fell back to one step; a few work graphs read
  by hand.

## Keep rule (user, set 2026-11-22, before any result)

Add F35 as a route only if it beats Deep by more than 1 point at similar compute, or matches Deep for clearly less
compute.

**Proposed definitions (for the user to confirm before any run):** "similar compute" = F35's GPU-seconds within 25%
of Deep's on the same jobs; "clearly less" = at most 75% of Deep's; "matches" = within 1 point of Deep. On 100
questions one question is 1 point, so the repeat spread is reported next to every difference.

If it passes, the next question is a prompt-only control (the same steps with no graph, as C- was for C), so the
graph's own share is known before F35 joins the router's routes.

## Cost

Free (Qwen on Fir, Nibi or Trillium). The pilot is small: 100 questions, three arms, three repeats.
