"""Router B labels: run one solver model over the training pool and grade every answer.

    python -m flotilla.router_labels --pool $SCRATCH/flotilla/router/pool.jsonl --model Qwen/Qwen3.8-27B \
        --name qwen --max-tokens 16384 --max-model-len 20480
Writes $FLOTILLA_RUNS/router-labels-<name>/labels.jsonl: {id, source, task_type, model, correct, tokens_out, truncated}.
Graders: math -> math-verify; science_mc -> option letter; code -> sandboxed tests; instruction -> our constraint checker.
"""
import argparse
import json
import os
import time
from pathlib import Path

from vllm import LLM, SamplingParams

from flotilla import tools
from flotilla.system import parse_final, solver_messages


def grade(item: dict, answer: str | None) -> bool:
    if answer is None:
        return False
    t = item["task_type"]
    if t == "math":
        return tools.sympy_check(answer, item["gold"])["ok"]
    if t == "science_mc":
        return answer.strip().upper()[:1] == str(item["gold"]).strip().upper()[:1]
    if t == "code":
        return tools.run_public_tests(answer, item["tests"], timeout_s=6)["ok"]
    if t == "instruction":
        return tools.constraint_check(item["task"], answer)["ok"]
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--max-model-len", type=int, default=20480)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    items = [json.loads(l) for l in open(a.pool)]
    if a.limit:
        items = items[: a.limit]
    llm = LLM(model=a.model, max_model_len=a.max_model_len, seed=20261119)
    sp = SamplingParams(temperature=0.0, max_tokens=a.max_tokens)
    msgs = [solver_messages(it["task"], it["task_type"], "v1") for it in items]
    t0 = time.time()
    outs = llm.chat(msgs, sp)
    wall = time.time() - t0
    out_dir = Path(os.environ.get("FLOTILLA_RUNS", "runs")) / f"router-labels-{a.name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    n_ok, n_tok = 0, 0
    with open(out_dir / "labels.jsonl", "w") as f:
        for it, o in zip(items, outs):
            text = o.outputs[0].text
            ans, conf = parse_final(text)
            ok = grade(it, ans)
            n_ok += ok
            n_tok += len(o.outputs[0].token_ids)
            f.write(json.dumps({"id": it["id"], "source": it["source"], "task_type": it["task_type"], "model": a.name,
                                "answer": (ans or "")[:2000], "confidence": conf, "correct": ok,
                                "tokens_out": len(o.outputs[0].token_ids), "truncated": o.outputs[0].finish_reason == "length"}) + "\n")
    summary = {"name": a.name, "model": a.model, "n": len(items), "correct": n_ok, "tokens_out": n_tok, "wall_seconds": round(wall, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
