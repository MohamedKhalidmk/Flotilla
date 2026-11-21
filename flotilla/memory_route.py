"""Memory routes: GRAFT facts from the question's own history, then a base route through the normal Flotilla loop.

    Memory            = Fast        + memory
    Memory+Deep       = Deep        + memory
    Vote+Memory       = Vote        + memory
    Deep+Tools+Memory = Deep+Tools  + memory

Availability is per item: an item has memory if it has non-empty "sessions" (LongMemEval). Pool questions (math,
science, code, instruction) have none, so the four Memory routes are unavailable on them; they are skipped, never
scored as wrong.

How GRAFT is called. GRAFT runs in its own environment (torch, networkx, sentence-transformers, GOAt), as a
subprocess: flotilla/graft_bridge.py, started with GRAFT's Python, imports GRAFT from $GRAFT_REPO (GraftAgent:
LLMWriter on an empty start graph, then GRAFT's retriever) and starts GRAFT's own gateway, pointed at the vLLM
server that serves Qwen (or at its fake backend in tests). Flotilla's environment never imports torch or GRAFT, and
GRAFT's files are not changed. eval/run.py is not used: it builds MemoryAgentBench FactConsolidation tasks only and
would make GRAFT's own answer call, which the Memory routes replace with the Flotilla loop.

Caching. One graph per history, shared by the four routes: <cache>/graphs/<item_id>.<key>.json, where key hashes
the item_id, the sessions, the GRAFT build settings, the schema file and the LLM (mode and served model). The build
cost (LLM calls, tokens, seconds) is saved next to the graph (.build.json) and copied into every route's trace under
retrieval.graft_build, apart from the answering tokens, so labels can count it once per history. Retrieved facts are
cached too (<cache>/retrieval/), keyed by the graph key, the full GRAFT config and the question.

Environment: GRAFT_REPO (default ~/SGAR), GRAFT_PYTHON (default $GRAFT_REPO/.venv/bin/python, or
GRAFT_CORE_PYTHON when a job unpacks GRAFT's venv to local disk), FLOTILLA_GRAFT_CACHE (default: graft_cache next to
the run folder).

Commands (none of them calls a paid API; prepare and judge need a running vLLM server):
    python -m flotilla.memory_route dry-run [--items LME.jsonl] [--n 3]          # fake models, prints label records
    python -m flotilla.memory_route prepare --items LME.jsonl --url http://127.0.0.1:8000/v1 --model qwen_w4a16 \
        --cache DIR [--build-workers 16] [--batch-size 25] [--limit N | --ids ...] # build every graph before the routes
    python -m flotilla.memory_route judge --items LME.jsonl --runs memory=DIR [route=DIR ...] --out verdicts.jsonl
        # LongMemEval's judge prompts on Claude Haiku 5.5 (protocol-v10 addendum, PAID: key from ANTHROPIC_API_KEY);
        # --backend qwen --url http://127.0.0.1:8000/v1 --model qwen_w4a16 keeps the earlier Qwen judge
Haiku judge calls: anthropic SDK, messages.with_raw_response.create (request-id header), thinking disabled,
max_tokens 10, no sampling parameters (the API rejects them); every call is logged to usage.jsonl next to the verdicts
with cost_usd (GRAFT's price card and token_cost), request hash, message ID, request ID and reply hash, as GRAFT's
gateway logs them.
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

FLOTILLA = Path(__file__).resolve().parent.parent
BRIDGE = Path(__file__).resolve().parent / "graft_bridge.py"
CONFIGS = FLOTILLA / "configs" / "systems"

MEMORY_BLOCK_VERSION = "memory_block.v1"
CHUNK_FORMAT = "lme-session.v1"   # bump when the session text changes: it is part of the graph key

# route -> the base route it wraps (the configs repeat this as extra.memory.base_route)
MEMORY_ROUTES = {"memory": "fast", "memory_deep": "deep", "vote_memory": "vote", "deep_tools_memory": "deep_tools"}
BASE_ROUTES = ("fast", "tools", "deep", "deep_tools", "vote", "vote_tools")
ROUTE_CONFIG = {r: CONFIGS / f"qwen_strategy_{r}.json" for r in (*BASE_ROUTES, *MEMORY_ROUTES)}

# GRAFT settings decided for Flotilla (2026-11-21): Qwen for every GRAFT LLM step, empty start graph built from the
# question's own history, plain mode C (ppr_goat_ppr) with GOAt, 50 facts. No T-REx base graph.
GRAFT_DEFAULTS = {
    "writer": "llm", "schema": "fixed", "schema_path": "my_method/schema.yaml", "revisions": True,
    "start_graph": "empty", "writer_max_tokens": 8192,
    "retrieval": "ppr_goat_ppr", "explainer": "goat", "max_facts": 50, "max_tokens": 5120, "include_outdated": False,
    "goat_targets": 3, "goat_topk": 12, "gnn_checkpoint": "results/checkpoints/gnn_bge_400w",
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "chunk_tokens": 4096,   # one chunk per session; longer sessions split at turn boundaries (MemoryAgentBench's LME size)
}
# Named GRAFT configs. A route config picks one with extra.memory.graft_preset (FLOTILLA_GRAFT_PRESET overrides it
# for a whole run); extra.memory.graft then overrides single keys. "plain_c" is the briefed default. "guide_b" is
# GRAFT test 06 arm B (configs/runs/exp/tg/b_guide.yaml: the T-REx structure guide's linking pass and chain planning
# on the same empty-start graph; no T-REx fact reaches the model): 45.7 vs 34.7 for plain C on Haiku, not yet run on
# Qwen. Its planning parses each question with one extra Qwen call (logged as retrieval_llm_calls).
GRAFT_PRESETS = {
    "plain_c": {},
    "guide_b": {"trex_guide": "results/checkpoints/trex_guide.json", "guide_linking": True, "guide_planning": True},
}
DEFAULT_PRESET = "plain_c"  # code default for offline tests; the four route configs choose guide_b (GRAFT default since test 06)
# GRAFT settings that change the graph (the rest only change retrieval)
BUILD_KEYS = ("writer", "schema", "schema_path", "revisions", "start_graph", "start_graph_path", "writer_max_tokens",
              "writer_linking", "linking_candidates", "chunk_tokens")
# fake mode: GRAFT's offline GNN checkpoint, trained with the hash embedder (no model download)
FAKE_GRAFT = {"gnn_checkpoint": "results/checkpoints/gnn_default", "embedding_model": "hash:384"}


class MemoryUnavailable(Exception):
    """The item has no history, so a Memory route cannot run on it."""


# ------------------------------------------------------------------ availability

def has_memory(item: dict) -> bool:
    return bool(item.get("sessions"))


def route_available(item: dict, route: str) -> bool:
    return route not in MEMORY_ROUTES or has_memory(item)


def available_routes(item: dict, routes=(*BASE_ROUTES, *MEMORY_ROUTES)) -> list[str]:
    return [r for r in routes if route_available(item, r)]


def unavailable_record(item: dict, route: str) -> dict:
    return {"item_id": item.get("item_id", item.get("id")), "route": route, "base_route": MEMORY_ROUTES.get(route),
            "available": False, "reason": "no history (no sessions): Memory routes run only on items with their own history"}


def question_text(item: dict) -> str:
    """What every route sees as the question of a LongMemEval item (no history, no answer)."""
    q = item.get("question") or item.get("task", "")
    return f"Current date: {item['question_date']}\nQuestion: {q}" if item.get("question_date") else q


def normalize_item(item: dict) -> dict:
    """A LongMemEval item in the run-item shape smalltest/serve expect for a Memory route (bench, scorer, task,
    task_type); LongMemEval's own "task" field ("memory") is replaced by the question. The gold answer, the evidence
    session ids and meta (evidence turns) are dropped: grading reads them from the items file. Pool items pass as
    they are."""
    if "sessions" not in item or item.get("scorer") == "lme_judge":  # note: LongMemEval's own "task" is "memory"
        return item
    keep = {k: v for k, v in item.items() if k not in ("answer", "answer_session_ids", "meta")}  # meta: evidence turns
    return {**keep, "bench": item.get("bench") or item.get("source", "longmemeval"), "scorer": "lme_judge",
            "task_type": "memory", "task": question_text(item), "gold": None}


# ------------------------------------------------------------------ history -> GRAFT documents

_DATE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\D+(\d{1,2}):(\d{2}))?")


def date_key(date: str | None) -> tuple:
    """Sort key for LongMemEval dates like '2023/05/20 (Sat) 02:21'; unparseable dates sort last, in input order."""
    m = _DATE.search(date or "")
    if not m:
        return (1, 0, 0, 0, 0, 0)
    return (0, *(int(g) if g else 0 for g in m.groups()))


def _turn_line(turn: dict) -> str:
    return f"{turn.get('role', 'user')}: {str(turn.get('content', '')).strip()}"


def sessions_to_chunks(item: dict, chunk_tokens: int = 4096) -> tuple[list[str], list[dict]]:
    """Sessions in date order become GRAFT documents: one chunk per session, or pieces of at most chunk_tokens
    (about 4 characters per token) split at turn boundaries. Every chunk starts with the session's id and date, so the
    writer and the solver can tell newer facts from older ones. Returns (chunks, chunk_map): chunk_map[i] gives
    chunk i's session_id, date and part."""
    limit = max(200, chunk_tokens * 4)
    order = sorted(enumerate(item.get("sessions") or []), key=lambda p: (date_key(p[1].get("date")), p[0]))
    chunks, cmap = [], []
    for _, s in order:
        sid, date = s.get("session_id", "?"), s.get("date") or "unknown date"
        lines = []
        for t in s.get("turns") or []:
            line = _turn_line(t)
            while len(line) > limit:  # one very long turn: cut at the last space before the limit
                cut = line.rfind(" ", 0, limit)
                cut = cut if cut > limit // 2 else limit
                lines.append(line[:cut])
                line = line[cut:].lstrip()
            lines.append(line)
        pieces, cur = [], []
        for line in lines:
            if cur and sum(len(x) + 1 for x in cur) + len(line) > limit:
                pieces.append(cur)
                cur = []
            cur.append(line)
        if cur or not pieces:
            pieces.append(cur)
        for k, piece in enumerate(pieces):
            part = f", part {k + 1} of {len(pieces)}" if len(pieces) > 1 else ""
            chunks.append(f"[Chat session {sid}, date {date}{part}]\n" + "\n".join(piece))
            cmap.append({"session_id": sid, "date": date, "part": k + 1, "parts": len(pieces)})
    return chunks, cmap


