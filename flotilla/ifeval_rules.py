# Sources: ifeval, lm-eval, rlvr-ifeval, open-instruct (docs/reference/REFERENCES.md)
"""Instruction rules on IFEval's standard (design: docs/design/forced_tools_self_check_design.md).

Two separate jobs:
- constraint_check v2 (a tool and verifier v2's instruction check): Qwen lists the question's rules as IFEval
  instruction IDs with arguments (`prompts/ifeval_rules.v1.md`, the question alone), the list is validated against the
  official checkers' registry, and the official checkers (`lm_eval.tasks.ifeval`) test a draft.
- grading instruction questions (labels): each RLVR-IFeval question's own ground_truth rule, checked by the functions
  that define it (open-instruct's if_functions, vendored), not by Qwen's list and not by the old regex.
The loop wraps every answer in its own JSON block, so a JSON-format rule is met by the loop (as before, 2026-11-20).
"""
import json
import re

RULES_JSON = re.compile(r"\{\s*\"rules\"\s*:.*\}", re.S)
JSON_RULES = ("detectable_format:json_format",)
JSON_FUNCS = ("validate_json_format",)


def registry() -> dict:
    from lm_eval.tasks.ifeval.instructions_registry import INSTRUCTION_DICT
    return INSTRUCTION_DICT


def rules_messages(question: str, version: str = "v1") -> list[dict]:
    from flotilla.system import PROMPTS, _section
    md = (PROMPTS / f"ifeval_rules.{version}.md").read_text()
    return [{"role": "system", "content": _section(md, "System")},
            {"role": "user", "content": _section(md, "User").replace("{question}", question)}]


def parse_rules(text: str, reg: dict | None = None) -> dict:
    """The last {"rules": [...]} block of a reply, each rule kept only if its ID is in the registry and its arguments
    build that checker. Returns {"rules": [...], "dropped": [...], "parsed": bool}."""
    import inspect
    reg = reg or registry()
    blobs = RULES_JSON.findall(text or "")
    data = None
    for b in reversed(blobs):
        try:
            data = json.loads(b[b.index("{"):])
            break
        except ValueError:
            # the greedy match may run past the block; cut at each closing brace from the end
            for k in range(len(b), 0, -1):
                if b[k - 1] == "}":
                    try:
                        data = json.loads(b[:k])
                        break
                    except ValueError:
                        continue
            if data is not None:
                break
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return {"rules": [], "dropped": [], "parsed": False}
    keep, dropped = [], []
    for r in data["rules"]:
        iid = r.get("instruction_id") if isinstance(r, dict) else None
        kw = r.get("kwargs") or {} if isinstance(r, dict) else {}
        if iid not in reg or not isinstance(kw, dict):
            dropped.append({"rule": r, "why": "unknown instruction_id"})
            continue
        allowed = set(inspect.signature(reg[iid].build_description).parameters) - {"self"}
        kw = {k: v for k, v in kw.items() if k in allowed and v is not None}
        try:
            reg[iid](iid).build_description(**kw)
        except Exception as e:  # noqa: BLE001 - bad arguments drop the rule, logged
            dropped.append({"rule": r, "why": f"{type(e).__name__}: {e}"[:200]})
            continue
        keep.append({"instruction_id": iid, "kwargs": kw})
    return {"rules": keep, "dropped": dropped, "parsed": True}


def check_rules(rules: list[dict], answer: str, question: str = "", loop_wrapped: bool = True,
                reg: dict | None = None) -> dict:
    """The official checkers on one draft. Returns {"ok", "output": [{"instruction_id", "passed"}], "detail"}."""
    reg = reg or registry()
    out = []
    for r in rules:
        iid = r["instruction_id"]
        if loop_wrapped and iid in JSON_RULES:
            out.append({"instruction_id": iid, "passed": True, "note": "met by the loop's JSON block"})
            continue
        chk = reg[iid](iid)
        chk.build_description(**r.get("kwargs", {}))
        if "prompt" in (chk.get_instruction_args_keys() or []):
            chk.build_description(prompt=question)
        try:
            ok = bool(answer and answer.strip() and chk.check_following(answer))
        except Exception:  # noqa: BLE001 - a checker crash is a fail, never a pass
            ok = False
        out.append({"instruction_id": iid, "passed": ok})
    return {"ok": all(x["passed"] for x in out), "output": out,
            "detail": f"{sum(x['passed'] for x in out)}/{len(out)} rules met"}


