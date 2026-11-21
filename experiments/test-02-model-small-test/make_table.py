"""test-02 tables from runs/run-01/*/scores.jsonl (per-question scores of each model's small-test groups):
  table.csv         per benchmark: each model's metric, questions only one model got right, all, none, perfect routers
  rule_4_2.csv      Command A+ alone minus Qwen alone, paired stratified bootstrap (10,000, seed 20261119)
  phi_vs_gptoss.csv the 25-item MATH-500 subset that decided protocol-v9 (gpt-oss in, Phi out)"""
import json, random, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import jsonl, write_table

RUN = HERE / "runs" / "run-01"
MODELS = {"qwen": "smalltest-qwen_w4a16_alone-*", "gptoss": "smalltest-gptoss_alone-*", "cmda": "smalltest-cmda_local"}
S = {m: {r["item_id"]: r for d in sorted(RUN.glob(g)) for r in jsonl(d / "scores.jsonl")} for m, g in MODELS.items()}
NAMES = {"aime2025": "AIME 2025", "aime2026": "AIME 2026", "gpqa": "GPQA-Diamond", "gsm8k": "GSM8K", "ifeval": "IFEval",
         "lcb": "LiveCodeBench", "math500": "MATH-500", "mmmu": "MMMU", "ocrbench": "OCRBench", "ruler_32k": "RULER 32K",
         "ruler_64k": "RULER 64K"}
ORDER = ["gsm8k", "math500", "aime2025", "aime2026", "gpqa", "ifeval", "lcb", "ruler_32k", "ruler_64k", "mmmu", "ocrbench"]
val = lambda r: r["score"] if r["bench"].startswith("ruler") else float(r["correct"])
rows = []
for b in ORDER:
    ids = [i for i, r in S["qwen"].items() if r["bench"] == b]
    n = len(ids)
    mean = {m: (round(sum(val(S[m][i]) for i in ids) / n, 4) if all(i in S[m] for i in ids) else None) for m in MODELS}
    cnt = Counter()
    for i in ids:
        avail = {m for m in MODELS if i in S[m]}
        got = {m for m in avail if S[m][i]["correct"]}
        cnt["none" if not got else "all" if got == avail else f"only_{next(iter(got))}" if len(got) == 1 else "two_of_three"] += 1
    best = lambda ms: round(sum(max(val(S[m][i]) for m in ms if i in S[m]) for i in ids) / n, 4)
    rows.append({"benchmark": NAMES[b], "n": n, "qwen": mean["qwen"], "gptoss": mean["gptoss"], "cmda": mean["cmda"],
                 "only_qwen": cnt["only_qwen"], "only_gptoss": cnt["only_gptoss"], "only_cmda": cnt["only_cmda"],
                 "all": cnt["all"], "none": cnt["none"], "two_of_three": cnt["two_of_three"],
                 "perfect_router_qwen_gptoss": best(("qwen", "gptoss")), "perfect_router_all3": best(tuple(MODELS)),
                 "router_gain_over_qwen": round(best(("qwen", "gptoss")) - mean["qwen"], 4)})
avg = lambda k: round(sum(r[k] for r in rows if r[k] is not None) / sum(r[k] is not None for r in rows), 4)
rows.append({"benchmark": "Mean over benchmarks", "n": sum(r["n"] for r in rows), "qwen": avg("qwen"), "gptoss": avg("gptoss"),
             "cmda": avg("cmda"), **{k: sum(r[k] for r in rows) for k in ("only_qwen", "only_gptoss", "only_cmda", "all", "none", "two_of_three")},
             "perfect_router_qwen_gptoss": avg("perfect_router_qwen_gptoss"), "perfect_router_all3": avg("perfect_router_all3"),
             "router_gain_over_qwen": round(avg("perfect_router_qwen_gptoss") - avg("qwen"), 4)})
write_table(HERE, "table", rows, "Small test (5% dev sets, same items for every model). RULER = mean sub-task score, others accuracy. "
            "gpt-oss mean is over its 9 text benchmarks (no image input).")

rng = random.Random(20261119)
by = {b: [i for i, r in S["qwen"].items() if r["bench"] == b] for b in ORDER}
mo = lambda m, smp: sum(sum(val(S[m][i]) for i in smp[b]) / len(smp[b]) for b in ORDER) / len(ORDER)
obs = mo("cmda", by) - mo("qwen", by)
diffs = sorted(mo("cmda", s) - mo("qwen", s) for s in ({b: [rng.choice(v) for _ in v] for b, v in by.items()} for _ in range(10000)))
write_table(HERE, "rule_4_2", [{"comparison": "Command A+ alone minus Qwen alone", "mean_difference": round(obs, 4),
                                "ci95_low": round(diffs[250], 4), "ci95_high": round(diffs[9749], 4), "resamples": 10000,
                                "keep_rule": "keep only if ci95_low > 0", "decision": "dropped" if diffs[250] <= 0 else "kept"}])

TEST01 = HERE.parent / "test-01-quantization" / "runs" / "run-01"
dev = {i.removeprefix("math500/") for i in json.loads((HERE.parent.parent / "configs" / "splits" / "math500.json").read_text())["dev"]}
sub = lambda rows_: {r["item_id"]: r for r in rows_ if r["item_id"] in dev}
q = sub(jsonl(TEST01 / "math500-qwen-fp8-ours" / "trace.jsonl"))
cands = [("Phi-4-reasoning-plus FP8 (ours), cap 30,000", sub(jsonl(TEST01 / "math500-phi-fp8-ours" / "trace.jsonl")))]
cands += [(f"gpt-oss-20b, effort {e}, cap 32,768", sub(jsonl(RUN / "phi-replacement" / f"st-math500-gptoss20b-{e}" / "trace.jsonl")))
          for e in ("low", "medium", "high")]
prow = [{"model": name, "n": len(r), "correct": sum(x["correct"] for x in r.values()),
         "mean_output_tokens": round(sum(x["tokens_out"] for x in r.values()) / len(r)),
         "hit_token_cap": sum(x["truncated"] for x in r.values()),
         "right_where_qwen_wrong": sum(1 for k, x in r.items() if x["correct"] and not q[k]["correct"])} for name, r in cands]
write_table(HERE, "phi_vs_gptoss", prow, "MATH-500 small set (25 dev items). Qwen FP8 got all 25 right.")
print(len(rows), "rows; rule 4.2:", round(obs, 4), diffs[250], diffs[9749])
