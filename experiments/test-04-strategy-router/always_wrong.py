"""The pilot questions every route got wrong, for a person to read: question, gold, each route's answers through the
verifier, trimmed reasoning, and the diagnosis made by hand. Reads runs/run-01/audit/failures.jsonl
(flotilla/failure_audit.py); writes runs/run-01/audit/always_wrong.md and .html."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUD = HERE / "runs" / "run-01" / "audit"
ROUTES = {"fast": "Fast", "tools": "Tools", "deep": "Deep", "deep_tools": "Deep+Tools", "vote": "Vote", "vote_tools": "Vote+Tools"}

# Hand diagnosis per question, after reading every route's answers, verifier checks and reasoning below.
DIAGNOSIS = {
    "mmlupro-2907": ("verifier", "All six routes answered E, the gold answer. The verifier's valid_option check accepted only A to D "
                     "(the item has no options list, and the check fell back to four letters), rejected E as invalid, and the "
                     "retry had to choose from A to D, so every route ended on A."),
    "mmlupro-3042": ("verifier", "All six routes answered H, the gold answer. The verifier rejected H, the retry gave G, which was "
                     "rejected too, and G was kept as the final answer. Same bug."),
    "mmlupro-4099": ("verifier", "All six routes answered G (65 kg x 9.8 m/s² x 4.0 m ≈ 2.5 × 10³ J, closest option G = 2.6 × 10³ J), "
                     "the gold answer. The verifier rejected G and every retry moved to D. Same bug."),
    "mmlupro-3393": ("mixed", "Deep, Deep+Tools, Vote and Vote+Tools answered G, the gold answer, and the verifier rejected it "
                     "(same bug); their retries moved to D. Fast and Tools (thinking off) answered D on the first try, which "
                     "is Qwen being wrong: high R-selected frequency is a plausible distractor."),
    "mmlupro-10772": ("qwen", "Five routes answered C on the first try and kept it: Qwen is wrong (it reads the question as asking "
                      "about the PL/I character set size and picks the 'label for a value' wording). Only Tools first answered I, "
                      "the gold answer, which the verifier rejected (same bug); one Vote+Tools sample also said I but lost the vote."),
}


def trim(s: str, n: int = 260) -> str:
    s = " ".join((s or "").split())
    return ("…" + s[-n:]) if len(s) > n else s


def main() -> None:
    rows = [json.loads(l) for l in open(AUD / "failures.jsonl")]
    qs = {}
    for r in rows:
        qs.setdefault(r["id"], {"task": r["task"], "gold": r["gold"], "source": r["source"], "routes": {}})["routes"][r["route"]] = r
    order = sorted(qs, key=lambda i: (DIAGNOSIS.get(i, ("z",))[0] != "verifier", i))
    counts = {}
    for i in qs:
        for s, r in qs[i]["routes"].items():
            counts[r["auto_cause"]] = counts.get(r["auto_cause"], 0) + 1
    md = ["# Test 04 pilot: questions every route got wrong", "",
          f"{len(qs)} of 50 pilot questions; {sum(counts.values())} route answers. Built by `always_wrong.py` from "
          "`failures.jsonl` (flotilla/failure_audit.py). Diagnosis by hand after reading every answer below.", "",
          "| Cause (automatic, checked by hand) | Route answers |", "|---|---|"]
    names = {"verifier": "Verifier rejected a correct answer (option check accepted only A to D)",
             "wrong": "Qwen wrong", "vote": "Qwen wrong in the majority (one sample was right)",
             "cap": "Hit the 32,768-token cap", "no_answer": "No answer", "grader_suspect": "Grader missed a right answer"}
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        md.append(f"| {names.get(c, c)} | {n} |")
    md += ["", "No failure here hit the token cap, and the grader matched every final answer correctly (single letters).", ""]
    for i in order:
        q = qs[i]
        tag, text = DIAGNOSIS.get(i, ("?", "not diagnosed"))
        md += [f"## {i} · gold {q['gold']}", "", "**Question**", "", "```text", q["task"].strip(), "```", "",
               f"**Diagnosis:** {text}", "", "| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |",
               "|---|---|---|---|"]
        for s in ROUTES:
            r = q["routes"].get(s)
            if not r:
                continue
            att = " → ".join(f"{a['answer'][:12] or '∅'} ({a['verdict']})" for a in r["attempts"]) or "–"
            votes = r.get("vote") or {}
            if len(r["samples"]) > 1:
                att += f"; samples {votes.get('counts')}"
            reason = next((c["reasoning_tail"] or c["content_tail"] for c in r["calls"] if c.get("reasoning_tail") or c.get("content_tail")), "")
            md.append(f"| {ROUTES[s]} | {att} | **{r['final_answer'][:20]}** | {trim(reason).replace('|', '/')} |")
        md.append("")
    (AUD / "always_wrong.md").write_text("\n".join(md) + "\n")

    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render("\n".join(md))
    css = """body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1f2328;background:#fff;margin:0}
main{max-width:1100px;margin:32px auto;padding:0 24px} h1{font-size:28px} h2{font-size:20px;margin-top:40px;border-top:1px solid #d1d9e0;padding-top:24px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px} th,td{border:1px solid #d1d9e0;padding:6px 10px;vertical-align:top;text-align:left}
th{background:#f6f8fa} pre{background:#f6f8fa;padding:12px;border-radius:6px;white-space:pre-wrap;font-size:13px} td:last-child{color:#59636e;font-size:12.5px}"""
    (AUD / "always_wrong.html").write_text(f"<!doctype html><meta charset=utf-8><title>Test 04 pilot: always wrong</title>"
                                          f"<style>{css}</style><main>{body}</main>")
    print(counts, "->", AUD / "always_wrong.md")


if __name__ == "__main__":
    main()