# ------------------------------------------------------------------ GRAFT config, keys, paths

def graft_repo(mem_conf: dict | None = None) -> Path:
    return Path((mem_conf or {}).get("graft_repo") or os.environ.get("GRAFT_REPO") or Path.home() / "SGAR").expanduser()


def graft_python(repo: Path) -> str:
    return os.environ.get("GRAFT_PYTHON") or os.environ.get("GRAFT_CORE_PYTHON") or str(repo / ".venv" / "bin" / "python")


def graft_preset(mem_conf: dict | None) -> str:
    name = os.environ.get("FLOTILLA_GRAFT_PRESET") or (mem_conf or {}).get("graft_preset") or DEFAULT_PRESET
    if name not in GRAFT_PRESETS:
        raise ValueError(f"unknown GRAFT preset {name!r}; known: {sorted(GRAFT_PRESETS)}")
    return name


def graft_config(mem_conf: dict | None, fake: bool = False) -> dict:
    """GRAFT_DEFAULTS, then the named preset, then the config's own overrides (then the fake-mode GNN if fake).
    The preset name is kept in the config, so it is part of the retrieval cache key and of every trace."""
    name = graft_preset(mem_conf)
    cfg = {**GRAFT_DEFAULTS, **GRAFT_PRESETS[name], **((mem_conf or {}).get("graft") or {}), "preset": name}
    return {**cfg, **FAKE_GRAFT} if fake else cfg


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _safe(item_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(item_id))[:120]


