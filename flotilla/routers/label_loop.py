"""Router labels through the real Flotilla loop (same tools, prompts, verifier and retry as the small tests).

The first labels (flotilla/legacy/router_labels.py) made one plain generation call with a prompt that offers tools but ran no
tool loop, so answers that called a tool ended without a final answer. They are kept, marked v1, and not used.

    python -m flotilla.routers.label_loop make-items --pool $SCRATCH/flotilla/router/pool.clean.jsonl \
        --out-dir $SCRATCH/flotilla/labelitems --shard-size 300
    # then serve each shard like a small-test group: python -m flotilla.core.serve ... --items-dir labelitems --benches label_03
    python -m flotilla.routers.label_loop score --pool .../pool.clean.jsonl --runs RUN_DIR [RUN_DIR ...] --model qwen \
        --out $SCRATCH/flotilla/runs/router-labels-loop-qwen

Items carry only what the model sees (task, task type); grading reads the gold answers and code tests from the pool,
so traces stay small. Every answer is kept with its score, tokens, calls and time per question.
"""
import argparse
import json
import re
from pathlib import Path

from flotilla.core import tools


_UNI = {"∞": "\\infty", "∪": "\\cup", "∩": "\\cap", "−": "-", "×": "\\times", "π": "\\pi", "≤": "\\le", "≥": "\\ge"}


def _plain(s: str) -> str:
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    for k, v in _UNI.items():
        s = s.replace(k, v)
    s = re.sub(r"√\s*\(([^)]*)\)|√\s*(\w+)", lambda m: "\\sqrt{" + (m.group(1) or m.group(2)) + "}", s)
    s = s.replace("\\$", "").replace("$", "").replace("\\%", "%").replace("{,}", "").replace("\\!", "")
    return re.sub(r"\s+", "", s).lower().rstrip(".")


def _options(task: str) -> dict:
    """Lettered options in a math question: 'A. 0.10' lines or '\\textbf{(A)}\\ expr \\qquad' runs."""
    out = {m.group(1): m.group(2).strip() for m in re.finditer(r"^\s*\(?([A-E])[.)]\s+(.+)$", task, re.M)}
    for m in re.finditer(r"\\textbf\{\(([A-E])\)\}\\?\s*(.+?)(?=\\qquad|\\textbf\{\(|\$|$)", task, re.S):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def math_format_match(task: str, answer: str, gold: str) -> bool:
    """Format misses of the math checker (2026-11-20 hand check): escaped dollars and \\text{} answers, and an option
    letter when the question asks for the letter but the gold is that option's value."""
    pa, pg = _plain(answer), _plain(gold)
    if pa and (pa == pg or tools.sympy_check(pa, pg)["ok"]):
        return True
    if re.fullmatch(r"-?\d+(?:\.\d+)?", pg.replace(",", "")):  # numeric gold, answer with a unit or words around one number
        nums = re.findall(r"-?\d[\d,]*(?:\.\d+)?", answer)
        if len(nums) == 1 and tools.sympy_check(nums[0].replace(",", ""), pg.replace(",", ""))["ok"]:
            return True
    a = answer.strip().strip("()").upper()
    opts = _options(task)
    if len(a) == 1 and a in opts:
        v = opts[a]
        return _plain(v) == _plain(gold) or tools.sympy_check(v, gold)["ok"]
    return False


def grade(item: dict, answer: str | None) -> bool:
    """The router-label graders. 2026-11-20: math format matches, float tolerance on code tests and the corrected
    instruction checker added after the hand check of test-04's failures (experiments/test-04-strategy-router)."""
    if answer is None:
        return False
    t = item["task_type"]
    if t == "math":
        return tools.sympy_check(answer, item["gold"])["ok"] or math_format_match(item["task"], answer, str(item["gold"]))
    if t == "science_mc":
        return answer.strip().upper()[:1] == str(item["gold"]).strip().upper()[:1]
    if t == "code":  # strip markdown fences as the small-test scorer does (v1 labels did not: fenced code always failed)
        from flotilla.core.scoring import strip_fence
        return tools.run_public_tests(strip_fence(answer), item["tests"], timeout_s=6)["ok"]
    if t == "instruction":
        if item.get("ground_truth"):   # RLVR-IFeval's own rule (2026-11-22; the full relabel grades with it)
            from flotilla.core.ifeval_rules import grade_ground_truth
            return grade_ground_truth(answer, item["ground_truth"])
        return tools.constraint_check(item["task"], answer, loop_wrapped=True)["ok"]   # run-04 and earlier labels
    if t == "memory":  # LongMemEval: LLM judge (flotilla/memory/memory_route.py judge), never a silent False here
        raise ValueError("memory answers are graded by LongMemEval's judge: python -m flotilla.memory.memory_route judge")
    return False



