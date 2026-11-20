"""Every question the older models got wrong (small test and router-B labels), with the cause, for a person to read.

    python reports/failure_audit/build.py
Reads the model_audit outputs copied into experiments/test-02-model-small-test/runs/run-02/audit/<model>/ and
experiments/test-03-router-b-models/runs/run-03/audit/<model>/ (flotilla/model_audit.py), plus hand_checks.json here
(golds checked by hand). Writes older_models.md and .html here; the PDF is printed from the HTML.
"""
import html
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCES = [("Small test (5% dev, 11 benchmarks)", ROOT / "experiments/test-02-model-small-test/runs/run-02/audit"),
           ("Router-B labels (4,760 pool questions)", ROOT / "experiments/test-03-router-b-models/runs/run-03/audit")]
MODELS = {"gptoss": "gpt-oss-20b", "cmda": "Command A+", "phi": "Phi-4-reasoning", "qwen": "Qwen3.8-27B (for reference)"}
CAUSES = ["verifier bug", "grader bug", "wrong gold", "model wrong"]


def load():
    hand = json.loads((HERE / "hand_checks.json").read_text()) if (HERE / "hand_checks.json").exists() else {}
    blocks = []
    for title, d in SOURCES:
        for m in MODELS:
            f = d / m / "failures.jsonl"
            if not f.exists():
                continue
            rows = [json.loads(l) for l in open(f)]
            for r in rows:
                h = hand.get(f"{m}:{r['id']}") or hand.get(r["id"])
                if h:
                    r["cause"], r["detail"] = h[0], h[1] + " (checked by hand)"
            blocks.append((title, m, rows))
    return blocks


def trim(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + " […]"


def main() -> None:
    blocks = load()
    md = ["# Older models: every wrong answer and its cause", "",
          "gpt-oss-20b, Command A+ and Phi-4-reasoning, on the 5% small test (test 02) and the router-B labels (test 03), "
          "with Qwen's small test for reference. For each wrong answer: the question, the gold answer, the model's answer "
          "and the cause. Causes are assigned by `flotilla/model_audit.py` with the graders fixed on 2026-11-20 (see "
          "experiments/test-04-strategy-router/runs/run-02/audit/failure_report.md), then checked by hand where it "
          "matters: every answer that Qwen also gave identically against the gold, and a sample of each cause.", "",
          "| Run | Model | Wrong | Verifier bug | Grader bug | Wrong gold | Model wrong |", "|---|---|---|---|---|---|---|"]
    for title, m, rows in blocks:
        c = Counter(r["cause"] for r in rows)
        md.append(f"| {title.split(' (')[0]} | {MODELS[m]} | {len(rows)} | " + " | ".join(str(c.get(k, 0)) for k in CAUSES) + " |")
    md += ["", "Phi-4-reasoning never ran the full small test: its small-test row is the 25-question MATH-500 set that "
           "decided protocol-v9 (21 of 25 right; the 4 wrong are checked by hand).", "",
           "**Phi-4-reasoning, router-B labels (test 03 run-01, 4,856 questions):** not listed per question. That run never "
           "ran the tool loop and capped answers at 16,384 tokens: 4,162 answers hit the cap with no final answer and 694 "
           "stopped without one (a tool call with nothing to run it). No question can be judged from it, so it is a harness "
           "failure, not a model, gold, grader or verifier result. It was replaced by the real-loop labels (run-02) for "
           "Qwen and gpt-oss; Phi was dropped before that (protocol-v9).", ""]
    for title, m, rows in blocks:
        md += [f"## {MODELS[m]} · {title}", ""]
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
    (HERE / "older_models.md").write_text("\n".join(md) + "\n")
    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark", {"html": True}).enable("table").render("\n".join(md))
    css = """body{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1f2328;background:#fff;margin:0}
main{max-width:1050px;margin:28px auto;padding:0 22px} h1{font-size:26px} h2{font-size:21px;margin-top:44px;border-bottom:2px solid #1f2328;padding-bottom:6px}
h3{font-size:17px;margin-top:28px} h4{font-size:14px;margin-top:22px;border-top:1px solid #d1d9e0;padding-top:14px}
table{border-collapse:collapse;margin:10px 0;font-size:13px} th,td{border:1px solid #d1d9e0;padding:5px 9px;text-align:left}
th{background:#f6f8fa} pre{background:#f6f8fa;padding:10px;border-radius:6px;white-space:pre-wrap;font-size:12px}
code{background:#eff1f3;padding:1px 4px;border-radius:4px;font-size:12.5px} summary{color:#0969da}"""
    (HERE / "older_models.html").write_text(f"<!doctype html><meta charset=utf-8><title>Older models: wrong answers</title>"
                                           f"<style>{css}</style><main>{body}</main>")
    print({f"{t.split(' (')[0]}/{m}": len(r) for t, m, r in blocks})


if __name__ == "__main__":
    main()
