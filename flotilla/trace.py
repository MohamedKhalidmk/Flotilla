"""One JSON line per question per run (PROTOCOL.md section 7). Every component appends to a Trace;
the run writes it when the question is finished."""
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Rules and order: PROTOCOL.md section 7 and flotilla/scoring.error_stage. token_cap (proposed 2026-11-22) splits
# "no final answer because a call hit the token cap" from format_parse_failure (ended without the JSON block).
ERROR_STAGES = ("none", "router_wrong_model", "retrieval_miss", "reasoning_error", "vote_wrong",
                "verifier_false_accept", "verifier_false_reject", "format_parse_failure", "token_cap", "timeout_or_oom")


@dataclass
class Sample:
    text: str
    final_answer: str | None
    confidence: float | None
    tokens_in: int
    tokens_out: int
    latency_s: float


@dataclass
class Trace:
    run_id: str
    protocol_version: str
    prompt_versions: dict[str, str]
    benchmark: str
    item_id: str
    split: str                                   # "dev" (small test) or "test"
    router: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    call_log: list[dict[str, Any]] = field(default_factory=list)  # per model call: round, finish reason, sizes
    models: list[dict[str, Any]] = field(default_factory=list)   # {name, quant, samples: [Sample]}
    retrieval: dict[str, Any] = field(default_factory=dict)
    vote: dict[str, Any] = field(default_factory=dict)
    cross_check: dict[str, Any] = field(default_factory=dict)
    verifier: dict[str, Any] = field(default_factory=dict)
    final_answer: str | None = None
    gold: Any = None
    correct: bool | None = None
    error_stage: str | None = None
    t0: float = field(default_factory=time.time)
    wall_seconds: float = 0.0

    def add_samples(self, name: str, quant: str, samples: list[Sample]) -> None:
        self.models.append({"name": name, "quant": quant, "samples": [asdict(s) for s in samples]})

    def tokens_total(self) -> int:
        n = sum(s["tokens_in"] + s["tokens_out"] for m in self.models for s in m["samples"])
        n += self.cross_check.get("tokens", 0) + self.verifier.get("tokens", 0) + self.router.get("tokens", 0)
        return n

    def finish(self) -> dict[str, Any]:
        self.wall_seconds = round(time.time() - self.t0, 3)
        d = asdict(self)
        d.pop("t0")
        d["tokens_total"] = self.tokens_total()
        return d


class TraceWriter:
    def __init__(self, run_dir: Path):
        run_dir.mkdir(parents=True, exist_ok=True)
        self.path = run_dir / "trace.jsonl"
        self.f = open(self.path, "a")

    def write(self, trace: Trace) -> None:
        self.f.write(json.dumps(trace.finish(), ensure_ascii=False) + "\n")
        self.f.flush()

    def close(self) -> None:
        self.f.close()
