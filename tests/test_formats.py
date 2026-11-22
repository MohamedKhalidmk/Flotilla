"""Format tests for every dataset Flotilla converts (LongMemEval has its own, tests/test_longmemeval.py).

Real rows, a few per source, live in tests/data/formats/ (written by scripts/make_format_samples.py where the datasets
are): raw_rows.json holds raw dataset rows keyed by the converter's load call ("repo|config|split", "lcb|bench",
"lcb|pool"; images shrunk and stored as PNG base64), ruler_items.jsonl holds exported RULER items with the haystack's
middle cut out. Each converter runs on its rows through a stubbed loader, so the tests need neither the datasets nor
the Hugging Face libraries and run on the Mac.

Checked for every item: the core fields (ID, task type, question, gold) with the right types, the scorer, and what the
type needs (options with the right number of letters, public tests for code, images for vision); then a round trip
back to the raw row, field by field, so nothing the dataset gave is lost.
"""
import ast
import base64
import json
import sys
import types
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data" / "formats"
RAW = json.loads((DATA / "raw_rows.json").read_text())
RULER = [json.loads(l) for l in open(DATA / "ruler_items.jsonl")]

for mod, attrs in (("datasets", {"load_dataset": None}), ("huggingface_hub", {"snapshot_download": None})):
    try:
        __import__(mod)
    except ImportError:  # the Mac has neither; the converters only need the names at import time
        sys.modules[mod] = types.SimpleNamespace(**attrs)

from flotilla import export_ruler, router_data, splits, strategy_items  # noqa: E402

TASK_TYPES = {"math", "science_mc", "instruction", "code", "vision", "long_context"}
SCORERS = {"math_verify", "mc_letter", "ifeval", "mmmu", "ocrbench", "ruler_substring", "lcb"}


class Img:
    """Stands in for a PIL image: png_b64() calls .convert("RGB").save(buf, format="PNG")."""

    def __init__(self, png: bytes):
        self.png = png

    def convert(self, mode):
        return self

    def save(self, buf, format):
        buf.write(self.png)


def decode(v):
    if isinstance(v, dict) and "__png_b64__" in v:
        return Img(base64.b64decode(v["__png_b64__"]))
    if isinstance(v, dict):
        return {k: decode(x) for k, x in v.items()}
    if isinstance(v, list):
        return [decode(x) for x in v]
    return v


@pytest.fixture
def loader(monkeypatch, tmp_path):
    def load(repo, config=None, split=None):
        return [decode(r) for r in RAW[f"{repo}|{config}|{split}"]]
    for mod in (splits, router_data):
        monkeypatch.setattr(mod, "load_dataset", load)

    def lcb_root(key):
        d = tmp_path / key
        d.mkdir(exist_ok=True)
        for r in RAW[key]:
            with open(d / r["_file"], "a") as f:
                f.write(json.dumps({k: v for k, v in r.items() if k != "_file"}) + "\n")
        return d
    monkeypatch.setattr(splits, "snapshot_download", lambda *a, **k: str(lcb_root("lcb|bench")))
    monkeypatch.setattr(router_data, "snapshot_download", lambda *a, **k: str(lcb_root("lcb|pool")))


def letters(task: str) -> list[str]:
    return [l[0] for l in task.splitlines() if len(l) > 2 and l[1:3] == ". " and l[0].isupper()]