def build_key(item: dict, gcfg: dict, llm_label: str, repo: Path) -> str:
    schema = repo / gcfg.get("schema_path", "my_method/schema.yaml")
    schema_hash = hashlib.sha256(schema.read_bytes()).hexdigest()[:16] if schema.exists() else "missing"
    return _h({"item_id": item["item_id"], "sessions": _h(item.get("sessions")), "chunk_format": CHUNK_FORMAT,
               "build": {k: gcfg.get(k) for k in BUILD_KEYS}, "schema": schema_hash, "llm": llm_label})


def retrieval_key(item: dict, gkey: str, gcfg: dict) -> str:
    return _h({"graph": gkey, "graft": gcfg, "question": item.get("question") or item.get("task")})


def default_cache(out_dir: str | Path | None = None) -> Path:
    if os.environ.get("FLOTILLA_GRAFT_CACHE"):
        return Path(os.environ["FLOTILLA_GRAFT_CACHE"])
    return (Path(out_dir).parent if out_dir else Path.cwd()) / "graft_cache"


def llm_for(mem_conf: dict, servers: dict | None = None, solvers: list | None = None) -> dict:
    """GRAFT's LLM: the same vLLM server and served model as the solver (llm_mode "local"), or GRAFT's fake backend.
    FLOTILLA_GRAFT_LLM=fake forces the fake backend (tests, dry runs)."""
    mode = os.environ.get("FLOTILLA_GRAFT_LLM") or (mem_conf.get("graft") or {}).get("llm_mode", "local")
    if mode == "fake":
        return {"mode": "fake", "model": "qwen-fake", "label": "fake"}
    if mode != "local":
        raise ValueError(f"GRAFT llm_mode {mode!r}: Flotilla uses only Qwen on vLLM ('local') or 'fake'")
    srv = (servers or {})[(solvers or [None])[0]]
    return {"mode": "local", "openai_base_url": srv["url"], "model": srv["model"], "label": f"local:{srv['model']}"}


# ------------------------------------------------------------------ build + retrieve (through the bridge)

def _paths(cache: Path, item: dict, gkey: str, rkey: str) -> tuple[Path, Path]:
    return (cache / "graphs" / f"{_safe(item['item_id'])}.{gkey}.json",
            cache / "retrieval" / f"{_safe(item['item_id'])}.{gkey}.{rkey}.json")


def run_bridge(spec: dict, repo: Path) -> list[dict]:
    """Start graft_bridge.py with GRAFT's Python; returns one row per job. Kept as a function so tests can count calls."""
    with tempfile.TemporaryDirectory() as tmp:
        spec_path, out_path = Path(tmp) / "bridge_in.json", Path(tmp) / "bridge_out.jsonl"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False))
        env = {**os.environ, "PYTHONPATH": str(repo), "TOKENIZERS_PARALLELISM": "false"}
        r = subprocess.run([graft_python(repo), str(BRIDGE), str(spec_path), str(out_path)], cwd=repo, env=env,
                           capture_output=True, text=True)
        log = Path(spec["cache_dir"]) / "bridge.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as f:
            f.write(f"\n==== {time.strftime('%Y-%m-%d %H:%M:%S')} jobs={len(spec['jobs'])} code={r.returncode}\n")
            f.write(r.stdout[-20000:] + r.stderr[-20000:])
        if r.returncode != 0 or not out_path.exists():
            raise RuntimeError(f"GRAFT bridge failed (code {r.returncode}); last output:\n{(r.stderr or r.stdout)[-3000:]}")
        return [json.loads(line) for line in open(out_path)]


