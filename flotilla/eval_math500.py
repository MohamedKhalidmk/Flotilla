"""MATH-500 with vLLM offline (protocol 1.3 and rule 4.1): 0-shot, chat template, greedy, math-verify scoring.

    python -m flotilla.eval_math500 --model <path or id> --name qwen-w4a16 --max-tokens 131072 --tp 1
Writes runs/<name>/trace.jsonl (one line per question) and runs/<name>/summary.json.
"""
import argparse
import json
import os
import time
from pathlib import Path

from flotilla.data import load as load_dataset
from math_verify import parse, verify
from vllm import LLM, SamplingParams

PROMPT = "Solve the following math problem. Put your final answer within \\boxed{{}}.\n\n{problem}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--max-tokens", type=int, default=131072)
    ap.add_argument("--max-model-len", type=int, default=0, help="0 = prompt room + max-tokens")
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--tokenizer", default=None, help="defaults to the base model of our own quantized checkpoints")
    ap.add_argument("--limit", type=int, default=0, help="first N items only (smoke tests)")
    ap.add_argument("--out", default=os.environ.get("FLOTILLA_RUNS", "runs"))
    a = ap.parse_args()

    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    if a.limit:
        ds = ds.select(range(a.limit))
    max_len = a.max_model_len or (a.max_tokens + 2048)
    tok = a.tokenizer
    meta = Path(a.model) / "flotilla_quant.json"
    if tok is None and meta.exists():  # our llm-compressor outputs: tokenizer from the original model
        tok = json.loads(meta.read_text())["model"]
    llm = LLM(model=a.model, tokenizer=tok, tensor_parallel_size=a.tp, max_model_len=max_len, seed=20261119)
    sp = SamplingParams(temperature=0.0, max_tokens=min(a.max_tokens, max_len - 2048))
    msgs = [[{"role": "user", "content": PROMPT.format(problem=ex["problem"])}] for ex in ds]

    t0 = time.time()
    outs = llm.chat(msgs, sp)
    wall = time.time() - t0

    out_dir = Path(a.out) / a.name
    out_dir.mkdir(parents=True, exist_ok=True)
    correct = tok_in = tok_out = truncated = 0
    with open(out_dir / "trace.jsonl", "w") as f:
        for ex, o in zip(ds, outs):
            text = o.outputs[0].text
            gold = parse("\\boxed{" + ex["answer"] + "}")
            pred = parse(text)
            ok = bool(gold) and bool(pred) and verify(gold, pred)
            n_in, n_out = len(o.prompt_token_ids), len(o.outputs[0].token_ids)
            cut = o.outputs[0].finish_reason == "length"
            correct += ok; tok_in += n_in; tok_out += n_out; truncated += cut
            f.write(json.dumps({"benchmark": "math500", "item_id": ex["unique_id"], "model": a.model, "final_answer": str(pred[-1]) if pred else None,
                                "gold": ex["answer"], "correct": ok, "truncated": cut, "tokens_in": n_in, "tokens_out": n_out}) + "\n")
    n = len(ds)
    summary = {"name": a.name, "model": a.model, "n": n, "accuracy": round(correct / n, 4), "correct": correct, "truncated": truncated,
               "tokens_in": tok_in, "tokens_out": tok_out, "wall_seconds": round(wall, 1), "tp": a.tp, "max_tokens": sp.max_tokens,
               "gen_tokens_per_s": round(tok_out / wall, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
