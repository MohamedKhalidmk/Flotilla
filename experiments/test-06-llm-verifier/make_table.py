"""Test 06 table from the runs only.

    python make_table.py --runs-root $SCRATCH/flotilla/lme_llmv/runs --verdicts $SCRATCH/flotilla/lme_llmv/judge/<name>/verdicts.jsonl
    python make_table.py --runs-root ... --first-answers OUT_ROOT   # before judging: write the first answers to judge

Judge route names: <arm>_r<k> for final answers; <arm>_r<k>_first for the first answer of every item the LLM check
rejected (written by --first-answers as trace.jsonl folders). Per arm and repeat: accuracy, reject rate, retry flips
(right to wrong, wrong to right, same), checker replies with no verdict, the run's GPU-seconds (compute.json, with the
GPU it ran on), and the share of request time spent on the check and the retry (trace latencies; a hardware-free
measure of the extra compute), with extra GPU-seconds = that share x the run's GPU-seconds.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

ARMS = [("fast", "F15", "S159"), ("fast_llmv", "F33", "S160"), ("deep", "F17", "S161"), ("deep_llmv", "F34", "S162")]
BASE = {"fast_llmv": "fast", "deep_llmv": "deep"}


def run_dirs(root: Path, arm: str) -> dict[int, Path]:
    out = {}
    for d in sorted((root / arm).glob("lme_dev_r*")):
        if (d / "trace.jsonl").exists():
            out[int(d.name.split("_r")[1].split("_")[0])] = d
    return out


def traces(d: Path) -> list[dict]:
    return [json.loads(l) for l in open(d / "trace.jsonl")]


def gpu(d: Path) -> tuple[float, str]:
    c = json.loads((d / "compute.json").read_text()) if (d / "compute.json").exists() else {}
    s = sum(v.get("gpu_seconds_run", 0) for v in c.get("servers", {}).values()) or c.get("run_seconds", 0)
    return round(s, 1), "slice" if d.name.endswith("_n") else "H100"


def time_share(ts: list[dict]) -> float:
    extra = tot = 0.0
    for t in ts:
        for m in t["models"]:
            lat = sum(s["latency_s"] for s in m["samples"])
            tot += lat
            if m["name"].endswith((":llm_check", ":retry")):
                extra += lat
    return extra / tot if tot else 0.0


def first_answers(root: Path, out: Path) -> None:
    n = 0
    for arm in BASE:
        for k, d in run_dirs(root, arm).items():
            rows = []
            for t in traces(d):
                att = (t.get("verifier") or {}).get("attempts", [])
                if len(att) > 1:
                    rows.append({"item_id": t["item_id"], "final_answer": att[0]["final_answer"]})
            o = out / f"{arm}_r{k}_first"
            o.mkdir(parents=True, exist_ok=True)
            (o / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            print(f"{arm}_r{k}_first={o}  ({len(rows)} rejected items)")
            n += len(rows)
    print(f"{n} first answers to judge")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--verdicts")
    ap.add_argument("--first-answers", help="write first-answer folders here and stop")
    ap.add_argument("--out", default=str(Path(__file__).parent / "table.csv"))
    a = ap.parse_args()
    root = Path(a.runs_root)
    if a.first_answers:
        return first_answers(root, Path(a.first_answers))
    v = {}
    for l in open(a.verdicts):
        r = json.loads(l)
        v[(r["item_id"], r["route"])] = bool(r["correct"])
    rows = []
    for arm, cand, setup in ARMS:
        for k, d in run_dirs(root, arm).items():
            ts = traces(d)
            route = f"{arm}_r{k}"
            acc = [v[(t["item_id"], route)] for t in ts if (t["item_id"], route) in v]
            rej = [t for t in ts if len((t.get("verifier") or {}).get("attempts", [])) > 1]
            flips = {"right_to_wrong": 0, "wrong_to_right": 0, "same": 0, "unjudged": 0}
            for t in rej:
                f, g = v.get((t["item_id"], route + "_first")), v.get((t["item_id"], route))
                key = "unjudged" if f is None or g is None else "right_to_wrong" if f and not g else \
                      "wrong_to_right" if g and not f else "same"
                flips[key] += 1
            nover = sum(1 for t in ts for c in ((t.get("verifier") or {}).get("attempts") or [{}])[0].get("checks", [])
                        if c.get("name") == "llm_check" and str(c.get("detail", "")).startswith("no verdict"))
            gs, hw = gpu(d)
            share = time_share(ts)
            rows.append({"candidate": cand, "setup": setup, "arm": arm, "repeat": k, "gpu": hw, "items": len(ts),
                         "judged": len(acc), "accuracy": round(sum(acc) / len(acc), 4) if acc else "",
                         "rejected": len(rej), "reject_rate": round(len(rej) / len(ts), 4) if ts else "",
                         **flips, "checker_no_verdict": nover, "gpu_seconds": gs,
                         "check_retry_time_share": round(share, 4), "extra_gpu_seconds": round(share * gs, 1)})
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {a.out}")
    for arm, cand, _ in ARMS:
        accs = [r["accuracy"] for r in rows if r["arm"] == arm and r["accuracy"] != ""]
        if accs:
            print(f"{cand} {arm}: mean {statistics.mean(accs):.4f}, spread {max(accs) - min(accs):.4f}, repeats {accs}")


if __name__ == "__main__":
    main()
