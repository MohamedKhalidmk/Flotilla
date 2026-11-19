"""Quantize one model with llm-compressor (protocol 4.1: 4-bit W4A16 GPTQ and 8-bit W8A8 FP8).

    python -m flotilla.quantize --model Qwen/Qwen3.8-27B --scheme w4a16_gptq --out $SCRATCH/flotilla/quant/qwen-w4a16
Offline: models and calibration data come from the HF cache filled on the login node.
"""
import argparse
import json
import time
from pathlib import Path

import torch
from flotilla.data import load as load_dataset
from llmcompressor import oneshot
from llmcompressor.modifiers.quantization import GPTQModifier, QuantizationModifier
from transformers import AutoModelForCausalLM, AutoTokenizer

# Vision towers and the output head stay in BF16, as in CQL's recipes (only the language model's
# linear layers are quantized).
IGNORE = ["lm_head", "re:.*visual.*", "re:.*vision.*", "re:.*mm_projector.*", "re:.*multi_modal.*"]


def load_model(model_id: str):
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")
    except (ValueError, KeyError):
        from transformers import AutoModelForImageTextToText  # vision-language checkpoints (e.g. Qwen3.8)
        return AutoModelForImageTextToText.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")


def copy_side_files(model_id: str, out: Path) -> list[str]:
    """Copy every config/tokenizer/processor file of the original model that the save did not write
    (vLLM needs e.g. Qwen3.8's preprocessor_config.json); never weights or the model config."""
    import shutil
    from huggingface_hub import try_to_load_from_cache
    # the download kept only model files (allow_patterns), so locate the cached folder via its config.json
    src = Path(model_id) if Path(model_id).exists() else Path(try_to_load_from_cache(model_id, "config.json")).parent
    copied = []
    for f in src.iterdir():
        if f.is_file() and not f.name.endswith((".safetensors", ".bin", ".pt")) and f.name not in ("config.json", "model.safetensors.index.json") \
                and not (out / f.name).exists():
            shutil.copy2(f, out / f.name)
            copied.append(f.name)
    return copied


def calibration(tokenizer, n: int, seq_len: int):
    ds = load_dataset("HuggingFaceH4/ultrachat_200k", split=f"train_sft[:{n}]").shuffle(seed=20261119)

    def to_text(ex):
        return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}

    def tok(ex):
        return tokenizer(ex["text"], max_length=seq_len, truncation=True, add_special_tokens=False)

    ds = ds.map(to_text)
    return ds.map(tok, remove_columns=ds.column_names)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--scheme", choices=["w4a16_gptq", "w8a8_fp8"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=512)
    ap.add_argument("--seq-len", type=int, default=2048)
    a = ap.parse_args()

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(a.model)
    model = load_model(a.model)
    if a.scheme == "w4a16_gptq":
        recipe = GPTQModifier(targets="Linear", scheme="W4A16", ignore=IGNORE)
        ds = calibration(tokenizer, a.samples, a.seq_len)
        # text-only calibration, already tokenized: pass the tokenizer so vision-language models (Qwen3.8)
        # don't try to build their image processor
        oneshot(model=model, dataset=ds, recipe=recipe, processor=tokenizer, max_seq_length=a.seq_len,
                num_calibration_samples=a.samples)
    else:  # FP8 weights and dynamic per-token FP8 activations: needs no calibration data
        recipe = QuantizationModifier(targets="Linear", scheme="FP8_DYNAMIC", ignore=IGNORE)
        oneshot(model=model, recipe=recipe)
    out = Path(a.out)
    model.save_pretrained(out, save_compressed=True)
    tokenizer.save_pretrained(out)
    copy_side_files(a.model, out)
    meta = {"model": a.model, "scheme": a.scheme, "calibration": "ultrachat_200k train_sft" if a.scheme == "w4a16_gptq" else None,
            "samples": a.samples, "seq_len": a.seq_len, "ignore": IGNORE, "seconds": round(time.time() - t0, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 2**30, 1) if torch.cuda.is_available() else None}
    (out / "flotilla_quant.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
