"""Run one system configuration over small-test (dev) items and write a trace per item (protocol 2, 7).

    python -m flotilla.core.smalltest --config configs/systems/cmda_alone.json --items-dir DIR --out RUN_DIR \
        [--benches gsm8k math500 ...] [--rpm 18] [--max-calls 900] [--concurrency 8]
Routing here uses each item's known task type with the fixed decision table (router_a.DEFAULT_TABLE), filtered to the
config's solvers, so configurations differ only in their models. Resumable: items already in trace.jsonl are skipped.
Call caps (for rate-limited APIs) are enforced before every model call, retries included; calls.json keeps the count
across restarts. API keys come only from the environment variable named in the config.
"""
import argparse
import asyncio
import contextvars
import json
import time
from collections import defaultdict
from pathlib import Path

from flotilla.legacy.router_a import DEFAULT_TABLE
from flotilla.core.system import SystemConfig, answer
from flotilla.core.trace import Trace

CURRENT = contextvars.ContextVar("item_id", default=None)


class CallBudget(Exception):
    pass


class Limiter:
    """At most `rpm` call starts per rolling minute per server, and at most `max_calls` calls in total (persisted)."""

    def __init__(self, rpm: int, max_calls: int, state: Path):
        self.rpm, self.max_calls, self.state = rpm, max_calls, state
        self.total = json.loads(state.read_text())["calls"] if state.exists() else 0
        self.starts: dict[str, list[float]] = defaultdict(list)
        self.per_item: dict[str, int] = defaultdict(int)
        self.lock = asyncio.Lock()

    async def __call__(self, server: str) -> None:
        async with self.lock:
            if self.total >= self.max_calls:
                raise CallBudget(f"call cap {self.max_calls} reached")
            if self.rpm:
                while True:
                    now = time.time()
                    self.starts[server] = [t for t in self.starts[server] if now - t < 60]
                    if len(self.starts[server]) < self.rpm:
                        break
                    await asyncio.sleep(60 - (now - self.starts[server][0]) + 0.1)
                self.starts[server].append(time.time())
            self.total += 1
            self.per_item[CURRENT.get()] += 1
            self.state.write_text(json.dumps({"calls": self.total}))


def load_items(items_dir: str, benches: list[str] | None) -> list[dict]:
    items = []
    for f in sorted(Path(items_dir).glob("*.jsonl")):
        if benches and f.stem not in benches:
            continue
        items += [json.loads(l) for l in open(f)]
    return items


