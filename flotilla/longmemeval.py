"""LongMemEval questions for labelling the Memory routes (test 04): leakage units, conversion, split, prompt tokens.

Source: the authors' cleaned release, xiaowu0162/longmemeval-cleaned (MIT), downloaded on a Fir login node into
$SCRATCH/flotilla/data/longmemeval/raw/ with manifest.json (URL, revision, sizes, sha256). LongMemEval is not one of
Flotilla's final benchmarks or small tests (PROTOCOL.md section 1), so all 500 questions are labelling candidates once
they pass the leakage check (section 5) against every test set in flotilla.leakage.

    python -m flotilla.longmemeval units  --raw-dir RAW --out units.jsonl
    python -m flotilla.leakage --pool units.jsonl --report longmemeval_units.json        (CPU job, embedding check)
    python -m flotilla.longmemeval build  --raw-dir RAW --leakage longmemeval_units.json --out-dir OUT --report REPORT
    python -m flotilla.longmemeval sample --items OUT/memory_items.jsonl --out tests/data/longmemeval_sample.jsonl
    python -m flotilla.longmemeval tokens --raw-dir RAW --split OUT/split.json --tokenizer QWEN_DIR --out OUT/prompt_tokens.jsonl

units: one leakage unit per question (question text) and per distinct chat turn of longmemeval_s and _oracle, long
turns cut into overlapping 200-word windows (bge-small reads 512 tokens; the overlap keeps every 13-gram whole).
build: an item is dropped if its question or any turn of any of its sessions (in _s or _oracle) is flagged; writes
memory_items.jsonl (from _s), memory_items_oracle.jsonl (same questions, evidence sessions only) and split.json
(70/15/15 train/dev/held-out stratified by question_type, seed 20261120, as flotilla.strategy_labels).
Item format, one JSON line per question:
    {item_id: "lme-<question_id>", source: "longmemeval_s" | "longmemeval_oracle", task: "memory", question_type,
     question, answer (str), question_date, sessions: [{session_id, date, turns: [{role, content}]}] (dataset order),
     answer_session_ids, abstention (question_id ends in "_abs"), meta: {question_id, answer_raw?, has_answer_turns}}
meta.has_answer_turns maps session_id -> indices of the turns the dataset marks has_answer.
tokens: Qwen chat-template token count of the solver prompt the six non-Memory routes would send (prompts/solver.v1.md,
task type long_context, whole history rendered by history_prompt), with and without tool schemas and thinking. Nothing
is truncated or dropped here.
"""
import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20261120
FILES = {"longmemeval_s": "longmemeval_s_cleaned.json", "longmemeval_oracle": "longmemeval_oracle.json",
         "longmemeval_m": "longmemeval_m_cleaned.json"}
WINDOW, OVERLAP = 200, 20          # words per leakage unit for long turns, and the overlap between windows
TASK_TYPE = "long_context"         # solver prompt task-type addition used for the token count
LIMITS = {"98304 (131072 served - 32768 out)": 98304, "131072 (served max-model-len)": 131072,
          "229376 (262144 native - 32768 out)": 229376}


def load_raw(raw_dir: str, source: str) -> list[dict]:
    return json.load(open(Path(raw_dir) / FILES[source]))


# ------------------------------------------------------------------ conversion

def convert(ex: dict, source: str) -> dict:
    sessions, has_answer = [], {}
    for sid, date, turns in zip(ex["haystack_session_ids"], ex["haystack_dates"], ex["haystack_sessions"]):
        sessions.append({"session_id": sid, "date": date,
                         "turns": [{"role": t["role"], "content": t["content"]} for t in turns]})
        marked = [i for i, t in enumerate(turns) if t.get("has_answer")]
        if marked:
            has_answer[sid] = marked
    meta = {"question_id": ex["question_id"], "has_answer_turns": has_answer}
    if not isinstance(ex["answer"], str):
        meta["answer_raw"] = ex["answer"]
    known = {"question_id", "question_type", "question", "answer", "question_date", "haystack_session_ids",
             "haystack_dates", "haystack_sessions", "answer_session_ids"}
    meta.update({k: v for k, v in ex.items() if k not in known})
    return {"item_id": f"lme-{ex['question_id']}", "source": source, "task": "memory",
            "question_type": ex["question_type"], "question": ex["question"], "answer": str(ex["answer"]),
            "question_date": ex["question_date"], "sessions": sessions,
            "answer_session_ids": list(ex["answer_session_ids"]), "abstention": ex["question_id"].endswith("_abs"),
            "meta": meta}


