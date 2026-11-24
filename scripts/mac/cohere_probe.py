"""Find which part of a request Cohere's compatibility API rejects. One call per variant; prints outcome and where
the text lands. The key is read from the environment and never printed."""
import json, os, sys
sys.path.insert(0, "/Users/mk/flotilla")
from openai import OpenAI
from flotilla.core.system import solver_messages, parse_final
item = json.loads(open("/Users/mk/flotilla-data/smalltest/gsm8k.jsonl").readline())
c = OpenAI(base_url="https://api.cohere.ai/compatibility/v1", api_key=os.environ["COHERE_API_KEY"], max_retries=0, timeout=600)
M = "command-a-plus-05-2026"
base = solver_messages(item["task"], "math", "v1")
dev = [{"role": "developer", "content": base[0]["content"]}, base[1]]
no_tool = [{"role": "system", "content": "\n".join(l for l in base[0]["content"].splitlines() if "TOOL" not in l and "tool" not in l)}, base[1]]
simple = [{"role": "user", "content": "What is 17 + 25? End with a JSON block {\"final_answer\": \"...\", \"confidence\": 0.9}."}]
variants = {
    "simple_user_only_thinking": dict(messages=simple, reasoning_effort="high", max_tokens=4096, temperature=0.0),
    "solver_no_thinking": dict(messages=base, reasoning_effort="none", max_tokens=8192, temperature=0.0),
    "solver_developer_role_thinking": dict(messages=dev, reasoning_effort="high", max_tokens=32768, temperature=0.0),
    "solver_without_tool_lines_thinking": dict(messages=no_tool, reasoning_effort="high", max_tokens=32768, temperature=0.0),
}
only = sys.argv[1:] or list(variants)
for name in only:
    try:
        r = c.chat.completions.create(model=M, **variants[name])
        d = r.model_dump(); msg = d["choices"][0]["message"]
        print(f"[{name}] OK finish={d['choices'][0].get('finish_reason')} usage={d.get('usage')}")
        print("   fields:", {k: (type(v).__name__, len(v) if isinstance(v, (str, list)) else v) for k, v in msg.items() if v is not None})
        print("   content tail:", repr((msg.get("content") or "")[-400:]))
        print("   parsed:", parse_final(msg.get("content") or ""), "gold:", item["gold"])
    except Exception as e:
        print(f"[{name}] FAIL {type(e).__name__}: {str(e)[:200]}")
