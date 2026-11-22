# Sources: usc, self-consistency, openai-sdk (docs/reference/REFERENCES.md)
"""Flotilla orchestration (docs/reference/PROMPTS.md flow): router -> solvers (N samples, tool loop) -> vote ->
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
from dataclasses import replace, dataclass, field
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
    llm_verify: bool = False               # F33/F34: verifier.v2's LLM check where no exact check exists (free text)
    llm_verify_max_tokens: int = 1024
    tie_rule: str = "first"                # free-text vote with no two answers matching: "first" sample, or "usc" (F36)
    forced_tool: str | None = None         # F37-F39: the first call must call this tool (tool_choice by name)
    constraint_v2: bool = False            # constraint_check and the instruction check on IFEval's official checkers
    self_check_rounds: int = 0             # F40: up to this many code check-revise rounds after the answer
    keep_reasoning: bool = True            # send each round's reasoning back with the assistant turn (2026-11-22 fix)
    usc_max_tokens: int = 256
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


# A task holding a chat history: LongMemEval's history prompt (base routes) or GRAFT's memory block (Memory routes).
HISTORY_MARKS = ("History Chats:", "MEMORY (facts that GRAFT recalled")


def question_only(task: str) -> str:
    """The task's own question. constraint_check reads its constraints from it, and the USC tie rule shows it. On a
    task holding a chat history only the question
    counts (from its last "Question: " line to the next blank line): instructions in old sessions ("add a P.S.", "at
    least 500 words") are not this task's (2026-11-22: they failed 166 of 419 memory checks on Vote+Tools). A history
    with no question line gives no constraints."""
    if not any(m in task for m in HISTORY_MARKS):
        return task
    i = task.rfind("Question: ")
    return task[i:].split("\n\n")[0] if i >= 0 else ""


def _run_tool(tool: str, arg: str, messages: list[dict]) -> dict:
    return {"sympy": lambda a: tools.sympy_check(a), "python_exec": lambda a: tools.python_exec(a),
            "constraint_check": lambda a: tools.constraint_check(question_only(_text(messages[-1]["content"])), a),
            "ocr": lambda a: {"ok": False, "output": None, "detail": "ocr tool not enabled"}}.get(
        tool, lambda a: {"ok": False, "output": None, "detail": f"unknown tool {tool}"})(arg)


def forced_tool_note(tool: str, version: str = "v1") -> str:
    """The forced route's wording for its tool, from prompts/forced_tool.<version>.md."""
    return _section((PROMPTS / f"forced_tool.{version}.md").read_text(), tool)


async def _tool_result(tool: str, arg: str, messages: list[dict], name: str, srv: dict, cfg: SystemConfig,
                       trace: Trace) -> dict:
    """One tool call. constraint_check v2 first lists the question's rules (once per question, cached on the trace)
    and runs IFEval's official checkers on the draft; every other tool as before."""
    if tool == "constraint_check" and cfg.constraint_v2:
        from flotilla import ifeval_rules
        q = question_only(_text(messages[-1]["content"]))
        rules = await ifeval_rules.list_rules(name, srv, q, cfg, trace)
        return ifeval_rules.check_rules(rules["rules"], arg, q)
    return _run_tool(tool, arg, messages)


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
    forced = cfg.forced_tool if (native and cfg.tools and cfg.forced_tool) else None
    if forced and msgs and msgs[0]["role"] == "system":
        msgs[0] = {**msgs[0], "content": msgs[0]["content"] + "\n" + forced_tool_note(forced)}
    for rnd in range(cfg.tool_rounds + 1):
        last = rnd == cfg.tool_rounds and rnd > 0
        if last:   # tool budget used up: the last call must answer
            msgs.append({"role": "user", "content": FINAL_ROUND_NOTE})
        # last round: no tools offered at all (gpt-oss still returned tool calls under tool_choice "none")
        kw = {} if last else dict(extra)
        if forced and rnd == 0:   # the forced route's first call must call its tool (named, stricter than "required")
            kw["tool_choice"] = {"type": "function", "function": {"name": forced}}
        r = await _create(name, srv, client, msgs, cfg, temperature, **kw)
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
            turn = {"role": "assistant", "content": out, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]}
            if cfg.keep_reasoning and reasoning:   # Qwen's template keeps it after the last user turn (interleaved thinking)
                turn["reasoning"] = reasoning
            msgs.append(turn)
            for c in calls:
                try:
                    arg = str(json.loads(c.function.arguments or "{}").get("input", ""))
                except ValueError:
                    arg = c.function.arguments or ""
                result = await _tool_result(c.function.name, arg, messages, name, srv, cfg, trace)
                trace.tools.append({"name": c.function.name, "input": arg[:500], "output": str(result.get("output"))[:500],
                                    "ok": result["ok"], "detail": str(result.get("detail") or "")[:1000], "via": "native"})
                text_all += f"TOOL {c.function.name}: {arg[:300]}\n"
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result)[:2000]})
            continue
        m = TOOL_LINE.search(out)
        if not m or parse_final(out)[0] is not None:
            text_all += out
            break
        tool, arg = m.group(1), m.group(2).strip()
        result = await _tool_result(tool, arg, messages, name, srv, cfg, trace)
        trace.tools.append({"name": tool, "input": arg[:500], "output": str(result.get("output"))[:500], "ok": result["ok"],
                            "detail": str(result.get("detail") or "")[:1000]})
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