def check_core(it: dict, id_key: str = "item_id", graded_here: bool = True):
    """graded_here=False: an item graded elsewhere by its id (label items), so it carries no gold."""
    assert isinstance(it[id_key], str) and it[id_key]
    assert it["task_type"] in TASK_TYPES
    assert isinstance(it["task"], str) and it["task"].strip()
    t = it["task_type"]
    if not graded_here:
        assert it["gold"] is None
    elif t == "math":
        assert isinstance(it["gold"], str) and it["gold"].strip()
    elif t == "science_mc":
        opts = it["options"]
        assert isinstance(opts, list) and 2 <= len(opts) <= 10 and all(isinstance(o, str) for o in opts)
        assert letters(it["task"]) == [chr(65 + k) for k in range(len(opts))]   # A.. as many letters as options (up to J)
        assert isinstance(it["gold"], str) and len(it["gold"]) == 1 and "A" <= it["gold"] < chr(65 + len(opts))
    elif t == "instruction":
        assert it["gold"] is None
    elif t == "code":
        assert it["gold"] is None
    elif t == "vision":
        assert isinstance(it["images"], list) and it["images"] and all(isinstance(b, str) for b in it["images"])
        for b in it["images"]:
            assert base64.b64decode(b)[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------- benchmarks (flotilla.splits)

def bench(name: str) -> list[dict]:
    items = list(splits.BENCHES[name]())
    assert items, name
    ids = [it["item_id"] for it in items]
    assert len(ids) == len(set(ids)) and all(i.startswith(name.replace("aime2025", "aime2025") + "/") for i in ids)
    for it in items:
        check_core(it)
        assert it["scorer"] in SCORERS
    return items


def test_math_benchmarks(loader):
    """Checks that GSM8K, MATH-500 and AIME items keep the dataset's ID, question and gold, with the GSM8K gold taken after #### and commas removed.
    Guards against: a GSM8K gold that keeps the worked solution or a thousands comma, so a right answer is graded wrong."""
    for it, r in zip(bench("gsm8k"), RAW["openai/gsm8k|main|test"]):
        assert it["task"] == r["question"] and it["gold"] == r["answer"].split("####")[-1].strip().replace(",", "")
    for it, r in zip(bench("math500"), RAW["HuggingFaceH4/MATH-500|None|test"]):
        assert (it["item_id"], it["task"], it["gold"]) == (f"math500/{r['unique_id']}", r["problem"], r["answer"])
    for y in (2025, 2026):
        for it, r in zip(bench(f"aime{y}"), RAW[f"MathArena/aime_{y}|None|train"]):
            assert (it["item_id"], it["task"], it["gold"]) == (f"aime{y}/{r['problem_idx']}", r["problem"], str(r["answer"]))


def test_gpqa_options_shuffled_but_complete(loader):
    """Checks that each GPQA item has the four original options in some order and that the gold letter points at the correct answer.
    Guards against: a shuffle that drops an option or leaves the gold letter pointing at a wrong answer."""
    for it, r in zip(bench("gpqa"), RAW["Idavidrein/gpqa|gpqa_diamond|train"]):
        assert it["task_type"] == "science_mc" and len(it["options"]) == 4
        orig = [r["Correct Answer"]] + [r[f"Incorrect Answer {k}"] for k in (1, 2, 3)]
        assert sorted(it["options"]) == sorted(o.strip() for o in orig)
        assert it["options"][ord(it["gold"]) - 65] == r["Correct Answer"].strip()
        assert it["task"].startswith(r["Question"].strip())


def test_ifeval_keeps_instructions(loader):
    """Checks that IFEval items keep the prompt, the key-based ID, the instruction ID list and their kwargs unchanged.
    Guards against: IFEval items losing the instruction list or kwargs the ifeval scorer needs to grade them."""
    for it, r in zip(bench("ifeval"), RAW["google/IFEval|None|train"]):
        assert (it["item_id"], it["task"]) == (f"ifeval/{r['key']}", r["prompt"])
        assert it["instruction_id_list"] == r["instruction_id_list"] and it["kwargs"] == r["kwargs"]


def test_vision_benchmarks_keep_images_and_options(loader):
    """Checks that MMMU items keep every image, option and answer letter, and OCRBench items keep the image, a gold list and the OCR type.
    Guards against: a vision item with a missing image, or an MMMU multiple-choice question whose lettered options differ from the dataset."""
    for it, r in zip(bench("mmmu"), RAW["lmms-lab/MMMU|None|validation"]):
        imgs = [r[f"image_{k}"]["__png_b64__"] for k in range(1, 8) if r.get(f"image_{k}")]
        assert it["images"] == imgs and it["gold"] == r["answer"] and r["question"] in it["task"]
        opts = ast.literal_eval(r["options"]) if r["options"] else []
        assert (it["options"] or []) == opts
        if r["question_type"] == "multiple-choice":
            assert letters(it["task"]) == [chr(65 + k) for k in range(len(opts))]
    for it, r in zip(bench("ocrbench"), RAW["echo840/OCRBench|None|test"]):
        gold = r["answer"] if isinstance(r["answer"], list) else [r["answer"]]
        assert it["gold"] == gold and it["task"] == r["question"] and it["images"] == [r["image"]["__png_b64__"]]
        assert (it["ocr_type"], it["ocr_dataset"]) == (r["question_type"], r["dataset"])
    mmmu_types = {r["question_type"] for r in RAW["lmms-lab/MMMU|None|validation"]}
    assert mmmu_types == {"multiple-choice", "open"}


def test_lcb_keeps_every_test(loader):
    """Checks that LiveCodeBench items keep all public and private tests, give public tests only for stdin problems, and show starter code.
    Guards against: a code item graded on fewer tests than the dataset has, or a function problem shown without its starter code."""
    items = bench("lcb")
    assert {bool(it["starter_code"]) for it in items} == {True, False}    # a function problem and a stdin problem
    by_id = {f"lcb/{x['question_id']}": x for x in RAW["lcb|bench"]}
    assert sorted(it["item_id"] for it in items) == sorted(by_id)
    for it in items:
        r = by_id[it["item_id"]]
        public = json.loads(r["public_test_cases"])
        assert it["item_id"] == f"lcb/{r['question_id']}" and it["task"].startswith(r["question_content"])
        assert it["all_tests"] == public + router_data._lcb_private(r["private_test_cases"])
        if all(t.get("testtype") == "stdin" for t in public):
            assert it["public_tests"] == public and all({"input", "output"} <= set(t) for t in public)
        else:
            assert it["public_tests"] is None and r["starter_code"] in it["task"]


# ---------------------------------------------------------------- RULER (flotilla.export_ruler)

def test_ruler_items_and_round_trip():
    """Checks that exported RULER 32k and 64k items have a list of gold strings and the ruler_substring scorer, and rebuild exactly from the lm-eval instance.
    Guards against: a RULER item whose ID, gold list or token count no longer matches what export_ruler.ruler_item produces."""
    assert {r["bench"] for r in RULER} == {"ruler_32k", "ruler_64k"}
    for it in RULER:
        check_core(it)
        assert it["scorer"] == "ruler_substring" and isinstance(it["gold"], list) and all(isinstance(g, str) for g in it["gold"])
        bench_, name, k = it["item_id"].split("/")
        assert (bench_, name) == (it["bench"], it["ruler_task"])
        inst = types.SimpleNamespace(args=(it["task"],), doc={"outputs": tuple(it["gold"])}, doc_id=it["lm_eval_doc_id"])
        assert export_ruler.ruler_item(bench_, name, int(k), inst, it["n_tokens_qwen"]) == \
            {kk: v for kk, v in it.items() if kk != "trimmed_for_tests"}


# ---------------------------------------------------------------- router pool (flotilla.router_data) and label items

def pool(name: str) -> list[dict]:
    rows = list(router_data.SOURCES[name]())
    assert rows, name
    for r in rows:
        check_core(r, "id")
        assert r["source"] == name
    return rows


def test_pool_sources_round_trip(loader):
    """Checks that every router pool source (GSM8K, MATH, AIME, MMLU-Pro, IFEval-like, LiveCodeBench) keeps the raw row's ID, question, gold and tests.
    Guards against: MMLU-Pro rows cut to four options instead of up to ten, or a MATH gold not taken from the boxed answer."""
    for r, raw in zip(pool("gsm8k"), RAW["openai/gsm8k|main|train"]):
        assert r["task"] == raw["question"] and r["gold"] == raw["answer"].split("####")[-1].strip().replace(",", "")
    raws = [x for k, v in RAW.items() if k.startswith("EleutherAI/hendrycks_math") for x in v]
    for r in pool("math"):
        raw = next(x for x in raws if x["problem"] == r["task"])
        assert r["gold"] == router_data.boxed(raw["solution"]) and r["level"] == raw.get("level")
    for r, raw in zip(pool("aime"), RAW["di-zhang-fdu/AIME_1983_2024|None|train"]):
        assert r["id"] == f"aime-{raw['Year']}-{raw.get('Part', '')}-{raw['Problem Number']}"
        assert (r["task"], r["gold"]) == (raw["Question"], str(raw["Answer"]).strip())
    rows = pool("mmlu_pro")
    assert {len(r["options"]) for r in rows} >= {10} and min(len(r["options"]) for r in rows) < 10   # up to J, and fewer
    for r, raw in zip(rows, RAW["TIGER-Lab/MMLU-Pro|None|test"]):
        assert r["options"] == raw["options"] and r["gold"] == raw["answer"] and r["task"].startswith(raw["question"])
    for r, raw in zip(pool("ifeval_like"), RAW["allenai/RLVR-IFeval|None|train"]):
        assert r["task"] == raw["messages"][-1]["content"] and r["constraint"] == raw.get("constraint")
    by_id = {f"lcb-{x['question_id']}": x for x in RAW["lcb|pool"]}
    for r in pool("lcb"):
        raw = by_id[r["id"]]
        public = json.loads(raw["public_test_cases"])
        assert r["public_tests"] == public and r["tests"][: len(public)] == public and r["task"].startswith(raw["question_content"])


def test_strategy_label_items_round_trip(loader):
    """Checks that strategy label items built from pool rows keep the pool ID, task, task type and source, with no gold and the router_label scorer.
    Guards against: a label item carrying its gold in the item file, or an ID that no longer matches the pool row it is graded against."""
    rows = [r for name in router_data.SOURCES for r in router_data.SOURCES[name]()]
    assert {r["task_type"] for r in rows} == {"math", "science_mc", "instruction", "code"}
    for r in rows:
        it = strategy_items.to_item(r, "pilot")
        check_core(it, graded_here=False)
        assert (it["item_id"], it["task"], it["task_type"], it["source"]) == (r["id"], r["task"], r["task_type"], r["source"])
        assert it["scorer"] == "router_label" and it["gold"] is None   # graded from the pool by id
