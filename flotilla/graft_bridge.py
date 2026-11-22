"""GRAFT side of the Memory routes. Runs inside GRAFT's own environment, never Flotilla's:

    $GRAFT_PYTHON flotilla/graft_bridge.py BRIDGE_IN.json BRIDGE_OUT.jsonl

flotilla/memory_route.py writes BRIDGE_IN.json and starts this script; nothing else should need to. It
1. starts GRAFT's gateway (baselines/claude_gateway/server.py) on a free local port: --fake for tests, or
   --openai-base-url pointing at the vLLM server that serves Qwen (GRAFT's llm.mode "local");
2. per job (one history): loads the cached graph, or builds it with GraftAgent.memorize (LLMWriter, empty start
   graph) and saves it, together with its build cost (LLM calls, tokens, seconds); builds run in parallel threads
   (the calls are HTTP requests to vLLM, which batches them);
3. per job: retrieves the facts for the question with GRAFT's retriever (plain mode C by default) and writes them,
   one JSON line per job, to BRIDGE_OUT.jsonl.

GRAFT's files are imported, not changed. Two things are replaced in this process only: my_method.agent's
load_embedder is memoised (one embedding model for all jobs instead of one per job), and each agent's LLM client is
wrapped to count its own calls and tokens (the gateway's phase field is global, so it cannot split the cost of
builds that run at the same time).
"""
import os
import sys

# This file lives in flotilla/, whose modules (data.py, trace.py, tools.py) must not shadow GRAFT's or the
# standard library's: drop the script's folder from the import path before importing anything else
# (os and sys are already loaded when the interpreter starts, so importing them first is safe).
_HERE = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
sys.path[:] = [p for p in sys.path if os.path.realpath(p or ".") != _HERE]

import contextlib  # noqa: E402
import functools  # noqa: E402
import json  # noqa: E402