# ------------------------------------------------------------------ leakage units

def _windows(text: str) -> list[str]:
    w = text.split()
    if len(w) <= WINDOW:
        return [text]
    step = WINDOW - OVERLAP
    return [" ".join(w[i:i + WINDOW]) for i in range(0, max(1, len(w) - OVERLAP), step)]


def turn_key(content: str) -> str:
    return hashlib.sha1(content.encode()).hexdigest()[:16]


def _kind(session_id: str) -> str:
    return "sharegpt" if session_id.startswith("sharegpt") else "ultrachat" if session_id.startswith("ultrachat") else "simulated"


def units(raw_dir: str, sources=("longmemeval_s", "longmemeval_oracle")) -> list[dict]:
    """Leakage units ({id, source, task}, the flotilla.leakage pool format): q:<question_id> per question,
    t:<sha1 of turn>:<k> per window of each distinct turn. Sorted by length so embedding batches pad little."""
    out, seen_q, seen_t = [], set(), set()
    for src in sources:
        for ex in load_raw(raw_dir, src):
            if ex["question_id"] not in seen_q:
                seen_q.add(ex["question_id"])
                out.append({"id": f"q:{ex['question_id']}", "source": "lme_question", "task": ex["question"]})
            for sid, turns in zip(ex["haystack_session_ids"], ex["haystack_sessions"]):
                for t in turns:
                    key = turn_key(t["content"])
                    if key in seen_t or not t["content"].strip():
                        continue
                    seen_t.add(key)
                    for k, w in enumerate(_windows(t["content"])):
                        out.append({"id": f"t:{key}:{k}", "source": f"lme_turn_{_kind(sid)}_{t['role']}", "task": w})
    return sorted(out, key=lambda u: (len(u["task"]), u["id"]))


def item_flags(ex: dict, flagged_turns: set[str], flagged_q: set[str]) -> list[str]:
    """Reasons an item is dropped: its question is flagged, or a flagged turn sits in one of its sessions."""
    why = [f"question:{ex['question_id']}"] if ex["question_id"] in flagged_q else []
    for sid, turns in zip(ex["haystack_session_ids"], ex["haystack_sessions"]):
        for t in turns:
            if turn_key(t["content"]) in flagged_turns:
                why.append(f"turn:{sid}:{turn_key(t['content'])}")
    return why


# ------------------------------------------------------------------ split (as flotilla.strategy_labels)

def split(items: list[dict]) -> dict:
    groups = defaultdict(list)
    for it in items:
        groups[it["question_type"]].append(it["item_id"])
    rng = random.Random(SEED)
    sp = {"train": [], "dev": [], "held_out": []}
    for key in sorted(groups):
        g = sorted(groups[key])
        rng.shuffle(g)
        k1, k2 = round(0.70 * len(g)), round(0.85 * len(g))
        sp["train"] += g[:k1]
        sp["dev"] += g[k1:k2]
        sp["held_out"] += g[k2:]
    return {"seed": SEED, "stratified_by": ["question_type"], **sp}


# ------------------------------------------------------------------ prompt

_DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2}) \(\w+\) (\d{2}):(\d{2})")


def _date_key(d: str) -> str:
    m = _DATE.match(d or "")
    return "".join(m.groups()) if m else (d or "")


def history_prompt(item: dict) -> str:
    """The whole chat history plus the question as one user message, sessions oldest first (stable sort by date;
    LongMemEval's reader also orders sessions by date), in the wording of LongMemEval's own reader prompt."""
    parts = ["I will give you several history chats between you and a user. Please answer the question based on "
             "the relevant chat history.", "", "History Chats:"]
    for i, s in enumerate(sorted(item["sessions"], key=lambda s: _date_key(s["date"])), 1):
        parts += ["", f"### Session {i} (id {s['session_id']}):", f"Session Date: {s['date']}", "Session Content:"]
        parts += [f"{t['role']}: {t['content']}" for t in s["turns"]]
    parts += ["", f"Current Date: {item['question_date']}", f"Question: {item['question']}"]
    return "\n".join(parts)


