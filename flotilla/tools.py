"""Python tools the router can send work to (protocol decision 6): exact checks instead of model guesses.

sympy_check   parse and compare math answers, evaluate expressions
python_exec   run code in a subprocess with time and memory limits (public tests only, never hidden)
constraint_check   our own instruction-constraint checker, written from the task text (not IFEval's grader)
Each tool returns a dict {ok, output, detail} and never raises.
"""
import json
import os
import re
import resource
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- math

def sympy_check(answer: str, reference: str | None = None, timeout_s: float = 5.0) -> dict:
    """Parse `answer` with math-verify; if `reference` is given, check equivalence."""
    try:
        from math_verify import parse, verify
        pa = parse(answer if "\\boxed" in answer or "$" in answer else f"${answer}$")
        if reference is None:
            return {"ok": bool(pa), "output": str(pa[-1]) if pa else None, "detail": "parsed" if pa else "unparseable"}
        pr = parse(reference if "\\boxed" in reference or "$" in reference else f"${reference}$")
        same = bool(pa) and bool(pr) and verify(pr, pa)
        return {"ok": same, "output": same, "detail": f"{pa[-1] if pa else None} vs {pr[-1] if pr else None}"}
    except Exception as e:  # noqa: BLE001 - tools never raise
        return {"ok": False, "output": None, "detail": f"{type(e).__name__}: {e}"[:300]}

# ---------------------------------------------------------------- code

def _limits(mem_mb: int):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 2**20, mem_mb * 2**20))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        os.setsid()
    return apply


def python_exec(code: str, stdin: str = "", timeout_s: float = 10.0, mem_mb: int = 2048) -> dict:
    """Run `code` with `stdin`; returns stdout. No network is available on compute nodes anyway."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "main.py")
        with open(path, "w") as f:
            f.write(code)
        try:
            p = subprocess.run([sys.executable, "-I", path], input=stdin, capture_output=True, text=True,
                               timeout=timeout_s, cwd=d, preexec_fn=_limits(mem_mb))
            return {"ok": p.returncode == 0, "output": p.stdout, "detail": p.stderr[-500:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": None, "detail": "timeout"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "output": None, "detail": f"{type(e).__name__}: {e}"[:300]}


def run_public_tests(code: str, tests: list[dict], timeout_s: float = 10.0) -> dict:
    """tests: [{"input": str, "output": str}] (stdin/stdout). Returns pass count; used to pick among samples."""
    passed = 0
    fails = []
    for t in tests:
        r = python_exec(code, t.get("input", ""), timeout_s)
        got = (r["output"] or "").strip().split()
        want = str(t.get("output", "")).strip().split()
        if r["ok"] and got == want:
            passed += 1
        elif len(fails) < 3:
            fails.append(r["detail"] or f"got {' '.join(got)[:80]!r}")
    return {"ok": passed == len(tests) and len(tests) > 0, "output": f"{passed}/{len(tests)}", "detail": "; ".join(fails)}

# ---------------------------------------------------------------- instruction constraints
# Detected from the task text with simple patterns; each detected constraint is checked on the answer.
# Written for Flotilla from plain-language reading of the instructions, not copied from any benchmark grader.

_NUM = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _n(s: str) -> int:
    return int(s) if s.isdigit() else _WORDS[s.lower()]


def detect_constraints(task: str) -> list[dict]:
    t = task.lower()
    found = []
    if m := re.search(r"(?:at least|no less than)\s+" + _NUM + r"\s+words", t):
        found.append({"type": "min_words", "n": _n(m.group(1))})
    if m := re.search(r"(?:at most|less than|no more than|fewer than)\s+" + _NUM + r"\s+words", t):
        found.append({"type": "max_words", "n": _n(m.group(1)), "strict": "less than" in m.group(0) or "fewer" in m.group(0)})
    if m := re.search(r"exactly\s+" + _NUM + r"\s+bullet", t):
        found.append({"type": "bullets", "n": _n(m.group(1))})
    if m := re.search(_NUM + r"\s+paragraphs", t):
        found.append({"type": "paragraphs", "n": _n(m.group(1))})
    if re.search(r"(all|entire|whole)[^.]*\b(lowercase|lower case)\b", t) or "in all lowercase" in t:
        found.append({"type": "lowercase"})
    if re.search(r"(all|entire|whole)[^.]*\b(capital letters|uppercase|upper case)\b", t):
        found.append({"type": "uppercase"})
    if re.search(r"\b(no|without|do not use any|avoid)\s+(any\s+)?commas?\b", t):
        found.append({"type": "no_commas"})
    if "json" in t and re.search(r"(wrap|entire output|format)[^.]*json", t):
        found.append({"type": "json"})
    if m := re.search(r"end (?:your|the) (?:response|answer|email|letter) with (?:the )?(?:exact )?(?:phrase )?[\"'“](.+?)[\"'”]", task, re.I):
        found.append({"type": "ends_with", "text": m.group(1)})
    if re.search(r"<<\s*title\s*>>|double angular brackets", t):
        found.append({"type": "title_brackets"})
    if m := re.search(r"(?:include|use) (?:the )?keywords? ([^.]+?)(?: in| \.|$)", t):
        kws = [k.strip(" \"'") for k in re.split(r",| and ", m.group(1)) if k.strip(" \"'")]
        if kws:
            found.append({"type": "keywords", "words": kws[:6]})
    if m := re.search(r"(?:p\.s\.|postscript)", t):
        found.append({"type": "postscript"})
    return found


def _check(c: dict, ans: str) -> bool:
    words = re.findall(r"\b\w+\b", ans)
    kind = c["type"]
    if kind == "min_words":
        return len(words) >= c["n"]
    if kind == "max_words":
        return len(words) < c["n"] if c.get("strict") else len(words) <= c["n"]
    if kind == "bullets":
        return len(re.findall(r"^\s*[\*\-]\s", ans, re.M)) == c["n"]
    if kind == "paragraphs":
        parts = [p for p in re.split(r"\n\s*\n|\*\*\*", ans) if p.strip()]
        return len(parts) == c["n"]
    if kind == "lowercase":
        return ans == ans.lower()
    if kind == "uppercase":
        return ans == ans.upper()
    if kind == "no_commas":
        return "," not in ans
    if kind == "json":
        s = ans.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            json.loads(s)
            return True
        except ValueError:
            return False
    if kind == "ends_with":
        return ans.strip().endswith(c["text"].strip())
    if kind == "title_brackets":
        return re.search(r"<<[^<>]+>>", ans) is not None
    if kind == "keywords":
        return all(w.lower() in ans.lower() for w in c["words"])
    if kind == "postscript":
        return re.search(r"\bP\.\s?S\.", ans) is not None
    return True


def constraint_check(task: str, answer: str) -> dict:
    cons = detect_constraints(task)
    results = [{"constraint": c, "passed": _check(c, answer)} for c in cons]
    return {"ok": all(r["passed"] for r in results), "output": results,
            "detail": f"{sum(r['passed'] for r in results)}/{len(results)} constraints met"}
