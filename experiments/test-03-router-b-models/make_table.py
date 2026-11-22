"""test-03 tables:
  table.csv   router comparison on the held-out 10% (476 pool questions), from run-02/router/*
  labels.csv  label accuracy per model and task type, run-02 (real loop) next to run-01 (v1, broken)"""
import json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import jsonl, write_table

R2 = HERE / "runs" / "run-02"
mb = json.loads((R2 / "router" / "router_b_modernbert" / "router_b.json").read_text())
lite = json.loads((R2 / "router" / "router_b_lite" / "meta.json").read_text())["val"]
final = mb["val_log"][-1]
q = final["qwen_alone_acc"]
rows = [{"candidate": "F06", "setup": "S119", "system": "Qwen alone", "held_out_accuracy": q, "gain_over_qwen": 0.0},
        {"candidate": "F07", "setup": "S120", "system": "gpt-oss alone", "held_out_accuracy": final["gptoss_alone_acc"], "gain_over_qwen": round(final["gptoss_alone_acc"] - q, 4)},
        {"candidate": "F13", "setup": "S124", "system": "Router B: ModernBERT-base fine-tune (final epoch, saved)", "held_out_accuracy": final["routed_acc"], "gain_over_qwen": round(final["routed_acc"] - q, 4)},
        {"candidate": "F14", "setup": "S125", "system": "Baseline: bge-small + logistic regression", "held_out_accuracy": lite["routed_acc"], "gain_over_qwen": round(lite["routed_acc"] - q, 4)},
        {"candidate": "", "setup": "", "system": "Perfect router", "held_out_accuracy": final["oracle_acc"], "gain_over_qwen": round(final["oracle_acc"] - q, 4)}]
for r in rows:
    r["held_out_questions"] = mb["val_items"]
    r["source"] = "run-02/router/" + ("router_b_lite/meta.json" if "logistic" in r["system"] else "router_b_modernbert/router_b.json")
write_table(HERE, "table", rows, f"Held-out 10% of the clean pool ({mb['val_items']} questions, chosen by question id); "
            f"trained on {mb['train_items']}. Keep rule: gpt-oss stays only if the router adds about 1 point or more.")

lab = []
for run, files in (("run-02 (real loop)", {"Qwen": R2 / "router-labels-loop-qwen" / "labels.jsonl", "gpt-oss": R2 / "router-labels-loop-gptoss" / "labels.jsonl"}),
                   ("run-01 (v1, no tool loop, broken)", {"Qwen": HERE / "runs" / "run-01" / "router-labels-v1-broken-qwen" / "labels.jsonl",
                                                          "Phi": HERE / "runs" / "run-01" / "router-labels-v1-broken-phi" / "labels.jsonl"})):
    for model, f in files.items():
        c = defaultdict(lambda: [0, 0])
        for r in jsonl(f):
            c[r["task_type"]][0] += 1
            c[r["task_type"]][1] += bool(r["correct"])
        n, k = sum(v[0] for v in c.values()), sum(v[1] for v in c.values())
        lab.append({"candidate": {"Qwen": "F06", "gpt-oss": "F07"}.get(model, "") if run.startswith("run-02") else "", "setup": {("run-02", "Qwen"): "S119", ("run-02", "gpt-oss"): "S120", ("run-01", "Qwen"): "S121", ("run-01", "Phi"): "S122"}[(run[:6], model)], "valid": "scored before the grader fixes, audited" if run.startswith("run-02") else "invalid (pre-fix)", "run": run, "model": model, "questions": n, "correct": k, "accuracy": round(k / n, 4),
                    **{f"{t}_acc": round(c[t][1] / c[t][0], 4) if c[t][0] else None for t in ("math", "code", "science_mc", "instruction")}})
write_table(HERE, "labels", lab, "Router labels: share of pool questions each model answered correctly.")
print(rows[2], lab[0]["accuracy"], lab[1]["accuracy"])