def prepare(items: list[dict], mem_conf: dict, llm: dict, cache: str | Path, build_workers: int = 1) -> dict[str, dict]:
    """Graph (built once per history, else loaded) and retrieved facts for every item with a history.
    Returns item_id -> memory result; items without sessions are left out (their Memory routes are unavailable).
    Cached retrievals are read without starting GRAFT at all."""
    repo, cache = graft_repo(mem_conf), Path(cache)
    gcfg = graft_config(mem_conf, fake=llm["mode"] == "fake")
    out, jobs, meta = {}, [], {}
    for it in items:
        if not has_memory(it):
            continue
        chunks, cmap = sessions_to_chunks(it, gcfg["chunk_tokens"])
        gkey = build_key(it, gcfg, llm["label"], repo)
        rkey = retrieval_key(it, gkey, gcfg)
        gpath, rpath = _paths(cache, it, gkey, rkey)
        meta[it["item_id"]] = (gkey, rkey, cmap, rpath)
        if rpath.exists():
            res = json.loads(rpath.read_text())
            res["build"] = {**res["build"], "cache_hit": True}
            res["built_in_this_run"] = False
            out[it["item_id"]] = res
            continue
        jobs.append({"item_id": it["item_id"], "graph_key": gkey, "retrieval_key": rkey, "graph_file": str(gpath),
                     "work_dir": str(cache / "work" / f"{_safe(it['item_id'])}.{gkey}"), "chunks": chunks,
                     "question": it.get("question") or it.get("task", ""), "llm_label": llm["label"]})
    if jobs:
        (cache / "graphs").mkdir(parents=True, exist_ok=True)
        (cache / "retrieval").mkdir(parents=True, exist_ok=True)
        spec = {"graft_repo": str(repo), "graft": gcfg, "cache_dir": str(cache), "build_workers": build_workers,
                "llm": {k: v for k, v in llm.items() if k != "label"}, "jobs": jobs}
        for row in run_bridge(spec, repo):
            gkey, rkey, cmap, rpath = meta[row["item_id"]]
            res = {"item_id": row["item_id"], "graph_key": gkey, "retrieval_key": rkey, "chunk_map": cmap,
                   "graft": {k: gcfg.get(k) for k in ("preset", "retrieval", "explainer", "max_facts", "gnn_checkpoint",
                                                       "embedding_model", "trex_guide", "guide_linking", "guide_planning")},
                   "build": {k: v for k, v in row["build"].items() if k != "traceback"},
                   "built_in_this_run": not row["build"].get("cache_hit", False) and "error" not in row}
            if "error" in row:
                res["error"] = row["error"]  # not cached: the next run tries again
            else:
                res["retrieval"] = row["retrieval"]
                rpath.write_text(json.dumps({**res, "built_in_this_run": None}, ensure_ascii=False))
            out[row["item_id"]] = res
    return out


# ------------------------------------------------------------------ memory block and route wrappers

MEMORY_HEADER = ("MEMORY (facts that GRAFT recalled from your earlier chat sessions with this user, most relevant "
                 "first; each gives the session date and the sentence it comes from; when two facts disagree, the one "
                 "from the later session is the current one)")
MEMORY_RULE = ("Based on the relevant memory, answer the question as concisely as you can, using a single phrase if "
               "possible. If the memory does not hold the information the question asks for, say so.")


def memory_block(mem: dict) -> str:
    cmap = mem.get("chunk_map") or []
    facts = (mem.get("retrieval") or {}).get("facts") or []
    lines = [MEMORY_HEADER + ":"]
    for i, f in enumerate(facts):
        c = f.get("chunk_id")
        date = cmap[c]["date"] if isinstance(c, int) and 0 <= c < len(cmap) else "unknown date"
        span = f" | \"{f['span'].strip()}\"" if f.get("span") else ""
        lines.append(f"[M{i + 1}] {date} | {f['subject']} | {f['relation']} | {f['object']}{span}"
                     + (" | OUTDATED" if f.get("outdated") else ""))
    if not facts:
        lines.append("(no facts were recalled)")
    return "\n".join(lines) + "\nEND OF MEMORY"


def memory_task(item: dict, mem: dict) -> str:
    return f"{memory_block(mem)}\n\n{question_text(item)}\n\n{MEMORY_RULE}"


def memory_trace(mem: dict) -> dict:
    r = mem.get("retrieval") or {}
    b = mem.get("build") or {}
    return {"source": "graft", "block_version": MEMORY_BLOCK_VERSION, "graph_key": mem.get("graph_key"),
            "retrieval_key": mem.get("retrieval_key"), "graft": mem.get("graft"), "facts": len(r.get("facts") or []),
            "fact_ids": [f["id"] for f in r.get("facts") or []], "linked_entities": r.get("linked_entities"),
            "fallback": r.get("fallback"), "subgraph_nodes": r.get("subgraph_nodes"), "graph": r.get("graph"),
            "retrieval_seconds": r.get("seconds"), "retrieval_llm_calls": r.get("llm_calls", 0),
            # the build is logged apart from answering: labels count it once per history, not once per route
            "graft_build": {"cache_hit": bool(b.get("cache_hit")), "built_in_this_run": bool(mem.get("built_in_this_run")),
                            **{k: b.get(k) for k in ("llm_calls", "input_tokens", "output_tokens", "llm_seconds",
                                                     "wall_seconds", "chunks", "chunk_chars", "graft_commit", "llm")}}}


def with_memory(item: dict, mem: dict | None, trace=None) -> dict:
    """The run item a Memory route answers: memory block + question, task type "memory"; the trace gets the
    retrieval record. Raises MemoryUnavailable on items without a history."""
    if not has_memory(item):
        raise MemoryUnavailable(f"{item.get('item_id')}: no sessions")
    if mem is None:
        raise RuntimeError(f"{item['item_id']}: memory was not prepared")
    if mem.get("error"):
        raise RuntimeError(f"{item['item_id']}: GRAFT failed: {mem['error']}")
    if trace is not None:
        trace.retrieval = memory_trace(mem)
    return {"item_id": item["item_id"], "task": memory_task(item, mem), "task_type": "memory"}


def load_config(route: str, servers: dict | None = None):
    """SystemConfig of a route from configs/systems/qwen_strategy_<route>.json (servers optionally replaced)."""
    from flotilla.system import SystemConfig
    conf = json.loads(ROUTE_CONFIG[route].read_text())
    if servers:  # only where each server lives (url, model); the route's own request settings (thinking, sampling) stay
        conf["servers"] = {k: {**conf.get("servers", {}).get(k, {}), **{f: v[f] for f in ("url", "model") if f in v}}
                           for k, v in servers.items()}
    return SystemConfig(**{k: v for k, v in conf.items() if k not in ("name", "notes")})


