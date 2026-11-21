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
        # Linux (clusters): memory and process caps. macOS counts RLIMIT_NPROC per user (all processes) and
        # may refuse RLIMIT_AS, so there each limit is best-effort and NPROC is skipped.
        for lim, val in ((resource.RLIMIT_AS, mem_mb * 2**20), (resource.RLIMIT_NPROC, 64)):
            if sys.platform == "darwin" and lim == resource.RLIMIT_NPROC:
                continue
            try:
                resource.setrlimit(lim, (val, val))
            except (ValueError, OSError):
                if sys.platform != "darwin":
                    raise
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


_FLOAT = re.compile(r"^-?\d*\.\d+(?:[eE][-+]?\d+)?$|^-?\d+[eE][-+]?\d+$")


def same_tokens(got: list[str], want: list[str], tol: float = 1e-6) -> bool:
    """Token-by-token equality; decimal numbers match within absolute or relative error `tol` (judges for problems with
    real-valued answers accept 1e-5 to 1e-9; 2026-11-20: exact text comparison failed correct float answers)."""
    if len(got) != len(want):
        return False
    for a, b in zip(got, want):
        if a == b:
            continue
        if _FLOAT.match(a) or _FLOAT.match(b):
            try:
                x, y = float(a), float(b)
            except ValueError:
                return False
            if abs(x - y) <= tol * max(1.0, abs(y)):
                continue
        return False
    return True


def run_public_tests(code: str, tests: list[dict], timeout_s: float = 10.0) -> dict:
    """tests: [{"input": str, "output": str}] (stdin/stdout). Returns pass count; used to pick among samples."""
    passed = 0
    fails = []
    for t in tests:
        r = python_exec(code, t.get("input", ""), timeout_s)
        got = (r["output"] or "").strip().split()
        want = str(t.get("output", "")).strip().split()
        if r["ok"] and same_tokens(got, want):
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
        found.append({"type": "paragraphs", "n": _n(m.group(1)), "divider": "* * *" in task})
    if re.search(r"(all|entire|whole)[^.]*\b(lowercase|lower case)\b", t) or "in all lowercase" in t:
        found.append({"type": "lowercase"})
    if re.search(r"(all|entire|whole)[^.]*\b(capital letters|uppercase|upper case)\b", t) and "words with all capital letters" not in t:
        found.append({"type": "uppercase"})
    if re.search(r"\b(no|without|do not use any|avoid)\s+(any\s+)?commas?\b", t):
        found.append({"type": "no_commas"})
    if "json" in t and re.search(r"(wrap|entire output|whole output)[^.]*json", t):
        found.append({"type": "json"})
    if m := re.search(r"end (?:your|the) (?:response|answer|email|letter) with (?:the )?(?:exact )?(?:phrase )?[\"'“](.+?)[\"'”]", task, re.I):
        found.append({"type": "ends_with", "text": m.group(1)})
    if re.search(r"<<\s*title\s*>>|double angular brackets", t):
        found.append({"type": "title_brackets"})
    if m := re.search(r"(?:do not|don't|never) (?:include|use) (?:the )?(?:keywords?|words?) ([^.]+?)(?: in (?:the|your) response| in| \.|$)", t):
        kws = [k.strip(" \"'") for k in re.split(r",| and | or ", m.group(1)) if k.strip(" \"'")]
        if kws:
            found.append({"type": "forbidden_words", "words": kws[:6]})
    elif m := re.search(r"(?:include|use) (?:the )?keywords? ([^.]+?)(?: in| \.|$)", t):
        kws = [k.strip(" \"'") for k in re.split(r",| and ", m.group(1)) if k.strip(" \"'")]
        if kws:
            found.append({"type": "keywords", "words": kws[:6]})
    if m := re.search(r"postscript starting with ([^\n]+)", task, re.I):
        rest = m.group(1).strip()
        k = rest.find(":")
        phrase = rest[: k + 1] if 0 <= k <= 25 else " ".join(rest.split()[:3])
        found.append({"type": "postscript", "start": phrase.strip(" \"'")})
    elif re.search(r"(?:p\.s\.|postscript)", t):
        found.append({"type": "postscript", "start": "P.S."})
    if m := re.search(r"words with all capital letters should appear (at most|at least|less than|fewer than) (\d+) times", t):
        found.append({"type": "capital_words", "relation": m.group(1), "n": int(m.group(2))})
    return found


def _check(c: dict, ans: str, loop_wrapped: bool = False) -> bool:
    words = re.findall(r"\b\w+\b", ans)
    kind = c["type"]
    if kind == "min_words":
        return len(words) >= c["n"]
    if kind == "max_words":
        return len(words) < c["n"] if c.get("strict") else len(words) <= c["n"]
    if kind == "bullets":
        return len(re.findall(r"^\s*[\*\-]\s", ans, re.M)) == c["n"]
    if kind == "paragraphs":
        if c.get("divider"):  # "separate paragraphs with the markdown divider: * * *"
            parts = [p for p in re.split(r"\s*\*\s?\*\s?\*\s*", ans) if p.strip()]
        else:
            parts = [p for p in re.split(r"\n\s*\n", ans) if p.strip()]
        return len(parts) == c["n"]
    if kind == "lowercase":
        return ans == ans.lower()
    if kind == "uppercase":
        return ans == ans.upper()
    if kind == "no_commas":
        return "," not in ans
    if kind == "json":
        if loop_wrapped:  # the Flotilla loop always delivers its output inside one JSON block
            return True
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
    if kind == "forbidden_words":
        return not any(re.search(r"\b" + re.escape(w.lower()) + r"\b", ans.lower()) for w in c["words"])
    if kind == "postscript":  # the phrase must start a postscript after the main text, not open the answer
        start = c.get("start") or "P.S."
        if start.upper() in ("P.S.", "PS", "P.S"):
            hits = [m.start() for m in re.finditer(r"\bP\.?\s?S\.?:?", ans)]
        else:
            hits = [m.start() for m in re.finditer(re.escape(start.lower()), ans.lower())]
        return any(h > 0 and ans[:h].strip() for h in hits)
    if kind == "capital_words":
        n = sum(w.isupper() for w in words)
        return n <= c["n"] if c["relation"] == "at most" else n < c["n"] if c["relation"] in ("less than", "fewer than") else n >= c["n"]
    return True


def constraint_check(task: str, answer: str, loop_wrapped: bool = False) -> dict:
    """loop_wrapped: the answer came out of the Flotilla loop, whose whole output is one JSON block, so a
    "wrap the entire output in JSON" rule is met by the loop itself (2026-11-20: it was tested on the final_answer
    field alone and could never pass)."""
    cons = detect_constraints(task)
    results = [{"constraint": c, "passed": _check(c, answer, loop_wrapped)} for c in cons]
    return {"ok": all(r["passed"] for r in results), "output": results,
            "detail": f"{sum(r['passed'] for r in results)}/{len(results)} constraints met"}
