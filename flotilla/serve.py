# Sources: vllm (docs/reference/REFERENCES.md)
"""Start the vLLM servers a system config needs on this node, run the small test against them, stop them.

    python -m flotilla.serve --system configs/systems/cmda_local.json --servers configs/servers.json \
        --items-dir $SCRATCH/flotilla/smalltest --out $SCRATCH/flotilla/runs/smalltest-cmda [--benches ...] [--ids ...]
configs/servers.json gives, per server name, the model path or id, GPUs and vLLM flags. GPUs are assigned in order
(server 1 gets the first `gpus`, and so on). Each server's URL in the system config is replaced with its local port.
Server logs go to <out>/server-<name>.log. Compute is recorded in <out>/compute.json (GPU-seconds per server).
The vLLM command of each server (model, max-model-len, max-num-seqs, ...) is kept in <out>/servers.resolved.json.
--exec "CMD" runs CMD (split like a shell line; {url} = the first server's base URL, {model} = its served name)
instead of the small test once the servers are healthy, e.g. flotilla.memory_route prepare or judge on LongMemEval.
"""
import argparse
import asyncio
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from flotilla import smalltest


def free_port() -> int:
    """A port no other process on this node holds. Several 1-GPU jobs can share a node: a fixed port 8000 let
    jobs reach each other's servers (Nibi, 2026-11-20)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_healthy(port: int, proc: subprocess.Popen, timeout_s: int) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:
            raise RuntimeError(f"server on port {port} exited with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(10)
    raise TimeoutError(f"server on port {port} not healthy after {timeout_s} s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--servers", required=True)
    ap.add_argument("--items-dir")
    ap.add_argument("--exec", dest="exec_cmd", help="run this command instead of the small test ({url}, {model} filled in)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--benches", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--smoke-ids", nargs="*", help="run these first; stop if any errors or has no parsed answer")
    ap.add_argument("--startup-timeout", type=int, default=3600)
    ap.add_argument("--smoke-only", action="store_true", help="run the smoke items and stop (checks)")
    a = ap.parse_args()
    if not a.items_dir and not a.exec_cmd:
        ap.error("--items-dir is required unless --exec is given")

    system = json.loads(Path(a.system).read_text())
    specs = json.loads(Path(a.servers).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vllm = str(Path(sys.executable).parent / "vllm")
    procs, gpu_next, started = [], 0, {}
    try:
        for i, name in enumerate(system["servers"]):
            spec = specs[name]
            port = free_port()
            gpus = ",".join(str(g) for g in range(gpu_next, gpu_next + spec["gpus"]))
            gpu_next += spec["gpus"]
            cmd = [vllm, "serve", spec["model"], "--served-model-name", name, "--port", str(port),
                   "--tensor-parallel-size", str(spec["gpus"]), "--seed", "20261119"] + spec.get("args", [])
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpus}
            log = open(out / f"server-{name}.log", "w")
            print(f"[serve] {name}: GPUs {gpus}, port {port}: {' '.join(cmd[1:])}", flush=True)
            procs.append((name, subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT), port, spec["gpus"]))
            resolved = json.loads((out / "servers.resolved.json").read_text()) if i else {}
            resolved[name] = {"servers_file": str(Path(a.servers).resolve()), "spec": spec, "cmd": cmd[1:],
                              "gpus": gpus, "slurm_job": os.environ.get("SLURM_JOB_ID")}
            (out / "servers.resolved.json").write_text(json.dumps(resolved, indent=1))
            system["servers"][name] = {**system["servers"][name], "url": f"http://127.0.0.1:{port}/v1", "model": name}
        for name, p, port, _ in procs:
            t0 = time.time()
            wait_healthy(port, p, a.startup_timeout)
            started[name] = time.time()
            print(f"[serve] {name} healthy after {time.time() - t0:.0f} s", flush=True)
        cfg_path = out / "system.resolved.json"
        cfg_path.write_text(json.dumps(system, indent=1))
        if a.exec_cmd:
            first = next(iter(system["servers"]))
            cmd = [x.replace("{url}", system["servers"][first]["url"]).replace("{model}", first)
                   for x in shlex.split(a.exec_cmd)]
            if cmd[0] == "python":  # the same environment as this process (the PATH python may be the bare module)
                cmd[0] = sys.executable
            print(f"[serve] exec: {' '.join(cmd)}", flush=True)
            t_run = time.time()
            rc = subprocess.run(cmd).returncode
            run_s = time.time() - t_run
            (out / "compute.json").write_text(json.dumps({
                "run_seconds": round(run_s, 1), "exec": cmd, "returncode": rc,
                "servers": {n: {"gpus": g, "gpu_seconds_run": round(run_s * g, 1),
                                "gpu_seconds_incl_startup": round((time.time() - started.get(n, time.time())) * g, 1)}
                            for n, _, _, g in procs}}, indent=1))
            if rc:
                raise SystemExit(f"[serve] exec failed with code {rc}")
            return
        if a.smoke_ids:
            smoke = out / "smoke"
            asyncio.run(smalltest.run(argparse.Namespace(config=str(cfg_path), items_dir=a.items_dir, out=str(smoke),
                                                         benches=None, ids=a.smoke_ids, rpm=0, max_calls=10**9,
                                                         concurrency=a.concurrency)))
            rows = [json.loads(l) for l in open(smoke / "trace.jsonl")]
            def capped(r):  # every sample used the whole token budget: the model ran out, the pipeline did not fail
                caps = [system["servers"].get(m["name"], {}).get("max_tokens", system["max_tokens"]) for m in r["models"]]
                return all(s.get("tokens_out", 0) >= c for m, c in zip(r["models"], caps) for s in m["samples"])
            errors = [r["item_id"] for r in rows if any(s["text"].startswith("ERROR") for m in r["models"] for s in m["samples"])]
            at_cap = [r["item_id"] for r in rows if r["final_answer"] is None and r["item_id"] not in errors and capped(r)]
            def gave_up(r):  # every sample ended with a normal stop and no answer text: the model's choice, not a fault
                ends = [c for c in r.get("call_log", []) if c["finish_reason"] == "stop"]
                return bool(ends) and all(c["content_chars"] == 0 for c in ends)
            no_text = [r["item_id"] for r in rows if r["final_answer"] is None and r["item_id"] not in errors + at_cap and gave_up(r)]
            bad = errors + [r["item_id"] for r in rows if r["final_answer"] is None and r["item_id"] not in errors + at_cap + no_text]
            print(f"[serve] smoke: {len(rows)} items, problems: {bad}, no answer at the token cap (allowed): {at_cap}, "
                  f"stopped with no answer text (allowed): {no_text}", flush=True)
            if bad or len(rows) < len(a.smoke_ids):
                raise SystemExit("[serve] smoke check failed; full run not started")
            if a.smoke_only:
                print("[serve] smoke only: done", flush=True)
                return
        t_run = time.time()
        args = argparse.Namespace(config=str(cfg_path), items_dir=a.items_dir, out=str(out), benches=a.benches, ids=a.ids,
                                  rpm=0, max_calls=10**9, concurrency=a.concurrency)
        asyncio.run(smalltest.run(args))
        run_s = time.time() - t_run
        (out / "compute.json").write_text(json.dumps({
            "run_seconds": round(run_s, 1),
            "servers": {n: {"gpus": g, "gpu_seconds_run": round(run_s * g, 1),
                            "gpu_seconds_incl_startup": round((time.time() - started.get(n, time.time())) * g, 1)}
                        for n, _, _, g in procs}}, indent=1))
    finally:
        for _, p, _, _ in procs:
            p.terminate()
        for _, p, _, _ in procs:
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
