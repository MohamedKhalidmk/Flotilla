"""Questions every route got wrong, for a person to read: the question, the gold answer, each route's answer through
the verifier, and the hand diagnosis (grader bug, verifier bug, wrong gold, or model wrong).

    python experiments/test-04-strategy-router/always_wrong.py run-01   # pilot, 50 questions
    python experiments/test-04-strategy-router/always_wrong.py run-02   # full labels, 1,450 questions
Reads runs/<run>/audit/failures.jsonl (flotilla/research/failure_audit.py) and runs/<run>/audit/diagnosis.json (hand diagnosis);
a multiple-choice question with no written diagnosis whose gold letter was a route's first answer, rejected by the
verifier, is described from the data. Writes runs/<run>/audit/always_wrong.md and .html."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTES = {"fast": "Fast", "tools": "Tools", "deep": "Deep", "deep_tools": "Deep+Tools", "vote": "Vote", "vote_tools": "Vote+Tools"}
ORDER = ["verifier bug", "grader bug", "wrong gold", "model wrong", "mixed", "not diagnosed"]


def first_letter(s: str) -> str:
    return (s or "").strip().upper()[:1]


def auto_mc(q: dict) -> tuple[str, str] | None:
    """Multiple choice: which routes answered the gold first and were rejected by the verifier."""
    g = first_letter(q["gold"])
    hit = [ROUTES[s] for s, r in q["routes"].items() if r["attempts"] and first_letter(r["attempts"][0]["answer"]) == g
           and r["attempts"][0]["verdict"] == "reject"]
    if not hit:
        return None
    finals = sorted({r["final_answer"][:12] or "no answer" for r in q["routes"].values()})
    return ("verifier bug", f"{len(hit)} of 6 routes answered {g}, the gold, on the first try ({', '.join(hit)}). The verifier's "
            f"option check accepted only A to D (the item has no options list) and rejected it; the retries ended on "
            f"{', '.join(finals)}.")


def trim(s: str, n: int = 220) -> str:
    s = " ".join((s or "").split())
    return (s[:n] + "…") if len(s) > n else s


def main(run: str) -> None:
    aud = HERE / "runs" / run / "audit"
    rows = [json.loads(l) for l in open(aud / "failures.jsonl")]
    diag = json.loads((aud / "diagnosis.json").read_text()) if (aud / "diagnosis.json").exists() else {}
    qs = {}
    for r in rows:
        qs.setdefault(r["id"], {"task": r["task"], "gold": r["gold"], "task_type": r["task_type"], "source": r["source"],
                                "routes": {}})["routes"][r["route"]] = r
    for i, q in qs.items():
        d = diag.get(i)
        q["label"], q["why"] = (d if d else (auto_mc(q) if q["task_type"] == "science_mc" else None) or ("not diagnosed", ""))
    counts = {k: sum(q["label"] == k for q in qs.values()) for k in ORDER}
    n_all = json.loads((aud / "overlap.json").read_text())["summary"]["questions"]
    md = [f"# Test 04 {run}: questions every route got wrong", "",
          f"{len(qs)} of {n_all} questions; six routes each. For each: the question, the gold answer, every route's answer "
          "through the verifier (first answer, verdict, final), and the diagnosis made by hand. Built by `always_wrong.py` "
          "from `failures.jsonl` and `diagnosis.json`.", "", "| Diagnosis | Questions |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in counts.items() if v]
    md += [""]
    for k in ORDER:
        group = sorted(i for i, q in qs.items() if q["label"] == k)
        if not group:
            continue
        md += [f"## {k.capitalize()} ({len(group)})", ""]
        for i in group:
            q = qs[i]
            gold = q["gold"] if q["gold"] not in (None, "None") else {
                "instruction": "no gold answer: graded by the instruction checker", "code": "the task's stdin/stdout tests"}.get(q["task_type"], "")
            task = q["task"].strip()
            md += [f"### {i} · {q['task_type']} · gold: {gold}", "", "<details open><summary>Question</summary>", "", "```text",
                   task + ("\n[… cut at 1,500 characters]" if len(task) >= 1500 else ""), "```", "", "</details>", "",
                   f"**Diagnosis ({q['label']}):** {q['why']}", "", "| Route | First answer → verdict | Final answer |", "|---|---|---|"]
            for s, name in ROUTES.items():
                r = q["routes"].get(s)
                if not r:
                    continue
                path = " → ".join(f"{trim(a['answer'], 40) or 'no answer'} ({a['verdict']})" for a in r["attempts"]) or "–"
                md.append(f"| {name} | {path.replace('|', '/')} | {trim(r['final_answer'], 160).replace('|', '/') or 'no answer'} |")
            md.append("")
    (aud / "always_wrong.md").write_text("\n".join(md) + "\n")
    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark", {"html": True}).enable("table").render("\n".join(md))
    css = """body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1f2328;background:#fff;margin:0}
main{max-width:1100px;margin:32px auto;padding:0 24px} h1{font-size:28px} h2{font-size:22px;margin-top:44px;border-bottom:2px solid #1f2328;padding-bottom:6px}
h3{font-size:16px;margin-top:30px;border-top:1px solid #d1d9e0;padding-top:18px} table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}
th,td{border:1px solid #d1d9e0;padding:5px 9px;vertical-align:top;text-align:left} th{background:#f6f8fa}
pre{background:#f6f8fa;padding:12px;border-radius:6px;white-space:pre-wrap;font-size:12.5px} summary{cursor:pointer;color:#0969da}
@media print{details{display:block} details>*{display:block}}"""
    (aud / "always_wrong.html").write_text(f"<!doctype html><meta charset=utf-8><title>Test 04 {run}: always wrong</title>"
                                          f"<style>{css}</style><main>{body}</main>")
    print(counts, "->", aud / "always_wrong.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run-02")