def route_messages(item: dict, tools: bool) -> list[dict]:
    """Messages a non-Memory route sends for this item (system.solver_messages + the wording _solve_once swaps in)."""
    from flotilla.system import native_tool_prompt, solver_messages
    msgs = solver_messages(history_prompt(item), TASK_TYPE, "v1")
    msgs[0]["content"] = native_tool_prompt(msgs[0]["content"], "v1", "Native-tool wording" if tools else "No-tool wording")
    return msgs


# ------------------------------------------------------------------ commands

def cmd_units(a) -> None:
    us = units(a.raw_dir)
    with open(a.out, "w") as f:
        f.writelines(json.dumps(u, ensure_ascii=False) + "\n" for u in us)
    print(json.dumps({"units": len(us), "per_source": Counter(u["source"] for u in us)}, indent=1))


def cmd_build(a) -> None:
    rep = json.load(open(a.leakage))
    flagged = rep["flagged_items"]
    flagged_q = {f["pool_id"][2:] for f in flagged if f["pool_id"].startswith("q:")}
    flagged_t = {f["pool_id"].split(":")[1] for f in flagged if f["pool_id"].startswith("t:")}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reasons: dict[str, list[str]] = defaultdict(list)
    raw = {src: load_raw(a.raw_dir, src) for src in ("longmemeval_s", "longmemeval_oracle")}
    for src, exs in raw.items():
        for ex in exs:
            reasons[ex["question_id"]] += [f"{src}:{r}" for r in item_flags(ex, flagged_t, flagged_q)]
    dropped = {q for q, r in reasons.items() if r}
    counts = {}
    for src, name in [("longmemeval_s", "memory_items.jsonl"), ("longmemeval_oracle", "memory_items_oracle.jsonl")]:
        items = [convert(ex, src) for ex in raw[src] if ex["question_id"] not in dropped]
        with open(out / name, "w") as f:
            f.writelines(json.dumps(it, ensure_ascii=False) + "\n" for it in items)
        counts[src] = {"items": len(raw[src]), "kept": len(items),
                       "question_type": dict(sorted(Counter(it["question_type"] for it in items).items())),
                       "abstention": sum(it["abstention"] for it in items)}
        if src == "longmemeval_s":
            sp = split(items)
            (out / "split.json").write_text(json.dumps(sp, indent=1))
            counts["split"] = {k: len(sp[k]) for k in ("train", "dev", "held_out")}
            qtype = {it["item_id"]: it["question_type"] for it in items}
            counts["split_by_type"] = {k: dict(sorted(Counter(qtype[i] for i in sp[k]).items()))
                                       for k in ("train", "dev", "held_out")}
    by_unit = Counter()   # flagged unit (question id or turn hash) -> how many items it drops
    for q in dropped:
        for u in {r.rsplit(":", 1)[-1] for r in reasons[q]}:
            by_unit[u] += 1
    rep["items"] = {"rule": "an item is dropped if its question or any turn in any of its sessions (longmemeval_s or "
                            "_oracle) is a flagged unit; _m histories are not checked (not used for labels)",
                    "questions": len(reasons), "dropped": len(dropped), "kept": len(reasons) - len(dropped),
                    "dropped_items": {f"lme-{q}": sorted(set(reasons[q])) for q in sorted(dropped)},
                    "items_per_flagged_unit": dict(by_unit.most_common()), **counts}
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in rep["items"].items() if k not in ("dropped_items",)}, indent=1))


def truncate(item: dict, sessions: int = 3, turns: int = 4, chars: int = 300) -> dict:
    """Small copy for unit tests: answer sessions first, then others, up to `sessions`; turns and text cut."""
    keep = [s for s in item["sessions"] if s["session_id"] in item["answer_session_ids"]][:sessions]
    keep += [s for s in item["sessions"] if s not in keep][: max(0, sessions - len(keep))]
    order = {s["session_id"]: i for i, s in enumerate(item["sessions"])}
    keep.sort(key=lambda s: order[s["session_id"]])
    out = {**item, "sessions": [{**s, "turns": [{**t, "content": t["content"][:chars]} for t in s["turns"][:turns]]}
                                for s in keep]}
    ids = {s["session_id"] for s in keep}
    kept = {k: [i for i in v if i < turns] for k, v in item["meta"]["has_answer_turns"].items() if k in ids}
    out["meta"] = {**item["meta"], "truncated": True, "has_answer_turns": {k: v for k, v in kept.items() if v}}
    return out


