# Flotilla

A compound AI system of small, quantized open models served with vLLM, measured against Canada Quant Labs' published numbers on their own benchmarks and settings, with every component's effect and every unit of compute reported.

- `docs/PROTOCOL.md`: what is measured and how, decision rules, leakage controls, traces, compute accounting (frozen before any scored run)
- `docs/PROMPTS.md`: prompt registry and data-flow diagram
- `prompts/`: versioned prompt for every role
- `notes/`: research notes behind the protocol (CQL settings, model candidates, benchmarks and components)
- `scripts/trillium/`: cluster setup and job scripts (Trillium GPU, def-sylu)

Status: protocol draft, not frozen.
