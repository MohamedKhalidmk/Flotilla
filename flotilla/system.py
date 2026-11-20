"""Flotilla orchestration (docs/PROMPTS.md flow): router -> solvers (N samples, tool loop) -> vote ->
cross-check (optional) -> verifier -> final answer, with a full trace per question.

Solvers are OpenAI-compatible servers (vLLM, or a hosted API) listed in a config:
    servers: {qwen: {url: http://node:8000/v1, model: <served name>, quant: w4a16}, phi: {...},
              cmda: {url: https://api.cohere.ai/compatibility/v1, model: command-a-plus-05-2026, quant: api,
                     api_key_env: COHERE_API_KEY, request: {reasoning_effort: high}, max_tokens: 32768}}
api_key_env names an environment variable (the key itself is never in a config, trace or log); request holds
extra per-server request fields; max_tokens overrides the config value for that server.
Every switch the ablations need is a field of SystemConfig.
"""
import asyncio
import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from openai import AsyncOpenAI

from flotilla import tools
from flotilla.trace import Sample, Trace

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
RETRY_PREV_CHARS = 8000   # the previous turn shown on a verifier retry is cut to its last 8,000 characters
TOOL_LINE = re.compile(r"^TOOL\s+(sympy|python_exec|constraint_check|ocr)\s*:\s*(.+)$", re.M)


@dataclass
class SystemConfig:
    servers: dict                          # name -> {url, model, quant}
    solvers: list[str]                     # which servers solve (e.g. ["qwen", "phi"])
    n_samples: int = 1                     # per solver
    temperature: float = 0.6               # sampling for N > 1; N = 1 uses 0.0
    max_tokens: int = 32768
    tool_rounds: int = 3
    tools: bool = True                     # False: no tool schemas sent, prompt says no tools (strategies Fast, Deep, Vote)
    cross_check: bool = False
    verifier: bool = True
    prompt_version: str = "v1"
    verifier_version: str = "v2"
    protocol_version: str = "protocol-v2"
    extra: dict = field(default_factory=dict)
    before_call: object = None             # optional async callable(server_name) run before every model call (rate/call caps)


# ------------------------------------------------------------------ prompts

def _section(md: str, title: str) -> str:
    m = re.search(rf"^##+ {re.escape(title)}\s*\n(.*?)(?=^##+ |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def solver_messages(task: str, task_type: str, version: str, retrieved: list[str] | None = None,
                    images: list[str] | None = None) -> list[dict]:
    md = (PROMPTS / f"solver.{version}.md").read_text()
    system = _section(md, "System")
    additions = _section(md, "Task-type additions (appended to the system message)")
    for line in additions.splitlines():
        if line.startswith(f"- {task_type}:") or (task_type.startswith("vision") and line.startswith("- vision")):
            system += "\n" + line.split(":", 1)[1].strip()
    user = task if not retrieved else task + "\n\nRetrieved facts:\n" + "\n".join(retrieved)
    if images:  # base64 PNGs, sent as OpenAI image_url parts before the text
        user = [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b}"}} for b in images] + \
               [{"type": "text", "text": user}]
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def native_tool_prompt(system: str, version: str, section: str = "Native-tool wording") -> str:
    """Swap the TOOL-line sentence of the solver prompt for another wording kept in the same prompt file:
    the native-tool wording (tools offered through function calls) or the no-tool wording (no tools offered)."""
    md = (PROMPTS / f"solver.{version}.md").read_text()
    text_rule = re.search(r"You may request a Python tool by writing a line\n.*?before you continue\.", md, re.S)
    title = next((m for m in re.findall(r"^## (.+)$", md, re.M) if m.startswith(section)), section)
    native = _section(md, title)
    return system.replace(text_rule.group(0), native) if text_rule and native else system


def client_for(srv: dict) -> AsyncOpenAI:
    key = os.environ.get(srv["api_key_env"], "") if srv.get("api_key_env") else "EMPTY"
    return AsyncOpenAI(base_url=srv["url"], api_key=key or "EMPTY", timeout=3600, max_retries=0)


def retry_message(version: str, previous_answer: str | None, verdict: dict) -> str:
    """verifier.v2: tell the model its previous answer was wrong, with the failed checks and the reason."""
    md = (PROMPTS / f"verifier.{version}.md").read_text()
    template = _section(md, "Retry message")
    failed = [f"{c['name']}: {c.get('detail', '')}".strip() for c in verdict.get("checks", []) if not c.get("passed")]
    return template.format(previous_answer=previous_answer if previous_answer is not None else "(no parseable final answer)",
                           failed_checks="; ".join(failed) or "none recorded",
                           reason=verdict.get("reason", ""))


