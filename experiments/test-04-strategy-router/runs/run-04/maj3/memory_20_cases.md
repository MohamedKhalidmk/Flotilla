# What Qwen did with the facts: 20 Memory-route misses with evidence shown (2026-11-22)

Route Memory (F20: Fast + GRAFT G35, run-04, the old writer). The 20 are drawn (seed 20261122, spread over question
types) from the 206 non-abstention questions the route got wrong although a fact from an answer session was among the
50 facts shown. For each, the needed fact was searched in the whole graph (`scratchpad/mem20_search.py`, by the gold's
key words) and in the 50 facts shown.

| Question (type) | Gold | Qwen answered | Needed fact | What happened |
|---|---|---|---|---|
| lme-852ce960 Wells Fargo pre-approval amount (knowledge-update) | $400,000 | memory has no pre-approval amount | not in the graph | writer missed it |
| lme-dd2973ad bedtime before the doctor's appointment (multi-session) | 2 AM | memory does not hold it | not in the graph (the appointment facts were shown) | writer missed it |
| lme-c4f10528 Nasi Goreng restaurant in Cihampelas Walk (single-session-assistant) | Miss Bee Providore | no such restaurant in memory | in the graph ("Miss Bee Providore serves ...", "Miss Bee's Nasi Goreng ..."), not shown; burger facts ranked 1-6 | retrieval ranked it out |
| lme-8a2466db video editing resources (preference) | tailored to Premiere Pro | "Adobe Premiere Pro" | shown (#1, #5) and used | the answer rule ("a single phrase") turned a recommendation into a name |
| lme-118b2229 daily commute (single-session-user) | 45 minutes each way | memory has no commute time | not in the graph | writer missed it |
| lme-370a8ff4 weeks from flu recovery to 10th jog (temporal) | 15 | 11 weeks | both shown (#1, #2), dated by their sessions (Jan 19, Apr 10) | reasoned with session dates; the facts carry no event dates |
| lme-9ea5eabc most recent family trip (knowledge-update) | Paris | Hawaii | both shown: "visited Hawaii" (May 26, #5), "travelled to Paris" (May 28, #15); no SUPERSEDES link | used the older fact |
| lme-e25c3b8d savings on the TK Maxx handbag (multi-session) | $300 | memory does not hold it | "price paid $200" in the graph, not shown; the original price not in the graph | retrieval ranked it out, and the writer missed half |
| lme-18dcd5a5 number of mummies (single-session-assistant) | 4 | memory does not say | only "the temple is filled with mummies" and the stat block, shown | writer dropped the count |
| lme-0a34ad58 getting around Tokyo (preference) | use the Suica card and TripIt | a hotel tour desk | Suica, TripIt not in the graph | writer missed them; the one-phrase rule as well |
| lme-60d45044 favourite rice (single-session-user) | Japanese short-grain | memory does not hold it | not in the graph | writer missed it |
| lme-gpt4_e414231e days from mountain-bike fix to pedal upgrade (temporal) | 4 | 0 days | "upgraded pedals to Shimano Ultegra" (Mar 19) in the graph, not shown; Qwen used "considers upgrading road bike" (Mar 15) | retrieval ranked it out; Qwen took the nearest shown fact |
| lme-affe2881 bird species seen in the park (knowledge-update) | 32 | memory does not hold it | not in the graph | writer missed it |
| lme-gpt4_ab202e7f kitchen items replaced or fixed (multi-session) | 5 | 4 | 4 of the 5 shown; "coffee maker" not in the graph | writer missed one item |
| lme-41275add the Mayo Clinic video (single-session-assistant) | title and link | the title | title shown (#25); the link not in the graph | writer dropped the link |
| lme-fca70973 theme park suggestions (preference) | build on their thrill-ride and event history | "Six Flags Magic Mountain" | shown (#8, #15, #20-23) | the one-phrase rule |
| lme-58ef2f1c date of the shelter's fundraising dinner (single-session-user) | February 14th | February | "Love is in the Air occurred on Valentine's Day" in the graph, not shown | retrieval ranked it out |
| lme-gpt4_5438fa52 cultural festival or Spanish classes first (temporal) | Spanish classes | memory does not hold it | "attended Sundance in January" in the graph, not shown; no start date for the classes | retrieval ranked it out, and the writer missed the start date |
| lme-72e3ee87 Crash Course Science episodes completed (knowledge-update) | 50 | 10 | only "currently watching episode 10" (shown, #41); the update to 50 not in the graph | writer missed the update (the case the G41 supersede check uses) |
| lme-91b15a6e minimum from selling the necklace and vanity (multi-session) | $5,150 | memory has nothing on the necklace | "necklace appraised value $5,000" in the graph, not shown; the vanity facts shown (#1-4) | retrieval ranked it out |

## Counts

| What happened | Cases |
|---|---|
| The needed fact was never written into the graph (writer) | 10 (7 fully, 3 in part: a count, a link, one of five items) |
| Written, but not among the 50 facts shown (retrieval rank) | 7 (2 of them also missing a second fact) |
| The facts were shown and the answer rule cut the answer to one phrase (preference questions) | 2 (a third, Tokyo, also lacked the facts) |
| Used an outdated fact (newer one shown, no SUPERSEDES link) | 1 |
| Reasoned wrong with the facts in hand (session dates taken as event dates) | 1 |
| Ignored a needed fact that was shown | 0 |

Each case is counted once, by its main cause (writer before retrieval before the rest).

## What this says

- "Evidence shown" (row 33's measure) is session-level: some fact from an answer session was shown, often not the one
  the question needs. By the needed fact, retrieval misses are much more common than the 77 retrieval_miss tags.
- Qwen rarely ignores a shown fact. The losses are upstream: the old writer leaves out about half the needed facts in
  these 20, and the ranking leaves out the rest.
- The Memory rule ("answer as concisely as you can, using a single phrase") hurts preference questions, which want a
  tailored recommendation.
- Facts carry their session date, not the event's date, which breaks temporal arithmetic.
- These graphs come from the old writer; the G41 rebuild (writer v2, bare-list fix) will show how many writer misses
  remain.