USC_PICK = re.compile(r"most consistent response is\s*\**\s*Response\s*(\d+)", re.I)


def is_free_text_tie(vote_rec: dict) -> bool:
    """The free-text vote found no two matching answers among two or more (the old rule then took sample 0)."""
    c = vote_rec.get("counts") or {}
    return vote_rec.get("rule") == "majority of normalized answers" and len(c) >= 2 and max(c.values()) == 1


def usc_messages(question: str, answers: list[str]) -> list[dict]:
    md = (PROMPTS / "vote_usc.v1.md").read_text()
    resp = "\n\n".join(f"Response {i}: {a}" for i, a in enumerate(answers, 1))
    return [{"role": "system", "content": _section(md, "System")},
            {"role": "user", "content": _section(md, "User").replace("{question}", question).replace("{responses}", resp)}]


def parse_usc(text: str, n: int) -> int | None:
    """0-based index of the picked response, or None when the reply names none in range."""
    m = USC_PICK.search(text or "")
    k = int(m.group(1)) if m else 0
    return k - 1 if 1 <= k <= n else None


async def usc_pick(name: str, srv: dict, question: str, answers: list[str], cfg: SystemConfig, trace: Trace) -> dict:
    """F36: one Qwen call (thinking off, temperature 0) picks the answer most others agree with. A failed call or an
    unparseable reply keeps the first answer (the old rule); the record says why."""
    srv = {**srv, "request": {**srv.get("request", {}), "extra_body": {
        **srv.get("request", {}).get("extra_body", {}), "chat_template_kwargs": {"enable_thinking": False}}},
        "max_tokens": cfg.usc_max_tokens}
    t0, out, tok_in, tok_out, err = time.time(), "", 0, 0, None
    try:
        r = await _create(f"{name}:usc", srv, client_for(srv), usc_messages(question, answers), cfg, 0.0)
        out = r.choices[0].message.content or ""
        tok_in, tok_out = r.usage.prompt_tokens, r.usage.completion_tokens
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "CallBudget":
            raise
        err = f"{type(e).__name__}: {e}"[:300]
    lat = round(time.time() - t0, 3)
    trace.add_samples(f"{name}:usc", srv.get("quant", "?"), [Sample(text=out or f"ERROR {err}", final_answer=None,
                      confidence=None, tokens_in=tok_in, tokens_out=tok_out, latency_s=lat)])
    k = parse_usc(out, len(answers))
    return {"index": 0 if k is None else k, "parsed": k is not None, "error": err, "reply": out[-300:],
            "tokens_in": tok_in, "tokens_out": tok_out, "latency_s": lat}


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
           public_tests: list[dict] | None = None, rules: list[dict] | None = None) -> dict:
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
    elif task_type == "instruction" and rules is not None:   # constraint_check v2: IFEval's official checkers
        from flotilla import ifeval_rules
        r = ifeval_rules.check_rules(rules, answer, question_only(task))
        checks.append({"name": "constraints", "passed": r["ok"], "detail": r["detail"]})
    elif task_type == "instruction":
        r = tools.constraint_check(task, answer, loop_wrapped=True)
        checks.append({"name": "constraints", "passed": r["ok"], "detail": r["detail"]})
    passed = all(c["passed"] for c in checks)
    return {"verdict": "accept" if passed else "reject", "checks": checks,
            "reason": "all deterministic checks passed" if passed else "failed: " + ", ".join(c["name"] for c in checks if not c["passed"])}


# ------------------------------------------------------------------ one question

LLM_CHECK_JSON = re.compile(r"\{[^{}]*\"verdict\"[^{}]*\}", re.S)


