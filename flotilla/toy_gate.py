# Sources: retool, critic, ifeval, open-instruct (docs/reference/REFERENCES.md)
"""Toy gate for the forced-tool and self-check routes (S169; design: docs/design/forced_tools_self_check_design.md).

    python -m flotilla.toy_gate --items experiments/test-10-forced-tools/toy/items.jsonl --url URL --model MODEL --out DIR
Runs every toy question through its route's config (configs/systems/qwen_strategy_<route>.json) on the real Qwen,
records every request Qwen got (messages, tools offered, tool choice) and every reply, and checks the gate:
  - every question has a parsed, non-empty final answer;
  - on a forced route, the first call called the forced tool;
  - on Forced Rules, the rule listing parsed;
  - on Self-Check, at least one check ran a program.
Known answers are graded and reported, but a wrong answer does not stop the gate. The first gate failure stops the run
(the remaining questions are not run) and the exit code is 1. DIR gets traces.jsonl, gate.json and one full trace per
route as <route>.md.
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from flotilla import system
from flotilla.trace import Trace

FORCED = {"forced_code": "python_exec", "forced_sympy": "sympy", "forced_rules": "constraint_check"}


def number_in(answer: str, value: float, tol: float = 1e-9) -> bool:
    nums = re.findall(r"-?\d[\d,]*\.?\d*(?:/\d+)?", answer or "")
    for n in nums:
        try:
            x = eval(n.replace(",", ""), {}, {}) if "/" in n else float(n.replace(",", ""))
        except Exception:  # noqa: BLE001
            continue
        if abs(x - value) <= max(tol, 1e-9 * abs(value)):
            return True
    return False


def grade(it: dict, answer: str | None) -> bool | None:
    c = it.get("check") or {}
    if answer is None:
        return False
    if c.get("kind") == "number":
        return number_in(answer, c["value"], c.get("tol", 1e-9))
    if c.get("kind") == "contains":
        return c["value"] in answer.lower()
    if c.get("kind") == "letter":
        return answer.strip().upper()[:1] == c["value"]
    if c.get("kind") == "tests":
        from flotilla import tools
        from flotilla.scoring import strip_fence
        return tools.run_public_tests(strip_fence(answer), c["tests"])["ok"]
    if c.get("kind") == "ground_truth":
        from flotilla.ifeval_rules import grade_ground_truth
        return grade_ground_truth(answer, it["ground_truth"])
    return None


def gate_problems(route: str, tr: dict, requests: list[dict]) -> list[str]:
    p = []
    fa = tr.get("final_answer")
    if fa is None or not str(fa).strip() or str(fa) == "None":
        p.append("no parsed final answer (parse failure or empty answer)")
    if route in FORCED:
        first = next((r for r in requests if r["name"] == "q"), None)
        if not first or (first["extra"].get("tool_choice") or {}).get("function", {}).get("name") != FORCED[route]:
            p.append("the first call did not set the named tool choice")
        if not tr["tools"] or tr["tools"][0]["name"] != FORCED[route]:
            p.append(f"the first tool call was not {FORCED[route]}")
    if route == "forced_rules" and not any(v.get("parsed") for v in tr.get("ifeval_rules", {}).values()):
        p.append("the rule listing did not parse")
    if route == "self_check" and not any(r.get("program") for r in tr.get("self_check", [])):
        p.append("no check program ran")
    return p


def dump(route: str, it: dict, tr: dict, requests: list[dict]) -> str:
    L = [f"# Toy gate trace: {route}, {it['item_id']}", "", f"**Task:** {it['task']}", "",
         f"**Final answer:** `{tr.get('final_answer')}`", ""]
    for k, r in enumerate(requests, 1):
        L += [f"## Call {k}: {r['name']} (temperature {r['temperature']})", ""]
        ex = r["extra"]
        L.append(f"Tools offered: {[t['function']['name'] for t in ex.get('tools', [])] or 'none'}; tool choice: "
                 f"{json.dumps(ex.get('tool_choice')) if ex.get('tool_choice') else 'auto/none'}; thinking: "
                 f"{(r['srv'].get('request', {}).get('extra_body', {}).get('chat_template_kwargs') or {}).get('enable_thinking', 'on')}")
        L.append("")
        for m in r["msgs"]:
            body = m.get("content") or ""
            L += [f"**{m['role']}**" + (" (with its reasoning)" if m.get("reasoning") else "") + ":", "", "```",
                  str(body)[:6000], "```"]
            if m.get("tool_calls"):
                L += ["tool calls: `" + json.dumps(m["tool_calls"])[:1500] + "`"]
            L.append("")
        rep = r["reply"]
        L += ["**Qwen replied:**", ""]
        if rep.get("reasoning"):
            L += ["reasoning:", "```", rep["reasoning"][-6000:], "```"]
        L += ["content:", "```", (rep.get("content") or "")[-6000:], "```"]
        if rep.get("tool_calls"):
            L += ["tool calls: `" + json.dumps(rep["tool_calls"])[:3000] + "`"]
        L += [f"finish: {rep.get('finish')}", ""]
    L += ["## Tool results (as run)", ""]
    for t in tr["tools"]:
        L += [f"- {t['name']} ({t.get('via', '')}) ok={t['ok']}", "  ```", "  input: " + str(t["input"])[:1500],
              "  output: " + str(t["output"])[:1500], "  error: " + str(t.get("detail", ""))[:1500], "  ```"]
    if tr.get("ifeval_rules"):
        L += ["", "## Rules listed (constraint_check v2)", "", "```", json.dumps(tr["ifeval_rules"], indent=1)[:4000], "```"]
    if tr.get("self_check"):
        L += ["", "## Self-check rounds", "", "```", json.dumps(tr["self_check"], indent=1)[:8000], "```"]
    return "\n".join(L) + "\n"


async def run(items: list[dict], url: str, model: str, out: Path) -> int:
    requests: list[dict] = []
    real = system._create

    async def logged(name, srv, client, msgs, cfg, temperature, **extra):
        r = await real(name, srv, client, msgs, cfg, temperature, **extra)
        m = r.choices[0].message
        requests.append({"name": name, "srv": srv, "temperature": temperature, "extra": extra,
                         "msgs": [dict(x) for x in msgs],
                         "reply": {"content": m.content, "finish": r.choices[0].finish_reason,
                                   "reasoning": getattr(m, "reasoning_content", None) or getattr(m, "reasoning", None),
                                   "tool_calls": [{"name": c.function.name, "arguments": c.function.arguments}
                                                  for c in (m.tool_calls or [])]}})
        return r
    system._create = logged
    report, dumped = [], set()
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "traces.jsonl", "w") as tf:
        for it in items:
            route = it["route"]
            conf = json.load(open(Path(__file__).resolve().parents[1] / f"configs/systems/qwen_strategy_{route}.json"))
            srv_name = next(iter(conf["servers"]))
            conf["servers"] = {"q": {**conf["servers"][srv_name], "url": url, "model": model}}
            conf["solvers"] = ["q"]
            cfg = system.SystemConfig(**{k: v for k, v in conf.items() if k not in ("name", "notes")})
            tr = Trace(run_id="toy", protocol_version="toy", prompt_versions={}, benchmark="toy", item_id=it["item_id"],
                       split="toy")
            requests.clear()
            await system.answer({k: v for k, v in it.items() if k not in ("route", "check")}, {}, cfg, tr)
            d = tr.finish()
            problems = gate_problems(route, d, requests)
            row = {"route": route, "item_id": it["item_id"], "final_answer": d["final_answer"],
                   "right": grade(it, d["final_answer"]), "calls": len(requests), "tool_calls": len(d["tools"]),
                   "problems": problems}
            if route == "forced_rules" and it.get("ground_truth"):
                row["rules_listed"] = [r["instruction_id"] for v in d["ifeval_rules"].values() for r in v["rules"]]
                row["ground_truth_rule"] = json.loads(it["ground_truth"])["func_name"]
            report.append(row)
            tf.write(json.dumps({**d, "requests": requests}, default=str) + "\n")
            print(json.dumps(row), flush=True)
            if route not in dumped or problems:
                (out / f"{route}{'' if route not in dumped else '_' + it['item_id']}.md").write_text(dump(route, it, d, requests))
                dumped.add(route)
            if problems:
                (out / "gate.json").write_text(json.dumps({"passed": False, "stopped_at": row, "rows": report}, indent=1))
                print(f"GATE STOPPED at {it['item_id']}: {problems}", flush=True)
                return 1
    (out / "gate.json").write_text(json.dumps({"passed": True, "rows": report}, indent=1))
    print("GATE PASSED", flush=True)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = [json.loads(line) for line in open(a.items) if line.strip()]
    sys.exit(asyncio.run(run(items, a.url, a.model, Path(a.out))))


if __name__ == "__main__":
    main()
