"""Which part of an image request Cohere's compatibility API rejects. One call per variant; the key is never printed."""
import base64, io, json, os, sys
sys.path.insert(0, "/Users/mk/flotilla")
from openai import OpenAI
from PIL import Image
from flotilla.core.system import solver_messages, parse_final
it = [json.loads(l) for l in open("/Users/mk/flotilla-data/smalltest/ocrbench.jsonl")][0]
c = OpenAI(base_url="https://api.cohere.ai/compatibility/v1", api_key=os.environ["COHERE_API_KEY"], max_retries=0, timeout=600)
M = "command-a-plus-05-2026"
b64 = it["images"][0]
im = Image.open(io.BytesIO(base64.b64decode(b64)))
print("image size:", im.size, "base64 chars:", len(b64))
small = im.copy(); small.thumbnail((512, 512)); buf = io.BytesIO(); small.convert("RGB").save(buf, "JPEG", quality=90)
small_b64 = base64.b64encode(buf.getvalue()).decode()
base = solver_messages(it["task"], "vision", "v1", images=[b64])
dev = [{"role": "developer", "content": base[0]["content"]}, base[1]]
img_part = base[1]["content"][0]; txt_part = base[1]["content"][1]
text_after = [dev[0], {"role": "user", "content": [txt_part, img_part]}]
user_only = [{"role": "user", "content": [img_part, {"type": "text", "text": base[0]["content"] + "\n\n" + it["task"]}]}]
small_jpeg = [dev[0], {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{small_b64}"}}, txt_part]}]
variants = {
    "dev_image_first_no_thinking": dict(messages=dev, reasoning_effort="none"),
    "user_only_image_thinking": dict(messages=user_only, reasoning_effort="high"),
    "dev_text_then_image_thinking": dict(messages=text_after, reasoning_effort="high"),
    "dev_small_jpeg_thinking": dict(messages=small_jpeg, reasoning_effort="high"),
}
for name, kw in variants.items():
    try:
        r = c.chat.completions.create(model=M, temperature=0.0, max_tokens=8192, **kw)
        msg = r.choices[0].message
        print(f"[{name}] OK finish={r.choices[0].finish_reason} tokens={r.usage.completion_tokens} content tail={(msg.content or '')[-200:]!r}")
        print("   parsed:", parse_final(msg.content or ""), "gold:", it["gold"])
    except Exception as e:
        print(f"[{name}] FAIL {type(e).__name__}: {str(e)[:200]}")