def cmd_sample(a) -> None:
    items = [json.loads(l) for l in open(a.items)]
    by_type = defaultdict(list)
    for it in items:
        by_type[it["question_type"]].append(it)
    rng = random.Random(SEED)
    picked = [rng.choice(by_type[t]) for t in sorted(by_type)]
    picked += [it for it in items if it["abstention"]][:1]
    rest = [it for it in items if it not in picked]
    picked += rng.sample(rest, a.n - len(picked))
    with open(a.out, "w") as f:
        f.writelines(json.dumps(truncate(it), ensure_ascii=False) + "\n" for it in picked[: a.n])
    print(f"{len(picked[: a.n])} items -> {a.out}")


def _count(args) -> dict:
    item, tok_dir = args
    tok = _count.tok if getattr(_count, "dir", None) == tok_dir else None
    if tok is None:
        from transformers import AutoTokenizer
        _count.tok, _count.dir = AutoTokenizer.from_pretrained(tok_dir), tok_dir
        tok = _count.tok
    from flotilla.system import TOOL_SCHEMAS
    res = {}
    for tools in (False, True):
        msgs = route_messages(item, tools)
        for think in (False, True):
            text = tok.apply_chat_template(msgs, tools=TOOL_SCHEMAS if tools else None, add_generation_prompt=True,
                                           enable_thinking=think, tokenize=False)
            res[f"{'tools' if tools else 'no_tools'}_{'think' if think else 'no_think'}"] = len(
                tok(text, add_special_tokens=False)["input_ids"])
    return {"item_id": item["item_id"], "source": item["source"], "question_type": item["question_type"],
            "sessions": len(item["sessions"]), "turns": sum(len(s["turns"]) for s in item["sessions"]),
            "history_chars": sum(len(t["content"]) for s in item["sessions"] for t in s["turns"]),
            "tokens": res, "max_tokens_any_route": max(res.values())}


def _pct(xs: list[int], p: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def cmd_tokens(a) -> None:
    from concurrent.futures import ProcessPoolExecutor
    sp = json.load(open(a.split))
    keep = {i for k in ("train", "dev", "held_out") for i in sp[k]}
    summary = {"prompt": f"prompts/solver.v1.md, task type {TASK_TYPE}, history_prompt(), Qwen chat template "
                         "(add_generation_prompt; tool schemas for the Tools routes; enable_thinking on/off)",
               "tokenizer": a.tokenizer, "per_source": {}}
    with open(a.out, "w") as f, ProcessPoolExecutor(a.workers) as ex:
        for src in a.sources:
            exs = [e for e in load_raw(a.raw_dir, src) if f"lme-{e['question_id']}" in keep]
            rows = list(ex.map(_count, ((convert(e, src), a.tokenizer) for e in exs), chunksize=1))
            del exs
            f.writelines(json.dumps(r) + "\n" for r in rows)
            xs = [r["max_tokens_any_route"] for r in rows]
            summary["per_source"][src] = {
                "items": len(xs), "min": min(xs), "median": _pct(xs, 50), "p90": _pct(xs, 90), "p99": _pct(xs, 99),
                "max": max(xs), "over": {k: sum(x > v for x in xs) for k, v in LIMITS.items()},
                "route_variant_spread": {k: max(r["tokens"][k] for r in rows) for k in rows[0]["tokens"]}}
            print(json.dumps({src: summary["per_source"][src]}), flush=True)
    Path(a.summary).write_text(json.dumps(summary, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("units"); p.add_argument("--raw-dir", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("build"); p.add_argument("--raw-dir", required=True); p.add_argument("--leakage", required=True)
    p.add_argument("--out-dir", required=True); p.add_argument("--report", required=True)
    p = sub.add_parser("sample"); p.add_argument("--items", required=True); p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=10)
    p = sub.add_parser("tokens"); p.add_argument("--raw-dir", required=True); p.add_argument("--split", required=True)
    p.add_argument("--tokenizer", required=True); p.add_argument("--out", required=True)
    p.add_argument("--summary", required=True); p.add_argument("--workers", type=int, default=8)
    p.add_argument("--sources", nargs="+", default=["longmemeval_s", "longmemeval_oracle", "longmemeval_m"])
    a = ap.parse_args()
    {"units": cmd_units, "build": cmd_build, "sample": cmd_sample, "tokens": cmd_tokens}[a.cmd](a)


if __name__ == "__main__":
    main()
