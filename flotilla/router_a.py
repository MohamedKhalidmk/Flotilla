# Sources: semantic-router, vela3 (docs/reference/REFERENCES.md)
"""Router A: the vLLM Semantic Router's decision model (vllm-sr/vela3-fast, Apache-2.0) classifies each task's
type; a fixed decision table maps task type to solver models and Python tools (protocol 4.5).

Why the decision model and not the whole vllm-sr product: the product runs as Docker services (router, Envoy,
dashboard) and downloads its assets at start; on the clusters there is no Docker and compute nodes are offline.
vela3-fast is the model the product uses for its decisions, so routing quality is the same component.

Deterministic rules come first: an image -> vision path; a very long input -> long_context.
"""
import sys
import time
from dataclasses import dataclass, field

TASK_TYPES = {
    "math": "A math problem to solve: arithmetic, algebra, geometry, counting, number theory or competition math, with a numeric or symbolic answer.",
    "code": "Write a program or function that solves a programming task, usually reading input and printing output.",
    "science_mc": "A multiple-choice question in science or engineering with lettered options; answer with one letter.",
    "instruction": "Write text (an essay, letter, story, list, answer) that must follow explicit formatting or style constraints.",
    "legal": "A question about law, statutes, cases or legal procedure.",
    "general": "Any other question or request.",
}
# decision table: task type -> models (in order) and tools; refined from small-test results (protocol 4.5)
DEFAULT_TABLE = {
    "math": {"models": ["qwen", "phi"], "tools": ["sympy"]},
    "code": {"models": ["qwen"], "tools": ["python_exec"]},
    "science_mc": {"models": ["qwen", "phi"], "tools": []},
    "instruction": {"models": ["qwen"], "tools": ["constraint_check"]},
    "legal": {"models": ["qwen"], "tools": []},
    "general": {"models": ["qwen"], "tools": []},
    "vision": {"models": ["vision"], "tools": []},
    "long_context": {"models": ["qwen"], "tools": []},
}
LONG_CONTEXT_CHARS = 60_000   # about 15K tokens


@dataclass
class RouterA:
    model_path: str
    table: dict = field(default_factory=lambda: dict(DEFAULT_TABLE))
    device: str | None = None

    def __post_init__(self):
        sys.path.insert(0, self.model_path)
        from vela3_encoder import DecisionEncoder  # shipped with the model repo
        self.enc = DecisionEncoder.load(self.model_path, device=self.device)

    def route(self, task: str, has_image: bool = False) -> dict:
        t0 = time.time()
        if has_image:
            ttype, probs, how = "vision", {}, "rule: image attached"
        elif len(task) > LONG_CONTEXT_CHARS:
            ttype, probs, how = "long_context", {}, "rule: input longer than 60K characters"
        else:
            q = {"task_type": {"type": "choice", "instructions": "What kind of task is this?", "criteria": TASK_TYPES}}
            # DecisionEncoder.predict returns (answers, n_tokens); answers[name] = {type, choice, probabilities}
            res = self.enc.predict(task[:20_000], q)
            ans = (res[0] if isinstance(res, (list, tuple)) else res)["task_type"]
            ttype = ans.get("choice") or max(ans.get("probabilities", {"general": 1}).items(), key=lambda kv: kv[1])[0]
            probs = {k: round(float(v), 4) for k, v in (ans.get("probabilities") or {}).items()}
            how = "vela3-fast choice"
        row = self.table.get(ttype, self.table["general"])
        return {"router": "A:vela3-fast", "task_type": ttype, "probabilities": probs, "how": how,
                "models": row["models"], "tools": row["tools"], "latency_s": round(time.time() - t0, 4)}