# Known-right and known-wrong answers graded before any grading or regrade run (user, 2026-11-26). On 2026-11-26 a
# regrade ran on a Fir login node without the job modules: sympy and math_verify failed to import, sympy_check returned
# ok=False, and every math answer was silently graded wrong. Instruction cases need langdetect (the vendored checkers).
SANITY_CASES = [
    ({"task_type": "math", "task": "x", "gold": "\\frac{7}{24}"}, "7/24", True),
    ({"task_type": "math", "task": "x", "gold": "40\\text{ min}"}, "40", True),
    ({"task_type": "math", "task": "x", "gold": "35"}, "35", True),
    ({"task_type": "math", "task": "x", "gold": "\\frac{7}{24}"}, "7/25", False),
    ({"task_type": "math", "task": "x", "gold": "35"}, "36", False),
    ({"task_type": "science_mc", "task": "x", "gold": "B"}, "B", True),
    ({"task_type": "science_mc", "task": "x", "gold": "B"}, "C", False),
    ({"task_type": "instruction", "task": "x", "ground_truth": {"func_name": "validate_lowercase"}}, "all lower case here", True),
    ({"task_type": "instruction", "task": "x", "ground_truth": {"func_name": "validate_lowercase"}}, "Not Lower Case", False),
    ({"task_type": "instruction", "task": "x", "ground_truth": {"func_name": "validate_forbidden_words",
                                                                 "forbidden_words": ["lampful"]}}, "negative", True),
    ({"task_type": "instruction", "task": "x", "ground_truth": {"func_name": "validate_forbidden_words",
                                                                 "forbidden_words": ["lampful"]}}, "a lampful of oil", False),
]


def assert_grader_sane() -> int:
    """Grades SANITY_CASES and raises RuntimeError naming every case that comes out wrong (and why, for math: the
    sympy_check detail, e.g. a missing module). Call it before any grading or regrade run. Returns the number of cases."""
    bad = []
    for item, answer, want in SANITY_CASES:
        try:
            got = grade(item, answer)
        except Exception as e:  # noqa: BLE001 - an import error here is exactly what the check is for
            got = f"error: {type(e).__name__}: {e}"
        if got is not want:
            why = ""
            if item["task_type"] == "math":
                why = f" (sympy_check: {tools.sympy_check(answer, item['gold']).get('detail')})"
            bad.append(f"{item['task_type']} answer {answer!r} gold {item.get('gold') or item.get('ground_truth')}: "
                       f"expected {want}, got {got}{why}")
    if bad:
        raise RuntimeError("grader sanity check failed; stop and fix the environment before grading:\n  "
                           + "\n  ".join(bad))
    return len(SANITY_CASES)

def make_items(pool: str, out_dir: str, shard_size: int) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(pool)]
    n_shards = (len(rows) + shard_size - 1) // shard_size
    # spread task types evenly over shards (round robin), so every shard takes about as long
    shards = [[] for _ in range(n_shards)]
    for i, r in enumerate(sorted(rows, key=lambda r: (r["task_type"], r["id"]))):
        shards[i % n_shards].append(r)
    for k, rs in enumerate(shards):
        with open(out / f"label_{k:02d}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps({"item_id": r["id"], "bench": f"label_{k:02d}", "scorer": "router_label",
                                    "task_type": r["task_type"], "task": r["task"], "source": r["source"],
                                    "gold": None}) + "\n")
    print(f"{len(rows)} questions -> {n_shards} shards of about {shard_size} in {out}")


def score(pool: str, runs: list[str], model: str, out_dir: str) -> None:
    items = {}
    for l in open(pool):
        r = json.loads(l)
        items[r["id"]] = r
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = ok = 0
    with open(out / "labels.jsonl", "w") as f:
        for run in runs:
            p = Path(run) / "trace.jsonl"
            if not p.exists():
                continue
            for line in open(p):
                t = json.loads(line)
                it = items[t["item_id"]]
                good = grade(it, t["final_answer"])
                samples = [s for m in t["models"] for s in m["samples"]]
                n += 1
                ok += good
                f.write(json.dumps({"id": it["id"], "source": it["source"], "task_type": it["task_type"], "model": model,
                                    "answer": (t["final_answer"] or "")[:4000], "correct": good,
                                    "tokens_out": sum(s.get("tokens_out", 0) for s in samples),
                                    "tokens_total": t.get("tokens_total"), "calls": t.get("calls"),
                                    "wall_seconds": t.get("wall_seconds"), "samples": len(samples),
                                    "tool_calls": len(t.get("tools", [])), "error_stage": t.get("error_stage"),
                                    "run": str(run)}) + "\n")
    (out / "summary.json").write_text(json.dumps({"model": model, "n": n, "correct": ok, "runs": runs}, indent=1))
    print(json.dumps({"model": model, "n": n, "correct": ok}))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make-items")
    m.add_argument("--pool", required=True)
    m.add_argument("--out-dir", required=True)
    m.add_argument("--shard-size", type=int, default=300)
    s = sub.add_parser("score")
    s.add_argument("--pool", required=True)
    s.add_argument("--runs", nargs="+", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "score":
        assert_grader_sane()   # known right and wrong answers first (user, 2026-11-26)
    if a.cmd == "make-items":
        make_items(a.pool, a.out_dir, a.shard_size)
    else:
        score(a.pool, a.runs, a.model, a.out)


if __name__ == "__main__":
    main()