async def run_memory_route(route: str, item: dict, mem: dict | None, cfg, trace):
    """One Memory route on one item: the matching base route's loop (solver, vote, verifier, retry) on the item with
    its memory block. cfg is the route's SystemConfig (its base-route settings plus extra.memory)."""
    from flotilla import system
    if route not in MEMORY_ROUTES:
        raise ValueError(f"{route} is not a Memory route")
    declared = (cfg.extra.get("memory") or {}).get("base_route")
    if declared and declared != MEMORY_ROUTES[route]:
        raise ValueError(f"config for {route} wraps {declared}, expected {MEMORY_ROUTES[route]}")
    run_item = with_memory(item, mem, trace)
    rt = {"router": "fixed-route", "route": route, "base_route": MEMORY_ROUTES[route], "task_type": "memory",
          "models": cfg.solvers}
    return await system.answer(run_item, rt, cfg, trace)


async def memory(item, mem, cfg, trace):
    return await run_memory_route("memory", item, mem, cfg, trace)


async def memory_deep(item, mem, cfg, trace):
    return await run_memory_route("memory_deep", item, mem, cfg, trace)


async def vote_memory(item, mem, cfg, trace):
    return await run_memory_route("vote_memory", item, mem, cfg, trace)


async def deep_tools_memory(item, mem, cfg, trace):
    return await run_memory_route("deep_tools_memory", item, mem, cfg, trace)


ROUTE_FUNCS = {"memory": memory, "memory_deep": memory_deep, "vote_memory": vote_memory,
               "deep_tools_memory": deep_tools_memory}


def label_record(route: str, d: dict, correct: bool | None = None) -> dict:
    """What a label keeps for one route on one item, from a finished trace (Trace.finish())."""
    samples = [s for m in d["models"] for s in m["samples"]]
    v = d.get("verifier") or {}
    mem = d.get("retrieval") or {}
    return {"item_id": d["item_id"], "route": route, "base_route": MEMORY_ROUTES.get(route, route), "available": True,
            "final_answer": d.get("final_answer"), "correct": correct,
            "tokens_in": sum(s["tokens_in"] for s in samples), "tokens_out": sum(s["tokens_out"] for s in samples),
            "tokens_total": d.get("tokens_total"), "model_calls": len(d.get("call_log") or []), "samples": len(samples),
            "wall_seconds": d.get("wall_seconds"), "verdict": v.get("verdict"), "retried": len(v.get("attempts", [])) > 1,
            "memory": {k: mem.get(k) for k in ("facts", "fallback", "linked_entities", "retrieval_seconds", "graph_key")},
            "graft_build": mem.get("graft_build")}


# ------------------------------------------------------------------ grading: LongMemEval's LLM judge

# Verbatim from LongMemEval's official src/evaluation/evaluate_qa.py (xiaowu0162/LongMemEval), the same text as
# MemoryAgentBench's llm_based_eval/longmem_qa_evaluate.py (commit 5380260). Official decoding: one user message,
# temperature 0, max_tokens 10, label = "yes" in the lowercased reply; abstention questions have "_abs" in their id.
JUDGE_VERSION = "longmemeval-evaluate_qa.v1"
_BASE = ("I will give you a question, a correct answer, and a response from a model. Please answer yes if the response "
         "contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or "
         "contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only "
         "contains a subset of the information required by the answer, answer no. ")
_QA = "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
JUDGE_TEMPLATES = {
    "default": _BASE + _QA,
    "temporal-reasoning": _BASE + "In addition, do not penalize off-by-one errors for the number of days. If the question "
        "asks for the number of days/weeks/months, etc., and the model makes off-by-one errors (e.g., predicting 19 days "
        "when the answer is 18), the model's response is still correct. " + _QA,
    "knowledge-update": "I will give you a question, a correct answer, and a response from a model. Please answer yes if "
        "the response contains the correct answer. Otherwise, answer no. If the response contains some previous "
        "information along with an updated answer, the response should be considered as correct as long as the updated "
        "answer is the required answer." + _QA,
    "single-session-preference": "I will give you a question, a rubric for desired personalized response, and a response "
        "from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model "
        "does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes "
        "the user's personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the model "
        "response correct? Answer yes or no only.",
    "abstention": "I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes "
        "if the model correctly identifies the question as unanswerable. The model could say that the information is "
        "incomplete, or some other information is given but the asked information is not.\n\nQuestion: {}\n\n"
        "Explanation: {}\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? Answer "
        "yes or no only.",
}
_DEFAULT_TYPES = ("single-session-user", "single-session-assistant", "multi-session")


def is_abstention(item: dict) -> bool:
    return bool(item.get("abstention")) or "_abs" in str(item.get("question_id") or item.get("item_id", ""))


def judge_prompt(question_type: str, question: str, answer: str, response: str, abstention: bool = False) -> str:
    if abstention:
        t = JUDGE_TEMPLATES["abstention"]
    elif question_type in _DEFAULT_TYPES:
        t = JUDGE_TEMPLATES["default"]
    elif question_type in JUDGE_TEMPLATES:
        t = JUDGE_TEMPLATES[question_type]
    else:
        raise NotImplementedError(question_type)  # as the official script: an unknown type is an error, not a guess
    return t.format(question, answer, response)


def parse_judge(reply: str | None) -> bool:
    return "yes" in (reply or "").strip().lower()


HAIKU = "claude-haiku-5-5"
# copied from GRAFT configs/pricing.yaml (SGAR f8c5aa4); USD per million tokens
PRICES = {HAIKU: {"long_prompt_threshold": 100000, "short": {"input": 0.10, "output": 0.50},
                  "long": {"input": 0.50, "output": 2.50}, "cache_read_multiplier": 0.1, "cache_write_multiplier": 1.25}}


