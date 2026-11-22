"""Every question the older models got wrong (small test and router-B labels), with the cause, for a person to read.

    python experiments/test-02-model-small-test/runs/run-02/audit/build.py
Reads the model_audit outputs in experiments/test-02-model-small-test/runs/run-02/audit/<model>/ and
experiments/test-03-router-b-models/runs/run-03/audit/<model>/ (flotilla/model_audit.py), plus hand_checks.json here
(golds checked by hand; they cover both tests). Writes older_models.md into each of those two audit folders: test 02's
holds the small-test models, test 03's the router-B labels. Markdown only (user, 2026-11-22).
"""
import html
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCES = [("Small test (5% dev, 11 benchmarks)", ROOT / "experiments/test-02-model-small-test/runs/run-02/audit", "02"),
           ("Router-B labels (4,760 pool questions)", ROOT / "experiments/test-03-router-b-models/runs/run-03/audit", "03")]
MODELS = {"gptoss": "gpt-oss-20b", "cmda": "Command A+", "phi": "Phi-4-reasoning", "qwen": "Qwen3.8-27B (for reference)"}
CAUSES = ["verifier bug", "grader bug", "wrong gold", "model wrong"]


def load():
    hand = json.loads((HERE / "hand_checks.json").read_text()) if (HERE / "hand_checks.json").exists() else {}
    blocks = []
    for title, d, test in SOURCES:
        for m in MODELS:
            f = d / m / "failures.jsonl"
            if not f.exists():
                continue
            rows = [json.loads(l) for l in open(f)]
            for r in rows:
                h = hand.get(f"{m}:{r['id']}") or hand.get(r["id"])
                if h:
                    r["cause"], r["detail"] = h[0], h[1] + " (checked by hand)"
            blocks.append((title, m, rows, test, d))
    return blocks


def trim(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + " […]"


INTRO = {
    "02": ("# Older models on the small test: every wrong answer and its cause",
           "gpt-oss-20b, Command A+ and Phi-4-reasoning on the 5% small test (this test, run-01), with Qwen for reference. "
           "The router-B labels' audit is in test 03 (runs/run-03/audit/older_models.md)."),
    "03": ("# gpt-oss-20b on the router-B labels: every wrong answer and its cause",
           "gpt-oss-20b on the router-B labels (this test, run-02). The small test's audit is in test 02 "
           "(runs/run-02/audit/older_models.md)."),
}
COMMON = ("For each wrong answer: the question, the gold answer, the model's answer and the cause. Causes are assigned by "
          "`flotilla/model_audit.py` with the graders fixed on 2026-11-20 (see "
          "experiments/test-04-strategy-router/runs/run-02/audit/failure_report.md), then checked by hand where it "
          "matters: every answer that Qwen also gave identically against the gold, and a sample of each cause.")
NOTES = {
    "02": ["Phi-4-reasoning never ran the full small test: its row is the 25-question MATH-500 set that decided "
           "protocol-v9 (21 of 25 right; the 4 wrong are checked by hand)."],
    "03": ["**Phi-4-reasoning, router-B labels (test 03 run-01, 4,856 questions):** not listed per question. That run never "
           "ran the tool loop and capped answers at 16,384 tokens: 4,162 answers hit the cap with no final answer and 694 "
           "stopped without one (a tool call with nothing to run it). No question can be judged from it, so it is a harness "
           "failure, not a model, gold, grader or verifier result. It was replaced by the real-loop labels (run-02) for "
           "Qwen and gpt-oss; Phi was dropped before that (protocol-v9)."],
}


def render(test: str, blocks: list) -> list[str]:
    title, intro = INTRO[test]
    md = [title, "", intro + " " + COMMON, "",
          "| Run | Model | Wrong | Verifier bug | Grader bug | Wrong gold | Model wrong |", "|---|---|---|---|---|---|---|"]
    for t, m, rows, _, _ in blocks:
        c = Counter(r["cause"] for r in rows)
        md.append(f"| {t.split(' (')[0]} | {MODELS[m]} | {len(rows)} | " + " | ".join(str(c.get(k, 0)) for k in CAUSES) + " |")
    md.append("")
    for n in NOTES[test]:
        md += [n, ""]
    for t, m, rows, _, _ in blocks:
        md += [f"## {MODELS[m]} · {t}", ""]
        for k in CAUSES:
            group = [r for r in rows if r["cause"] == k]
            if not group:
                continue
            md += [f"### {k.capitalize()} ({len(group)})", ""]
            for r in group:
                md += [f"#### {r['id']} · {r['bench']} · gold: {trim(r['gold'], 120)}", "",
                       "<details open><summary>Question</summary>", "", "```text", trim(r["task"].strip(), 1200), "```", "",
                       "</details>", "", f"**{MODELS[m].split(' (')[0]} answered:** `{trim(' '.join(r['answer'].split()), 300) or 'no answer'}`", ""]
                if r.get("attempts") and len(r["attempts"]) > 1:
                    md.append("Verifier: " + " → ".join(f"`{trim(a['answer'], 40) or '∅'}` ({a['verdict']})" for a in r["attempts"]))
                    md.append("")
                md += [f"**Diagnosis ({k}):** {r['detail'] or ('the answer is wrong' if k == 'model wrong' else '')}", ""]
    return md


def main() -> None:
    blocks = load()
    for _, d, test in SOURCES:
        mine = [b for b in blocks if b[3] == test]
        (d / "older_models.md").write_text("\n".join(render(test, mine)) + "\n")
    print({f"{t.split(' (')[0]}/{m}": len(r) for t, m, r, _, _ in blocks})


if __name__ == "__main__":
    main()