# ------------------------------------------------------------------ parsing

def parse_final(text: str) -> tuple[str | None, float | None]:
    """Last JSON object with final_answer; None if missing (scored as format_parse_failure).
    Uses a real JSON decoder from each '{', so answers containing braces (code, sets, LaTeX) parse."""
    dec = json.JSONDecoder()
    pos = len(text)
    while True:
        k = text.rfind('"final_answer"', 0, pos)
        if k < 0:
            return None, None
        j = text.rfind("{", 0, k)
        while j >= 0:
            try:
                d, _ = dec.raw_decode(text, j)
                if isinstance(d, dict) and "final_answer" in d:
                    conf = d.get("confidence")
                    fa = d["final_answer"]
                    fa = fa if isinstance(fa, str) else json.dumps(fa)
                    return fa.strip(), (float(conf) if isinstance(conf, (int, float)) else None)
            except ValueError:
                pass
            j = text.rfind("{", 0, j)
        pos = k


# ------------------------------------------------------------------ one solver call with tool loop

async def _create(name: str, srv: dict, client: AsyncOpenAI, msgs: list[dict], cfg: SystemConfig, temperature: float,
                  **extra):
    """One model call. Rate-limit and connection errors are retried with backoff (each try passes before_call,
    so call caps count it); other errors propagate and are logged as the sample's error."""
    from openai import APIConnectionError, APITimeoutError, RateLimitError, InternalServerError
    if srv.get("system_role"):   # e.g. Cohere's compatibility API takes system instructions as role "developer"
        msgs = [{**m, "role": srv["system_role"]} if m["role"] == "system" else m for m in msgs]
    for attempt in range(5):
        if cfg.before_call is not None:
            await cfg.before_call(name)
        try:
            return await client.chat.completions.create(model=srv["model"], messages=msgs, temperature=temperature,
                                                        max_tokens=srv.get("max_tokens", cfg.max_tokens),
                                                        **srv.get("request", {}), **extra)
        except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError):
            if attempt == 4:
                raise
            await asyncio.sleep(15 * 2 ** attempt)


FINAL_ROUND_NOTE = ("No more tool calls are available. Do not call a tool. Give your final answer now, "
                    "ending with the JSON block.")