def llm_check_messages(version: str, task_text: str, final_answer: str) -> list[dict]:
    """verifier.<version>'s LLM check: system and user messages, filled from the prompt file."""
    md = (PROMPTS / f"verifier.{version}.md").read_text()
    m = re.search(r"^## LLM check.*?^### System\s*\n(.*?)^### User\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    if not m:
        raise ValueError(f"verifier.{version}.md has no LLM check section")
    system, user = m.group(1).strip(), m.group(2).strip()
    return [{"role": "system", "content": system},
            {"role": "user", "content": user.replace("{task_text}", task_text).replace("{final_answer}", final_answer)}]


def parse_llm_verdict(text: str) -> dict | None:
    """The last JSON object with a verdict of accept or reject, else None."""
    for blob in reversed(LLM_CHECK_JSON.findall(text or "")):
        try:
            d = json.loads(blob)
        except ValueError:
            continue
        if str(d.get("verdict", "")).lower() in ("accept", "reject"):
            return {"verdict": str(d["verdict"]).lower(), "reason": str(d.get("reason", ""))[:500]}
    return None


async def llm_check(name: str, srv: dict, task_text: str, final_answer: str, cfg: SystemConfig, trace: Trace) -> dict:
    """One checker call on the solver's server, thinking off, temperature 0. A checker that fails or gives no
    parseable verdict accepts (the answer stands); the check records why."""
    srv = {**srv, "request": {**srv.get("request", {}), "extra_body": {
        **srv.get("request", {}).get("extra_body", {}), "chat_template_kwargs": {"enable_thinking": False}}},
        "max_tokens": cfg.llm_verify_max_tokens}
    t0, out, tok_in, tok_out = time.time(), "", 0, 0
    try:
        r = await _create(f"{name}:llm_check", srv, client_for(srv),
                          llm_check_messages(cfg.verifier_version, task_text, final_answer), cfg, 0.0)
        out = r.choices[0].message.content or ""
        tok_in, tok_out = r.usage.prompt_tokens, r.usage.completion_tokens
        err = None
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "CallBudget":
            raise
        err = f"{type(e).__name__}: {e}"[:300]
    lat = round(time.time() - t0, 3)
    trace.add_samples(f"{name}:llm_check", srv.get("quant", "?"),
                      [Sample(text=out or f"ERROR {err}", final_answer=None, confidence=None, tokens_in=tok_in,
                              tokens_out=tok_out, latency_s=lat)])
    v = parse_llm_verdict(out)
    if v is None:
        return {"name": "llm_check", "passed": True, "detail": f"no verdict ({err or 'unparseable reply'}); accepted",
                "reply": out[-500:], "latency_s": lat, "tokens_in": tok_in, "tokens_out": tok_out}
    return {"name": "llm_check", "passed": v["verdict"] == "accept", "detail": v["reason"], "reply": out[-500:],
            "latency_s": lat, "tokens_in": tok_in, "tokens_out": tok_out}


CHECK_LINE = re.compile(r"^CHECK (PASS|FAIL)\b.*$", re.M)


def self_check_messages(kind: str, version: str = "v1", **fill) -> list[dict]:
    md = (PROMPTS / f"self_check.{version}.md").read_text()
    text = _section(md, {"check": "Check user", "revise": "Revise user"}[kind])
    for k, v in fill.items():
        text = text.replace("{" + k + "}", str(v))
    return ([{"role": "system", "content": _section(md, "Check system")}] if kind == "check" else []) + \
        [{"role": "user", "content": text}]


def check_verdict(stdout: str | None) -> bool:
    """The check passes only when its last CHECK line says PASS (an error, a timeout or no line is a fail)."""
    lines = CHECK_LINE.findall(stdout or "")
    return bool(lines) and lines[-1] == "PASS"


async def self_check(name: str, srv: dict, task: str, task_type: str, answer: str, cfg: SystemConfig,
                     trace: Trace) -> str:
    """F40 (CRITIC-style): up to cfg.self_check_rounds rounds. Check: Qwen (thinking off, temperature 0) must call
    python_exec with a program that checks the answer and prints CHECK PASS or CHECK FAIL; the program runs here.
    A pass stops. Otherwise revise: the route's own solver sees the program and its full output (errors included) and
    answers again; an unchanged answer stops (CRITIC's rule). Every call is in compute; trace.self_check records each
    round."""
    q = question_only(task)
    chk_srv = {**srv, "request": {**srv.get("request", {}), "extra_body": {
        **srv.get("request", {}).get("extra_body", {}), "chat_template_kwargs": {"enable_thinking": False}}}}
    py_tool = [t for t in TOOL_SCHEMAS if t["function"]["name"] == "python_exec"]
    for k in range(cfg.self_check_rounds):
        t0, out, prog, err = time.time(), "", "", None
        ti = to = 0
        try:
            r = await _create(f"{name}:check", chk_srv, client_for(chk_srv),
                              self_check_messages("check", question=q, answer=answer), cfg, 0.0, tools=py_tool,
                              tool_choice={"type": "function", "function": {"name": "python_exec"}})
            msg = r.choices[0].message
            out = msg.content or ""
            ti, to = r.usage.prompt_tokens, r.usage.completion_tokens
            calls = msg.tool_calls or []
            if calls:
                try:
                    prog = str(json.loads(calls[0].function.arguments or "{}").get("input", ""))
                except ValueError:
                    prog = calls[0].function.arguments or ""
        except Exception as e:  # noqa: BLE001
            if type(e).__name__ == "CallBudget":
                raise
            err = f"{type(e).__name__}: {e}"[:300]
        trace.add_samples(f"{name}:check", srv.get("quant", "?"), [Sample(text=out or prog or f"ERROR {err}",
                          final_answer=None, confidence=None, tokens_in=ti, tokens_out=to,
                          latency_s=round(time.time() - t0, 3))])
        res = tools.python_exec(prog) if prog else {"ok": False, "output": None, "detail": err or "no check program"}
        shown = ((res.get("output") or "") + ("\n" + res["detail"] if res.get("detail") else "")).strip()
        passed = bool(res.get("ok")) and check_verdict(res.get("output"))
        trace.tools.append({"name": "python_exec", "input": prog[:500], "output": str(res.get("output"))[:500],
                            "ok": res["ok"], "detail": str(res.get("detail") or "")[:1000], "via": "self_check"})
        rec = {"round": k + 1, "answer": answer, "program": prog[:4000], "output": shown[:4000], "passed": passed}
        if passed:
            trace.self_check.append(rec)
            break
        msgs = solver_messages(task, task_type, cfg.prompt_version)[:1] + self_check_messages(
            "revise", question=q, answer=answer, program=prog or "(no program)", output=shown or "(no output)")
        rev = await _solve_once(name, srv, msgs, replace(cfg, tools=False), 0.0, trace)
        trace.add_samples(f"{name}:revise", srv.get("quant", "?"), [rev])
        rec["revised"] = rev.final_answer
        trace.self_check.append(rec)
        if rev.final_answer is None or _norm_ans(rev.final_answer) == _norm_ans(answer):
            break
        answer = rev.final_answer
    return answer


def _norm_ans(a: str | None) -> str:
    return re.sub(r"\s+", " ", str(a or "").strip().lower()).strip(" .")


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
    if cfg.tie_rule == "usc" and is_free_text_tie(trace.vote):
        cands = [a for a in answers if a]
        u = await usc_pick(solvers[0], cfg.servers[solvers[0]], question_only(_text(msgs[-1]["content"])), cands, cfg, trace)
        trace.vote = {**trace.vote, "winner": cands[u["index"]], "rule": "USC tie rule (no two answers match)", "usc": u}
    final = trace.vote["winner"]
    if cfg.self_check_rounds and final is not None:   # F40: code check-revise rounds (CRITIC-style)
        final = await self_check(solvers[0], cfg.servers[solvers[0]], item["task"], task_type, final, cfg, trace)
    rules = None
    if cfg.constraint_v2 and task_type == "instruction":
        from flotilla import ifeval_rules
        rules = (await ifeval_rules.list_rules(solvers[0], cfg.servers[solvers[0]], question_only(item["task"]),
                                               cfg, trace))["rules"]
    if cfg.verifier:
        v = verify(item["task"], task_type, final, item.get("options"), item.get("public_tests"), rules)
        if cfg.llm_verify and v["verdict"] == "accept" and not v["checks"]:  # no exact check for this task type
            c = await llm_check(solvers[0], cfg.servers[solvers[0]], _text(msgs[-1]["content"]), final, cfg, trace)
            v = {"verdict": "accept" if c["passed"] else "reject", "checks": [c],
                 "reason": "LLM check passed" if c["passed"] else c["detail"] or "rejected by the LLM check"}
        trace.verifier = {"version": cfg.verifier_version, "llm_verify": cfg.llm_verify,
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
            v2 = verify(item["task"], task_type, retry.final_answer, item.get("options"), item.get("public_tests"), rules)
            trace.verifier["attempts"].append({"attempt": 2, "final_answer": retry.final_answer, "retry_message": msg, **v2})
            final = retry.final_answer
        trace.verifier["verdict"] = trace.verifier["attempts"][-1]["verdict"]
    trace.final_answer = final
    return trace
