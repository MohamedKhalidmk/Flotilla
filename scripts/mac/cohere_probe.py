"""One call to Cohere's compatibility API with the Flotilla solver prompt; prints where the text lands (no key printed)."""
import json, os, sys
sys.path.insert(0, "/Users/mk/flotilla")
from openai import OpenAI
from flotilla.system import solver_messages, parse_final
item = json.loads(open("/Users/mk/flotilla-data/smalltest/gsm8k.jsonl").readline())
c = OpenAI(base_url="https://api.cohere.ai/compatibility/v1", api_key=os.environ["COHERE_API_KEY"], max_retries=0, timeout=600)
r = c.chat.completions.create(model="command-a-plus-05-2026", messages=solver_messages(item["task"], "math", "v1"),
                              temperature=0.0, max_tokens=32768, reasoning_effort="high")
d = r.model_dump()
msg = d["choices"][0]["message"]
print("finish_reason:", d["choices"][0].get("finish_reason"), "| usage:", d.get("usage"))
print("message fields:", {k: (type(v).__name__, len(v) if isinstance(v, (str, list)) else v) for k, v in msg.items()})
print("content (last 1500 chars):", repr((msg.get("content") or "")[-1500:]))
for k in ("reasoning_content", "reasoning", "thinking"):
    if msg.get(k):
        print(f"{k} (first 300 chars):", repr(str(msg[k])[:300]))
print("parsed:", parse_final(msg.get("content") or ""), "| gold:", item["gold"])