async def run(a) -> None:
    conf = json.loads(Path(a.config).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    limiter = Limiter(a.rpm, a.max_calls, out / "calls.json")
    cfg = SystemConfig(**{k: v for k, v in conf.items() if k not in ("name", "notes")}, before_call=limiter)
    trace_path = out / "trace.jsonl"
    done = {json.loads(l)["item_id"] for l in open(trace_path)} if trace_path.exists() else set()
    items = [it for it in load_items(a.items_dir, a.benches) if it["item_id"] not in done and (not a.ids or it["item_id"] in a.ids)]
    # Memory routes (flotilla/memory/memory_route.py): LongMemEval items get the run-item shape; items without a history are
    # skipped (the route is unavailable on them, not wrong); graphs are built or loaded before any answer
    # (base-route runs leave LongMemEval items as they are: how they show the history is flotilla/memory/longmemeval.py's call)
    from flotilla.memory import memory_route
    mem_conf = cfg.extra.get("memory")
    prepared = {}
    if mem_conf:
        items = [memory_route.normalize_item(it) for it in items]
        no_history = [it["item_id"] for it in items if not memory_route.has_memory(it)]
        items = [it for it in items if memory_route.has_memory(it)]
        print(f"Memory route: {len(no_history)} items have no history (route unavailable, skipped)", flush=True)
        t_prep = time.time()
        prepared = await asyncio.to_thread(memory_route.prepare, items, mem_conf,
                                           memory_route.llm_for(mem_conf, cfg.servers, cfg.solvers),
                                           memory_route.default_cache(out), getattr(a, "build_workers", 16))
        built = [m for m in prepared.values() if m.get("built_in_this_run")]
        # build time and cost apart from answering (the run's GPU time includes this; labels subtract it)
        (out / "graft_prepare.json").write_text(json.dumps({
            "wall_seconds": round(time.time() - t_prep, 1), "histories": len(prepared), "built": len(built),
            "skipped_no_history": len(no_history), "errors": [k for k, m in prepared.items() if m.get("error")],
            "build_llm_calls": sum(m["build"].get("llm_calls") or 0 for m in built),
            "build_input_tokens": sum(m["build"].get("input_tokens") or 0 for m in built),
            "build_output_tokens": sum(m["build"].get("output_tokens") or 0 for m in built)}, indent=1))
    print(f"{len(items)} items to run ({len(done)} already done); calls used so far {limiter.total}", flush=True)
    (out / "config.json").write_text(json.dumps({**conf, "rpm": a.rpm, "max_calls": a.max_calls}, indent=1))
    sem = asyncio.Semaphore(a.concurrency)
    f = open(trace_path, "a")
    stop = asyncio.Event()

    async def one(it: dict) -> None:
        async with sem:
            if stop.is_set():
                return
            CURRENT.set(it["item_id"])
            row = DEFAULT_TABLE.get(it["task_type"], DEFAULT_TABLE["general"])
            route = {"router": "known-task-type", "task_type": it["task_type"], "models": row["models"], "tools": row["tools"]}
            tr = Trace(run_id=out.name, protocol_version=cfg.protocol_version,
                       prompt_versions={"solver": cfg.prompt_version, "verifier": cfg.verifier_version},
                       benchmark=it["bench"], item_id=it["item_id"], split="dev", gold=it.get("gold") if it["scorer"] != "lcb" else None)
            try:
                if mem_conf:
                    tr.prompt_versions["memory_block"] = memory_route.MEMORY_BLOCK_VERSION
                    route = {**route, "route": f"{mem_conf['base_route']}+memory", "task_type": "memory"}
                    await answer(memory_route.with_memory(it, prepared.get(it["item_id"]), tr), route, cfg, tr)
                else:
                    await answer(it, route, cfg, tr)
            except CallBudget as e:
                stop.set()
                print(f"STOP: {e}", flush=True)
                return
            except Exception as e:  # noqa: BLE001 - record the item with its error instead of stopping the run
                tr.error_stage = "timeout_or_oom" if "Timeout" in type(e).__name__ else "format_parse_failure"
                tr.models.append({"name": "error", "quant": "-", "samples": [{"text": f"ERROR {type(e).__name__}: {e}"[:500],
                                  "final_answer": None, "confidence": None, "tokens_in": 0, "tokens_out": 0, "latency_s": 0}]})
            d = tr.finish()
            errors = [s["text"][:200] for m in d["models"] for s in m["samples"] if s["text"].startswith("ERROR")]
            if any("CallBudget" in e for e in errors):
                stop.set()
                print("STOP: call cap reached inside a call; item not recorded", flush=True)
                return
            d["calls"] = limiter.per_item.get(it["item_id"], 0)
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{it['item_id']}: answer={str(d['final_answer'])[:40]!r} calls={d['calls']} tokens={d['tokens_total']}"
                  + (f" ERR {errors[0][:120]}" if errors else ""), flush=True)

    await asyncio.gather(*[one(it) for it in items])
    f.close()
    print(f"finished; total calls {limiter.total}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--items-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--benches", nargs="*")
    ap.add_argument("--ids", nargs="*", help="only these item_ids (checks)")
    ap.add_argument("--rpm", type=int, default=0, help="max call starts per minute per server (0 = no limit)")
    ap.add_argument("--max-calls", type=int, default=10**9)
    ap.add_argument("--concurrency", type=int, default=16)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