TOOL_FUNCS = {
    "sympy": "Check or simplify ONE math expression or equation with sympy (not a program; use python_exec for code). input: the expression.",
    "python_exec": "Run a Python program and return its standard output. input: the full program.",
    "constraint_check": "Check a draft answer against the task's formatting instructions. input: the draft answer.",
}
# native function-calling form of the same tools, for servers whose API rejects text tool lines (native_tools: true)
TOOL_SCHEMAS = [{"type": "function", "function": {"name": n, "description": d, "parameters": {
    "type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}}} for n, d in TOOL_FUNCS.items()]


def _run_tool(tool: str, arg: str, messages: list[dict]) -> dict:
    return {"sympy": lambda a: tools.sympy_check(a), "python_exec": lambda a: tools.python_exec(a),
            "constraint_check": lambda a: tools.constraint_check(_text(messages[-1]["content"]), a),
            "ocr": lambda a: {"ok": False, "output": None, "detail": "ocr tool not enabled"}}.get(
        tool, lambda a: {"ok": False, "output": None, "detail": f"unknown tool {tool}"})(arg)


async def _solve_once(name: str, srv: dict, messages: list[dict], cfg: SystemConfig,
                      temperature: float, trace: Trace) -> Sample:
    client = client_for(srv)
    t0, tok_in, tok_out, text_all = time.time(), 0, 0, ""
    msgs = list(messages)
    native = bool(srv.get("native_tools"))
    extra = {"tools": TOOL_SCHEMAS} if native and cfg.tools else {}
    if msgs and msgs[0]["role"] == "system" and (native or not cfg.tools):  # never teach the text TOOL-line format
        msgs[0] = {**msgs[0], "content": native_tool_prompt(msgs[0]["content"], cfg.prompt_version,
                                                            "Native-tool wording" if cfg.tools else "No-tool wording")}
    for rnd in range(cfg.tool_rounds + 1):
        last = rnd == cfg.tool_rounds and rnd > 0
        if last:   # tool budget used up: the last call must answer
            msgs.append({"role": "user", "content": FINAL_ROUND_NOTE})
        # last round: no tools offered at all (gpt-oss still returned tool calls under tool_choice "none")
        r = await _create(name, srv, client, msgs, cfg, temperature, **({} if last else extra))
        msg = r.choices[0].message
        out = msg.content or ""
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
        trace.call_log.append({"model": name, "round": rnd, "last": last, "finish_reason": r.choices[0].finish_reason,
                            "tokens_out": r.usage.completion_tokens, "content_chars": len(out),
                            "reasoning_chars": len(reasoning), "tool_calls": len(msg.tool_calls or []),
                            "content_tail": out[-300:], "reasoning_tail": reasoning[-300:]})
        tok_in += r.usage.prompt_tokens
        tok_out += r.usage.completion_tokens
        if native:
            calls = msg.tool_calls or []
            if not calls or last:  # on the last round a stray tool call is not run; its text is the answer
                text_all += out
                break
            text_all += out + "\n"
            msgs.append({"role": "assistant", "content": out, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]})
            for c in calls:
                try:
                    arg = str(json.loads(c.function.arguments or "{}").get("input", ""))
                except ValueError:
                    arg = c.function.arguments or ""
                result = _run_tool(c.function.name, arg, messages)
                trace.tools.append({"name": c.function.name, "input": arg[:500], "output": str(result.get("output"))[:500],
                                    "ok": result["ok"], "via": "native"})
                text_all += f"TOOL {c.function.name}: {arg[:300]}\n"
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result)[:2000]})
            continue
        m = TOOL_LINE.search(out)
        if not m or parse_final(out)[0] is not None:
            text_all += out
            break
        tool, arg = m.group(1), m.group(2).strip()
        result = _run_tool(tool, arg, messages)
        trace.tools.append({"name": tool, "input": arg[:500], "output": str(result.get("output"))[:500], "ok": result["ok"]})
        upto = out[: m.end()]
        text_all += upto + "\n"
        msgs += [{"role": "assistant", "content": upto}, {"role": "user", "content": f"TOOL RESULT ({tool}): {json.dumps(result)[:2000]}"}]
    fa, conf = parse_final(text_all)
    return Sample(text=text_all, final_answer=fa, confidence=conf, tokens_in=tok_in, tokens_out=tok_out,
                  latency_s=round(time.time() - t0, 3))


def _text(content) -> str:
    return content if isinstance(content, str) else " ".join(p.get("text", "") for p in content if p.get("type") == "text")


# ------------------------------------------------------------------ vote

def vote(task_type: str, answers: list[str], public_tests: list[dict] | None = None) -> dict:
    cands = [a for a in answers if a]
    if not cands:
        return {"winner": None, "rule": "no parseable answer", "counts": {}}
    if task_type == "code" and public_tests:
        scored = [(int(tools.run_public_tests(a, public_tests)["output"].split("/")[0]), i, a) for i, a in enumerate(cands)]
        best = max(scored)
        return {"winner": best[2], "rule": "most public tests passed", "counts": {i: s for s, i, _ in scored}}
    if task_type == "math":
        groups: list[list[str]] = []
        for a in cands:
            for g in groups:
                if tools.sympy_check(a, g[0])["ok"]:
                    g.append(a)
                    break
            else:
                groups.append([a])
        best = max(groups, key=len)
        return {"winner": best[0], "rule": "majority by sympy equivalence", "counts": {g[0]: len(g) for g in groups}}
    norm = [re.sub(r"\s+", " ", a.strip().strip(".").upper() if len(a) <= 3 else a.strip().lower()) for a in cands]
    top, _ = Counter(norm).most_common(1)[0]
    return {"winner": cands[norm.index(top)], "rule": "majority of normalized answers", "counts": dict(Counter(norm))}


# ------------------------------------------------------------------ verifier (deterministic first)

_OPTION_LINE = re.compile(r"^\s*\(?([A-Z])[.)]\s", re.M)


def n_options(task: str, options: list[str] | None) -> int:
    """How many answer letters are valid: the item's options list, else the lettered lines in the question text
    (MMLU-Pro has ten, A to J), else four. Before 2026-11-20 this fell back to four whenever an item had no options
    list, so pool questions with options E to J had every E-J answer rejected."""
    if options:
        return len(options)
    letters = _OPTION_LINE.findall(task or "")
    run = 0
    while run < len(letters) and letters[run] == chr(65 + run):
        run += 1
    return run if run >= 2 else 4


