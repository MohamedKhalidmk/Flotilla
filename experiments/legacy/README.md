# Legacy results

Results that never became a numbered test, or no longer back any decision. Kept as records; nothing current rests on
them. Candidate IDs are in the [registry](../../docs/reference/REGISTRY.md).

## Router A (F12, setup S123): [router_a_pool500.json](router_a_pool500.json)

Router A was the off-the-shelf router of protocol-v4: the vLLM Semantic Router's decision model `vllm-sr/vela3-fast`
classified each task's type, and a fixed decision table mapped the type to solver models and tools
(`flotilla/router_a.py`, protocol section 4.5). On 500 clean router-pool items with known task types it scored
**0.744** routing accuracy (math 260/276, science 73/98, instruction 28/90, code 11/36), at 0.047 s per item.

Superseded by router B (test 03), then by the strategy routers (test 04).
