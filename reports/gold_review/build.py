"""Build reports/gold_review/: one Markdown file per question that any audit marked "wrong gold", for a hand review.

Sources (all in the repo): the test 04 run-02 and run-03 hand diagnoses, the test 02 hand checks, and the test 03
gpt-oss failure audit give the reasons. The test 04 graded per-question files give the six routes' answers, and the
router B label files give the Qwen and gpt-oss answers. Question text is the longest copy stored in the repo.
No verdict is written; each file ends with a blank "MK's call:" line. Labels are not changed.
Run from the repo root: python3 reports/gold_review/build.py
"""
import glob, gzip, json, os, re

OUT = "reports/gold_review"
E4 = "experiments/test-04-strategy-router/runs"
AUDITS = [  # (label, file, kind)
    ("test 04 run-02 hand diagnosis", f"{E4}/run-02/audit/diagnosis.json", "diag"),
    ("test 04 run-03 hand diagnosis", f"{E4}/run-03/audit/diagnosis.json", "diag"),
    ("test 02 hand checks", "experiments/test-02-model-small-test/runs/run-02/audit/hand_checks.json", "diag"),
    ("test 03 gpt-oss failure audit", "experiments/test-03-router-b-models/runs/run-03/audit/gptoss/failures.jsonl", "fail"),
]
ROUTES = ["fast", "tools", "deep", "deep_tools", "vote", "vote_tools"]
LABELS = {"router B labels, Qwen": "experiments/test-03-router-b-models/runs/run-02/router-labels-loop-qwen/labels.jsonl.gz",
          "router B labels, gpt-oss": "experiments/test-03-router-b-models/runs/run-02/router-labels-loop-gptoss/labels.jsonl.gz"}


def jl(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


reasons = {}
for label, path, kind in AUDITS:
    if kind == "diag":
        for i, v in json.load(open(path)).items():
            if isinstance(v, list) and v and v[0] == "wrong gold":
                reasons.setdefault(i, []).append((label, v[1]))
    else:
        for d in jl(path):
            if d.get("cause") == "wrong gold":
                reasons.setdefault(d["id"], []).append((label, d.get("detail", "")))

text, gold, meta = {}, {}, {}
for path in glob.glob("experiments/**/*.jsonl", recursive=True):
    for d in jl(path):
        i = d.get("id")
        if i not in reasons:
            continue
        t = d.get("task")
        if isinstance(t, str) and len(t) > len(text.get(i, "")) and not t.startswith("[GPQA"):
            text[i] = t
        if d.get("gold") not in (None, ""):
            gold.setdefault(i, str(d["gold"]))
        meta.setdefault(i, (d.get("source"), d.get("task_type")))

answers = {i: [] for i in reasons}
for run in ("run-02", "run-03"):
    for d in jl(f"{E4}/{run}/graded/per_question.jsonl"):
        if d["id"] in reasons:
            meta.setdefault(d["id"], (d.get("source"), d.get("task_type")))
            for r in ROUTES:
                if isinstance(d.get(r), dict):
                    a = d[r]
                    answers[d["id"]].append((f"test 04 {run}", r, a.get("answer"), a.get("correct")))
for label, path in LABELS.items():
    for d in jl(path):
        if d["id"] in reasons:
            answers[d["id"]].append((label, d.get("model"), d.get("answer"), d.get("correct")))


def fence(s):
    return "```text\n" + s.strip() + "\n```"


def cell(a):
    a = "" if a is None else str(a).strip().replace("\n", " ").replace("|", "\\|")
    return (a[:200] + "...") if len(a) > 200 else (a or "(no answer)")


os.makedirs(OUT, exist_ok=True)
rows = []
for i in sorted(reasons):
    src = {"gsm8k": "GSM8K (train)", "lcb": "LiveCodeBench", "mmlupro": "MMLU-Pro", "aime": "AIME"}.get(i.split("-")[0])
    tt = meta.get(i, (None, None))[1]
    t = text.get(i, "(question text not stored in the repo)")
    lines = [f"# {i}", "", f"Source: {src or 'unknown'}. Task type: {tt or 'unknown'}.", "", "## Question", ""]
    if i.startswith("lcb-"):
        contest, task = re.match(r"lcb-(abc\d+)_(\w+)", i).groups()
        lines += [f"Full statement: https://atcoder.jp/contests/{contest}/tasks/{contest}_{task}", ""]
    lines += [fence(t)]
    if len(t) >= 2500:
        lines += ["", "The repo stores only the first 2,500 characters of this statement."]
    if re.search(r"\n[A-J]\. ", t):
        lines += ["", "The options are listed at the end of the question above."]
    else:
        lines += ["", "Options: none (free answer)."]
    lines += ["", "## Gold", "", f"`{gold.get(i, 'unknown')}`", "", "## Answers", ""]
    if answers[i]:
        lines += ["| Run | Route or model | Answer | Graded correct |", "|---|---|---|---|"]
        lines += [f"| {r} | {m} | {cell(a)} | {c} |" for r, m, a, c in answers[i]]
    else:
        lines += ["No route answers are stored in the repo for this question."]
    lines += ["", "## Audit reasons", ""]
    lines += [f"- {label}: {why}" for label, why in reasons[i]]
    lines += ["", "---", "", "MK's call (wrong gold / ambiguous / gold is right):", ""]
    open(f"{OUT}/{i}.md", "w").write("\n".join(lines))
    rows.append(f"| [{i}]({i}.md) | {src} | `{gold.get(i, '?')}` | {', '.join(sorted({l for l, _ in reasons[i]}))} | |")

idx = ["# Wrong-gold review", "",
       f"{len(rows)} questions that at least one audit marked \"wrong gold\". Each file has the question, the gold, every "
       "stored route or model answer, and the audit's reason, with no verdict. Fill in the \"MK's call\" line at the "
       "bottom of each file. No labels change until this review is done.", "",
       "Built by `python3 reports/gold_review/build.py`.", "",
       "| Question | Source | Gold | Marked by | MK's call |", "|---|---|---|---|---|"] + rows
open(f"{OUT}/index.md", "w").write("\n".join(idx) + "\n")
print(len(rows), "files")