def verify(task: str, task_type: str, answer: str | None, options: list[str] | None = None,
           public_tests: list[dict] | None = None) -> dict:
    checks = []
    if answer is None:
        return {"verdict": "reject", "checks": [{"name": "parse", "passed": False}], "reason": "no final answer"}
    if task_type == "math":
        r = tools.sympy_check(answer)
        checks.append({"name": "math_parses", "passed": r["ok"], "detail": r["detail"]})
    elif task_type in ("science_mc",) or options:
        ok = answer.strip().upper()[:1] in [chr(65 + i) for i in range(n_options(task, options))]
        checks.append({"name": "valid_option", "passed": ok, "detail": answer[:20]})
    elif task_type == "code" and public_tests:
        r = tools.run_public_tests(answer, public_tests)
        checks.append({"name": "public_tests", "passed": r["ok"], "detail": r["output"]})
    elif task_type == "instruction":
        r = tools.constraint_check(task, answer, loop_wrapped=True)
        checks.append({"name": "constraints", "passed": r["ok"], "detail": r["detail"]})
    passed = all(c["passed"] for c in checks)
    return {"verdict": "accept" if passed else "reject", "checks": checks,
            "reason": "all deterministic checks passed" if passed else "failed: " + ", ".join(c["name"] for c in checks if not c["passed"])}


# ------------------------------------------------------------------ one question

async def answer(item: dict, route: dict, cfg: SystemConfig, trace: Trace) -> Trace:
    """item: {item_id, task, task_type?, options?, public_tests?, retrieved?}; route: router output."""
    trace.router = route
    task_type = route.get("task_type", item.get("task_type", "general"))
    msgs = solver_messages(item["task"], task_type, cfg.prompt_version, item.get("retrieved"), item.get("images"))
    solvers = [s for s in route.get("models", cfg.solvers) if s in cfg.servers] or cfg.solvers
    temp = 0.0 if cfg.n_samples == 1 else cfg.temperature
    jobs = []
    for s in solvers:
        jobs += [(s, _solve_once(s, cfg.servers[s], msgs, cfg, temp, trace)) for _ in range(cfg.n_samples)]
    results = await asyncio.gather(*[j for _, j in jobs], return_exceptions=True)
    by_model: dict[str, list[Sample]] = {}
    for (s, _), r in zip(jobs, results):
        if isinstance(r, Exception):
            r = Sample(text=f"ERROR {type(r).__name__}: {r}"[:500], final_answer=None, confidence=None, tokens_in=0, tokens_out=0, latency_s=0)
        by_model.setdefault(s, []).append(r)
    for s, samples in by_model.items():
        trace.add_samples(s, cfg.servers[s].get("quant", "?"), samples)
    answers = [smp.final_answer for ss in by_model.values() for smp in ss]
    trace.vote = vote(task_type, answers, item.get("public_tests"))
    final = trace.vote["winner"]
    if cfg.verifier:
        v = verify(item["task"], task_type, final, item.get("options"), item.get("public_tests"))
        trace.verifier = {"version": cfg.verifier_version,
                          "attempts": [{"attempt": 1, "final_answer": final, **v}]}
        if v["verdict"] == "reject":  # verifier.v2: one retry, told it was wrong and why; keep the retry's answer
            s = solvers[0]
            srv = cfg.servers[s]
            msg = retry_message(cfg.verifier_version, final, v)
            # the model sees its own previous turn (the sample that gave `final`, else the first solver's), then the note
            prev = next((x for x in by_model.get(s, []) if x.final_answer == final), (by_model.get(s) or [None])[0])
            prev_text = (prev.text if prev and not prev.text.startswith("ERROR") else "")[-RETRY_PREV_CHARS:] or "(no output)"
            retry_msgs = msgs + [{"role": "assistant", "content": prev_text}, {"role": "user", "content": msg}]
            try:
                retry = await _solve_once(s, srv, retry_msgs, cfg, temp, trace)
            except Exception as e:  # noqa: BLE001 - a failed retry is logged; the first answer stands
                if type(e).__name__ == "CallBudget":
                    raise
                retry = Sample(text=f"ERROR {type(e).__name__}: {e}"[:500], final_answer=final, confidence=None,
                               tokens_in=0, tokens_out=0, latency_s=0)
            trace.add_samples(f"{s}:retry", srv.get("quant", "?"), [retry])
            v2 = verify(item["task"], task_type, retry.final_answer, item.get("options"), item.get("public_tests"))
            trace.verifier["attempts"].append({"attempt": 2, "final_answer": retry.final_answer, "retry_message": msg, **v2})
            final = retry.final_answer
        trace.verifier["verdict"] = trace.verifier["attempts"][-1]["verdict"]
    trace.final_answer = final
    return trace