def token_cost(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0,
               cache_write_tokens: int = 0) -> float:
    """USD for one request, as GRAFT's eval/cost.py: the rate card depends on the request's total prompt length."""
    p = PRICES[model]  # a model without a price is an error, never $0
    card = p["long"] if input_tokens + cache_read_tokens + cache_write_tokens > p["long_prompt_threshold"] else p["short"]
    return (input_tokens * card["input"] + cache_read_tokens * card["input"] * p["cache_read_multiplier"]
            + cache_write_tokens * card["input"] * p["cache_write_multiplier"] + output_tokens * card["output"]) / 1e6


class HaikuJudge:
    """LongMemEval's judge on Claude Haiku: one call per answer, logged like GRAFT's gateway (usage.jsonl)."""

    def __init__(self, usage_log: str | Path, model: str = HAIKU, client=None):
        if client is None:
            import anthropic
            client = anthropic.AsyncAnthropic(max_retries=5)  # key from ANTHROPIC_API_KEY only
        self.client, self.model, self.usage_log = client, model, Path(usage_log)
        self.lock = asyncio.Lock()

    async def __call__(self, prompt: str, item_id: str, route: str) -> str:
        params = {"model": self.model, "max_tokens": 10, "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}]}
        request_hash = hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        t0 = time.time()
        raw = await self.client.messages.with_raw_response.create(**params)
        msg = raw.parse()
        text = "".join(getattr(b, "text", "") or "" for b in msg.content)
        u = msg.usage
        read, write = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
        row = {"ts": time.time(), "phase": "lme_judge", "item_id": item_id, "route": route, "model": self.model,
               "input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "cache_read_tokens": read,
               "cache_write_tokens": write, "cost_usd": token_cost(self.model, u.input_tokens, u.output_tokens, read, write),
               "latency_s": round(time.time() - t0, 3), "stop_reason": msg.stop_reason, "request_hash": request_hash,
               "message_id": msg.id, "request_id": raw.headers.get("request-id"),
               "reply_hash": hashlib.sha256(text.encode()).hexdigest()[:16]}
        async with self.lock:
            with open(self.usage_log, "a") as f:
                f.write(json.dumps(row) + "\n")
        return text


async def judge_answer_haiku(item: dict, response: str | None, judge: HaikuJudge, route: str = "") -> dict:
    """LongMemEval's judge prompt for the item's question type on Claude Haiku (protocol-v10 addendum)."""
    if response is None:
        return {"correct": False, "judge_reply": None, "judge": JUDGE_VERSION, "judge_model": judge.model,
                "reason": "no final answer"}
    prompt = judge_prompt(item["question_type"], item["question"], str(item["answer"]), response, is_abstention(item))
    reply = (await judge(prompt, item["item_id"], route)).strip()
    return {"correct": parse_judge(reply), "judge_reply": reply, "judge": JUDGE_VERSION, "judge_model": judge.model}


async def judge_answer(item: dict, response: str | None, srv: dict) -> dict:
    """LongMemEval's judge with Qwen (thinking off) on the given server. srv: {url, model[, api_key_env]}."""
    from flotilla import system
    if response is None:
        return {"correct": False, "judge_reply": None, "judge": JUDGE_VERSION, "reason": "no final answer"}
    prompt = judge_prompt(item["question_type"], item["question"], str(item["answer"]), response, is_abstention(item))
    client = system.client_for(srv)
    r = await client.chat.completions.create(model=srv["model"], messages=[{"role": "user", "content": prompt}],
                                             temperature=0, max_tokens=10,
                                             extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    reply = (r.choices[0].message.content or "").strip()
    return {"correct": parse_judge(reply), "judge_reply": reply, "judge": JUDGE_VERSION, "judge_model": srv["model"]}


# ------------------------------------------------------------------ fake Qwen (tests and dry runs only)

class FakeQwen:
    """Stands in for the OpenAI client of a vLLM server. Solver calls: answers with the object of the memory fact that
    shares most words with the question (the newest on a tie), or "I do not know". Judge calls: "yes" if the correct
    answer appears in the response. Every request is kept in .seen."""

    def __init__(self):
        self.seen: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    @staticmethod
    def _words(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", s.lower())) - {"the", "a", "of", "is", "what", "which", "who", "where", "now", "my"}

    def _solve(self, text: str) -> str:
        q = re.search(r"^Question: (.+)$", text, re.M)
        qw = self._words(q.group(1) if q else text)
        best, score = None, 1
        for m in re.finditer(r"^\[M\d+\] (.+?) \| (.+?) \| (.+?) \| (.+?)(?: \| .*)?$", text, re.M):
            date, subj, rel, obj = m.groups()
            s = len(qw & self._words(subj + " " + rel))
            if s > score or (s == score and best and date >= best[0]):
                best, score = (date, obj), s
        return best[1] if best else "I do not know"

    async def create(self, model, messages, temperature=0.0, max_tokens=None, **kw):
        last = messages[-1]["content"]
        text = last if isinstance(last, str) else " ".join(p.get("text", "") for p in last if isinstance(p, dict))
        self.seen.append({"model": model, "messages": messages, "kwargs": kw})
        if text.startswith("I will give you"):
            gold = re.search(r"(?:Correct Answer|Explanation|Rubric): (.*?)\n\nModel Response: (.*?)\n\n", text, re.S)
            ok = gold and (gold.group(1).lower() in gold.group(2).lower() or
                           ("unanswerable" in text[:80] and "not" in gold.group(2).lower()))
            content = "yes" if ok else "no"
        else:
            content = json.dumps({"final_answer": self._solve(text), "confidence": 0.9, "sources": [], "tool_calls": []})
        n_in = sum(len(m["content"]) if isinstance(m["content"], str) else 0 for m in messages) // 4
        msg = SimpleNamespace(content=content, tool_calls=None, reasoning_content="")
        return SimpleNamespace(id="fake", choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                               usage=SimpleNamespace(prompt_tokens=max(1, n_in), completion_tokens=max(1, len(content) // 4)))


def _session(sid, date, user_text):
    return {"session_id": sid, "date": date, "turns": [{"role": "user", "content": user_text},
                                                       {"role": "assistant", "content": "Thanks, noted."},
                                                       {"role": "user", "content": "Please remember: " + user_text}]}


# Toy items in the LongMemEval item format. The sentences follow FactConsolidation templates because GRAFT's fake
# writer (fake_rules/graft.py) extracts facts with that template parser; real chat text gives an empty graph in fake mode.
SAMPLE_ITEMS = [
    {"item_id": "lme-toy-ku", "source": "longmemeval_s", "task": "memory", "question_type": "knowledge-update",
     "question": "Which country is Alice Moreau a citizen of now?", "answer": "Canada",
     "question_date": "2023/10/01 (Sun) 09:00",
     "sessions": [_session("s3", "2023/09/02 (Sat) 18:40", "1. Alice Moreau is a citizen of Canada."),
                  _session("s1", "2023/05/01 (Mon) 10:00", "1. Alice Moreau is a citizen of France."),
                  _session("s2", "2023/06/10 (Sat) 14:15", "1. Bob Stone was born in the city of Lyon.")],
     "answer_session_ids": ["s3"], "abstention": False},
    {"item_id": "lme-toy-ssu", "source": "longmemeval_s", "task": "memory", "question_type": "single-session-user",
     "question": "Who is Bob Stone married to?", "answer": "Carla Diaz", "question_date": "2023/08/01 (Tue) 12:00",
     "sessions": [_session("s1", "2023/07/03 (Mon) 08:30", "1. Bob Stone is married to Carla Diaz."),
                  _session("s2", "2023/07/20 (Thu) 21:05", "1. Carla Diaz is a citizen of Spain.")],
     "answer_session_ids": ["s1"], "abstention": False},
    {"item_id": "lme-toy-abs_abs", "source": "longmemeval_s", "task": "memory", "question_type": "single-session-user",
     "question": "Where did Dana Kim die?", "answer": "The user never mentioned Dana Kim; the question is unanswerable.",
     "question_date": "2023/08/01 (Tue) 12:00",
     "sessions": [_session("s1", "2023/07/03 (Mon) 08:30", "1. Erik Lund is married to Fay Moss."),
                  _session("s2", "2023/07/04 (Tue) 08:30", "1. Fay Moss was born in the city of Oslo.")],
     "answer_session_ids": [], "abstention": True},
]
POOL_SAMPLE = {"item_id": "pool-math-1", "bench": "label_00", "scorer": "router_label", "task_type": "math",
               "task": "What is 2+2?", "source": "gsm8k"}


# ------------------------------------------------------------------ commands

async def _dry_run(items: list[dict], cache: Path) -> list[dict]:
    from flotilla import system
    from flotilla.trace import Trace
    fake = FakeQwen()
    system.client_for = lambda srv: fake  # every solver, verifier-retry and judge call goes to the fake
    mem_conf = json.loads(ROUTE_CONFIG["memory"].read_text())["extra"]["memory"]
    llm = {"mode": "fake", "model": "qwen-fake", "label": "fake"}
    t0 = time.time()
    prepared = prepare(items, mem_conf, llm, cache)
    print(f"[dry-run] GRAFT prepare (fake gateway): {len(prepared)} histories in {time.time() - t0:.1f} s; "
          f"built now: {sum(m['built_in_this_run'] for m in prepared.values())}", flush=True)
    records = []
    for it in items + [POOL_SAMPLE]:
        it = normalize_item(it)
        for route in MEMORY_ROUTES:
            if not route_available(it, route):
                records.append(unavailable_record(it, route))
                continue
            cfg = load_config(route)
            tr = Trace(run_id="dry-run", protocol_version=cfg.protocol_version,
                       prompt_versions={"solver": cfg.prompt_version, "verifier": cfg.verifier_version,
                                        "memory_block": MEMORY_BLOCK_VERSION},
                       benchmark=it["bench"], item_id=it["item_id"], split="dry-run")
            await ROUTE_FUNCS[route](it, prepared.get(it["item_id"]), cfg, tr)
            d = tr.finish()
            src = next(x for x in items if x["item_id"] == it["item_id"])
            v = await judge_answer(src, d["final_answer"], {"url": "fake", "model": "qwen-fake"})
            records.append(label_record(route, d, v["correct"]))
    return records


def cmd_dry_run(a) -> None:
    items = [json.loads(l) for l in open(a.items)][: a.n] if a.items else SAMPLE_ITEMS[: a.n]
    cache = Path(a.cache) if a.cache else Path(tempfile.mkdtemp(prefix="flotilla-graft-dryrun-"))
    for r in asyncio.run(_dry_run(items, cache)):
        print(json.dumps(r, ensure_ascii=False))
    print(f"[dry-run] graph cache: {cache}", flush=True)


def cmd_prepare(a) -> None:
    """Graphs and retrieved facts for the items, in batches of --batch-size histories (one bridge call each), so
    finished retrievals are cached as the job goes and a job that hits its time limit loses at most one batch."""
    items = [json.loads(l) for l in open(a.items)]
    if a.ids:
        items = [it for it in items if it["item_id"] in set(a.ids)]
    if a.limit:
        items = items[: a.limit]
    mem_conf = json.loads(Path(a.system).read_text())["extra"]["memory"]
    if a.graft_preset:
        mem_conf = {**mem_conf, "graft_preset": a.graft_preset}
    llm = llm_for(mem_conf, {"s": {"url": a.url, "model": a.model}}, ["s"]) if not a.fake else \
        {"mode": "fake", "model": "qwen-fake", "label": "fake"}
    t0 = time.time()
    res, step = {}, max(1, a.batch_size or len(items))
    for k in range(0, len(items), step):
        tb = time.time()
        part = prepare(items[k:k + step], mem_conf, llm, a.cache, a.build_workers)
        res.update(part)
        built = [m for m in part.values() if m.get("built_in_this_run")]
        print(f"[prepare] batch {k // step + 1}: {len(part)} histories, built {len(built)}, "
              f"errors {sum(bool(m.get('error')) for m in part.values())}, {time.time() - tb:.0f} s "
              f"(total {len(res)} of {len(items)}, {time.time() - t0:.0f} s)", flush=True)
    built = [m for m in res.values() if m.get("built_in_this_run")]
    summary = {"histories": len(res), "built": len(built), "errors": {k: m["error"] for k, m in res.items() if m.get("error")},
               "wall_seconds": round(time.time() - t0, 1), "build_workers": a.build_workers, "batch_size": step,
               "graft": graft_config(mem_conf, fake=a.fake), "llm": llm.get("label"),
               "build_llm_calls": sum(m["build"].get("llm_calls") or 0 for m in built),
               "build_input_tokens": sum(m["build"].get("input_tokens") or 0 for m in built),
               "build_output_tokens": sum(m["build"].get("output_tokens") or 0 for m in built),
               "per_history": {k: {**{f: m["build"].get(f) for f in ("chunks", "chunk_chars", "llm_calls", "input_tokens",
                                                                     "output_tokens", "llm_seconds", "wall_seconds", "cache_hit")},
                                   "facts": len((m.get("retrieval") or {}).get("facts") or []),
                                   "retrieval_seconds": (m.get("retrieval") or {}).get("seconds"),
                                   "retrieval_llm_calls": (m.get("retrieval") or {}).get("llm_calls")}
                               for k, m in res.items()}}
    Path(a.cache).mkdir(parents=True, exist_ok=True)
    name = f"prepare-{os.environ.get('SLURM_JOB_ID') or time.strftime('%Y%m%d-%H%M%S')}.json"
    (Path(a.cache) / name).write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_history", "graft")}, indent=1))
    if summary["errors"]:
        raise SystemExit(f"{len(summary['errors'])} histories failed; see {Path(a.cache) / name}")


async def _judge(a) -> None:
    items = {}
    for line in open(a.items):
        it = json.loads(line)
        items[it["item_id"]] = it
    out = Path(a.out)
    done = {(r["item_id"], r["route"]) for r in map(json.loads, open(out))} if out.exists() else set()
    jobs = []
    for kv in a.runs:
        route, d = kv.split("=", 1)
        for line in open(Path(d) / "trace.jsonl"):
            t = json.loads(line)
            if t["item_id"] in items and (t["item_id"], route) not in done:
                jobs.append((route, t))
    if a.backend == "qwen" and not a.url:
        raise SystemExit("--backend qwen needs --url")
    srv = {"url": a.url, "model": a.model}
    haiku = HaikuJudge(out.parent / "usage.jsonl") if a.backend == "haiku" else None
    sem = asyncio.Semaphore(a.concurrency)
    with open(out, "a") as f:
        async def one(route, t):
            async with sem:
                if haiku is not None:
                    v = await judge_answer_haiku(items[t["item_id"]], t["final_answer"], haiku, route)
                else:
                    v = await judge_answer(items[t["item_id"]], t["final_answer"], srv)
                f.write(json.dumps({"item_id": t["item_id"], "route": route, "answer": t["final_answer"], **v},
                                   ensure_ascii=False) + "\n")
                f.flush()
        await asyncio.gather(*[one(r, t) for r, t in jobs])
    print(f"judged {len(jobs)} answers -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run", help="the four Memory routes end to end with fake models; prints label records")
    d.add_argument("--items", help="LongMemEval items (JSONL); default: built-in toy items")
    d.add_argument("--n", type=int, default=3)
    d.add_argument("--cache")
    p = sub.add_parser("prepare", help="build every history's graph and retrieve its facts (needs vLLM, or --fake)")
    p.add_argument("--items", required=True)
    p.add_argument("--system", default=str(ROUTE_CONFIG["memory"]))
    p.add_argument("--url")
    p.add_argument("--model", default="qwen_w4a16")
    p.add_argument("--cache", required=True)
    p.add_argument("--build-workers", type=int, default=16)
    p.add_argument("--fake", action="store_true")
    p.add_argument("--graft-preset", choices=sorted(GRAFT_PRESETS), help="overrides the config's graft_preset")
    p.add_argument("--batch-size", type=int, default=25, help="histories per GRAFT bridge call (0 = all at once)")
    p.add_argument("--ids", nargs="*", help="only these item_ids (pilot)")
    p.add_argument("--limit", type=int, help="only the first N items (pilot)")
    j = sub.add_parser("judge", help="grade LongMemEval answers with LongMemEval's judge prompts (Haiku; PAID)")
    j.add_argument("--items", required=True)
    j.add_argument("--runs", nargs="+", required=True, help="route=RUN_DIR ...")
    j.add_argument("--backend", choices=["haiku", "qwen"], default="haiku",
                   help="haiku (protocol-v10 addendum, default) or qwen (needs --url)")
    j.add_argument("--url")
    j.add_argument("--model", default="qwen_w4a16")
    j.add_argument("--out", required=True)
    j.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "dry-run":
        cmd_dry_run(a)
    elif a.cmd == "prepare":
        cmd_prepare(a)
    else:
        asyncio.run(_judge(a))


if __name__ == "__main__":
    main()