import socket  # noqa: E402
import subprocess  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402
import urllib.request  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_gateway(repo: Path, llm: dict, usage_log: Path, log) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    # the gateway's own embedder serves only /v1/embeddings, which GraftAgent does not use (it embeds in-process)
    cmd = [sys.executable, "-m", "baselines.claude_gateway.server", "--port", str(port), "--model", llm["model"],
           "--embedding-model", "hash:16", "--usage-log", str(usage_log)]
    if llm["mode"] == "fake":
        cmd.append("--fake")
    elif llm["mode"] == "local":
        cmd += ["--openai-base-url", llm["openai_base_url"]] + (["--thinking"] if llm.get("thinking") else [])
    else:
        raise SystemExit(f"llm mode {llm['mode']!r}: only 'fake' and 'local' (vLLM) are allowed for Flotilla")
    env = {**os.environ, "PYTHONPATH": str(repo), "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}
    proc = subprocess.Popen(cmd, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(3600):  # GRAFT's runner waits up to 30 minutes too (slow imports on cluster disks)
        if proc.poll() is not None:
            raise RuntimeError(f"GRAFT gateway exited during startup (code {proc.returncode})")
        try:
            urllib.request.urlopen(url + "/health", timeout=1)
            return proc, url
        except OSError:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("GRAFT gateway did not start within 30 minutes")


class CountingLLM:
    """Wraps one agent's ClaudeLLM: same complete(), plus a tally of calls, tokens and seconds."""

    def __init__(self, inner):
        self.inner, self.model = inner, inner.model
        self.calls = self.input_tokens = self.output_tokens = 0
        self.seconds = 0.0
        self.lock = threading.Lock()

    def complete(self, system, user, max_tokens):
        call = self.inner.complete(system, user, max_tokens)
        with self.lock:
            self.calls += 1
            self.input_tokens += call.input_tokens
            self.output_tokens += call.output_tokens
            self.seconds += call.latency_s
        return call

    def tally(self) -> dict:
        return {"llm_calls": self.calls, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "llm_seconds": round(self.seconds, 3)}


def make_agent(job: dict, cfg: dict, gateway_url: str):
    from baselines.common.protocol import Task
    from my_method.agent import GraftAgent
    gw = type("Gateway", (), {"anthropic_base_url": gateway_url})()
    task = Task(sub_datasets=["longmemeval_s"], chunk_size=cfg.get("chunk_tokens", 0), chunks=job["chunks"], questions=[])
    agent = GraftAgent({**cfg, "shared_graph": job["graph_file"], "work_dir": job["work_dir"]}, gw, task)
    counter = CountingLLM(agent.llm)
    agent.llm = counter
    if hasattr(agent.writer, "llm"):
        agent.writer.llm = counter  # LLMWriter holds the same client
    if getattr(agent.writer, "linker", None) is not None:
        agent.writer.linker.llm = counter
    return agent, counter


def build(job: dict, cfg: dict, gateway_url: str, commit: str) -> dict:
    """Load the cached graph (with the cost recorded when it was built) or build and save it."""
    graph, meta_path = Path(job["graph_file"]), Path(job["graph_file"] + ".build.json")
    if graph.exists() and meta_path.exists():
        return {**json.loads(meta_path.read_text()), "cache_hit": True}
    Path(job["work_dir"]).mkdir(parents=True, exist_ok=True)
    agent, counter = make_agent(job, cfg, gateway_url)
    t0 = time.time()
    info = agent.memorize(job["chunks"])
    meta = {"item_id": job["item_id"], "graph_key": job["graph_key"], "graph_file": str(graph),
            "chunks": len(job["chunks"]), "chunk_chars": sum(len(c) for c in job["chunks"]),
            "wall_seconds": round(time.time() - t0, 3), **counter.tally(), "graph": info.get("graph"),
            "writer": info.get("writer"), "graft_commit": commit, "llm": job["llm_label"], "built_at": time.time()}
    meta_path.write_text(json.dumps(meta, indent=1))
    return {**meta, "cache_hit": False}


def fact_record(store, fid: str, outdated: bool) -> dict:
    d = store.fact(fid)
    p = d["provenance"]
    return {"id": fid, "subject": d["subject"], "relation": d["relation"], "object": d["object"],
            "span": p.get("span") or "", "chunk_id": p.get("chunk_id"), "arrival": p.get("arrival"),
            "outdated": outdated, "mentions": len(d.get("mentions", []))}


def retrieve(job: dict, cfg: dict, gateway_url: str) -> dict:
    Path(job["work_dir"]).mkdir(parents=True, exist_ok=True)  # the guide preset writes its linking log here
    agent, counter = make_agent(job, cfg, gateway_url)
    agent.memorize(job["chunks"])  # the graph exists now: this loads it and makes the retriever, no LLM call
    t0 = time.time()
    if agent.retriever.cfg.query_graph or agent.retriever.cfg.guide_planning:  # off in plain mode C
        agent._prepare_query_graphs([job["question"]])
    region = agent.retriever.retrieve(job["question"])
    store = agent.store
    return {"facts": [fact_record(store, f, f in region.outdated) for f in region.facts],
            "linked_entities": [store.fact(e)["name"] if e in store.g else e for e in region.linked_entities],
            "fallback": region.fallback, "subgraph_nodes": region.subgraph_nodes, "sources": region.sources,
            "graph": store.stats(), "seconds": round(time.time() - t0, 3), **counter.tally()}


def graft_commit(repo: Path) -> str:
    if os.environ.get("GRAFT_COMMIT"):
        return os.environ["GRAFT_COMMIT"]
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=10).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text())
    out_path = Path(sys.argv[2])
    repo = Path(spec["graft_repo"]).resolve()
    sys.path.insert(0, str(repo))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import my_method.agent as agent_mod
    from eval.methods import METHODS
    agent_mod.load_embedder = functools.lru_cache(maxsize=None)(agent_mod.load_embedder)  # one model for all jobs
    cfg = {**METHODS["graft"].defaults, **spec["graft"], "model": spec["llm"]["model"], "answer_max_tokens": 256}
    jobs = spec["jobs"]
    commit = graft_commit(repo)
    cache = Path(spec["cache_dir"])
    cache.mkdir(parents=True, exist_ok=True)
    log = open(cache / "gateway.log", "a", buffering=1)
    gateway, url = start_gateway(repo, spec["llm"], cache / "usage.jsonl", log)
    results: dict[str, dict] = {}
    try:
        with contextlib.redirect_stdout(sys.stderr):  # GRAFT prints progress; stdout is not our channel
            def safe_build(job):
                try:
                    return job["item_id"], build(job, cfg, url, commit)
                except Exception as e:  # noqa: BLE001 - one bad history must not stop the others
                    return job["item_id"], {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-2000:]}
            todo = list({j["graph_file"]: j for j in jobs}.values())  # one build per graph, even if jobs share it
            with ThreadPoolExecutor(max(1, int(spec.get("build_workers", 1)))) as ex:
                builds_by_graph = {}
                for job, (iid, b) in zip(todo, ex.map(safe_build, todo)):
                    builds_by_graph[job["graph_file"]] = b
            for job in jobs:  # retrieval is quick CPU work (GOAt): one job at a time
                b = builds_by_graph[job["graph_file"]]
                row = {"item_id": job["item_id"], "graph_key": job["graph_key"], "retrieval_key": job["retrieval_key"],
                       "build": b}
                if "error" not in b:
                    try:
                        row["retrieval"] = retrieve(job, cfg, url)
                    except Exception as e:  # noqa: BLE001
                        row["error"] = f"retrieval: {type(e).__name__}: {e}"
                        row["traceback"] = traceback.format_exc()[-2000:]
                else:
                    row["error"] = "build: " + b["error"]
                results[job["item_id"]] = row
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=30)
        except subprocess.TimeoutExpired:
            gateway.kill()
        log.close()
    with open(out_path, "w") as f:
        for job in jobs:
            f.write(json.dumps(results[job["item_id"]], ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
