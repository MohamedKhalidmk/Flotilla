"""Start the vLLM servers a system config needs on this node, run the small test against them, stop them.

    python -m flotilla.serve --system configs/systems/cmda_local.json --servers configs/servers.json \
        --items-dir $SCRATCH/flotilla/smalltest --out $SCRATCH/flotilla/runs/smalltest-cmda [--benches ...] [--ids ...]
configs/servers.json gives, per server name, the model path or id, GPUs and vLLM flags. GPUs are assigned in order
(server 1 gets the first `gpus`, and so on). Each server's URL in the system config is replaced with its local port.
Server logs go to <out>/server-<name>.log. Compute is recorded in <out>/compute.json (GPU-seconds per server).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from flotilla import smalltest


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
    ap.add_argument("--items-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--benches", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--smoke-ids", nargs="*", help="run these first; stop if any errors or has no parsed answer")
    ap.add_argument("--startup-timeout", type=int, default=3600)
    a = ap.parse_args()

    system = json.loads(Path(a.system).read_text())
    specs = json.loads(Path(a.servers).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vllm = str(Path(sys.executable).parent / "vllm")
    procs, gpu_next, started = [], 0, {}
    try:
        for i, name in enumerate(system["servers"]):
            spec = specs[name]
            port = 8000 + i
            gpus = ",".join(str(g) for g in range(gpu_next, gpu_next + spec["gpus"]))
            gpu_next += spec["gpus"]
            cmd = [vllm, "serve", spec["model"], "--served-model-name", name, "--port", str(port),
                   "--tensor-parallel-size", str(spec["gpus"]), "--seed", "20261119"] + spec.get("args", [])
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpus}
            log = open(out / f"server-{name}.log", "w")
            print(f"[serve] {name}: GPUs {gpus}, port {port}: {' '.join(cmd[1:])}", flush=True)
            procs.append((name, subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT), port, spec["gpus"]))
            system["servers"][name] = {**system["servers"][name], "url": f"http://127.0.0.1:{port}/v1", "model": name}
        for name, p, port, _ in procs:
            t0 = time.time()
            wait_healthy(port, p, a.startup_timeout)
            started[name] = time.time()
            print(f"[serve] {name} healthy after {time.time() - t0:.0f} s", flush=True)
        cfg_path = out / "system.resolved.json"
        cfg_path.write_text(json.dumps(system, indent=1))
        if a.smoke_ids:
            smoke = out / "smoke"
            asyncio.run(smalltest.run(argparse.Namespace(config=str(cfg_path), items_dir=a.items_dir, out=str(smoke),
                                                         benches=None, ids=a.smoke_ids, rpm=0, max_calls=10**9,
                                                         concurrency=a.concurrency)))
            rows = [json.loads(l) for l in open(smoke / "trace.jsonl")]
            bad = [r["item_id"] for r in rows if r["final_answer"] is None or any(
                s["text"].startswith("ERROR") for m in r["models"] for s in m["samples"])]
            print(f"[serve] smoke: {len(rows)} items, problems: {bad}", flush=True)
            if bad or len(rows) < len(a.smoke_ids):
                raise SystemExit("[serve] smoke check failed; full run not started")
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