async def list_rules(name: str, srv: dict, question: str, cfg, trace) -> dict:
    """One Qwen call (thinking off, temperature 0) lists the question's rules; cached on the trace per question."""
    from flotilla import system
    from flotilla.trace import Sample
    import time
    if question in trace.ifeval_rules:
        return trace.ifeval_rules[question]
    srv = {**srv, "request": {**srv.get("request", {}), "extra_body": {
        **srv.get("request", {}).get("extra_body", {}), "chat_template_kwargs": {"enable_thinking": False}}},
        "max_tokens": 1024}
    t0, out, ti, to, err = time.time(), "", 0, 0, None
    try:
        r = await system._create(f"{name}:rules", srv, system.client_for(srv), rules_messages(question), cfg, 0.0)
        out = r.choices[0].message.content or ""
        ti, to = r.usage.prompt_tokens, r.usage.completion_tokens
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "CallBudget":
            raise
        err = f"{type(e).__name__}: {e}"[:300]
    trace.add_samples(f"{name}:rules", srv.get("quant", "?"), [Sample(text=out or f"ERROR {err}", final_answer=None,
                      confidence=None, tokens_in=ti, tokens_out=to, latency_s=round(time.time() - t0, 3))])
    res = {**parse_rules(out), "error": err, "reply": out[-500:]}
    trace.ifeval_rules[question] = res
    return res


def grade_ground_truth(answer: str | None, ground_truth: str | dict) -> bool:
    """RLVR-IFeval's own rule on an answer: the function named in ground_truth with its non-null arguments, as
    open-instruct calls it. A JSON-format rule is met by the loop's JSON block."""
    from flotilla.vendor.open_instruct_if_functions import IF_FUNCTIONS_MAP
    gt = json.loads(ground_truth) if isinstance(ground_truth, str) else dict(ground_truth)
    func = gt.pop("func_name")
    if func in JSON_FUNCS:
        return bool(answer and answer.strip())
    if not answer or not answer.strip():
        return False
    fn = IF_FUNCTIONS_MAP[func]
    import inspect
    args = {k: v for k, v in gt.items() if v is not None and k in inspect.signature(fn).parameters}
    if func == "validate_choice" and isinstance(args.get("options"), str):
        # RLVR-IFeval stores the options as one string ("a), b), c), d)", "I know or I don't know", "yes/no/maybe");
        # validate_choice iterates its options, so a string would test single characters and pass almost anything.
        # Our one deviation from open-instruct (2026-11-22): split the string into its options first.
        args["options"] = split_options(args["options"])
    try:
        return bool(fn(answer, **args))
    except Exception:  # noqa: BLE001 - a checker error is a fail
        return False


def split_options(text: str) -> list[str]:
    """'a), b), c), d)' -> ['a)', 'b)', 'c)', 'd)']; "I know or I don't know" -> two; 'yes/no/maybe' -> three."""
    return [o.strip() for o in re.split(r",\s*|\s+or\s+|/", text) if o.strip()]


def attach_ground_truth(items: list[dict], parquet: str) -> int:
    """Adds RLVR-IFeval's ground_truth to pool items rlvrif-<row> (the pool kept only the rule's text). Returns how
    many items got one."""
    import pyarrow.parquet as pq
    gts = pq.read_table(parquet, columns=["ground_truth"]).column("ground_truth").to_pylist()
    n = 0
    for it in items:
        iid = it.get("item_id") or it.get("id") or ""
        if iid.startswith("rlvrif-"):
            it["ground_truth"] = gts[int(iid.split("-", 1)[1])]
            n += 1
    return n
