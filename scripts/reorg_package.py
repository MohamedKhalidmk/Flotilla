"""Move flotilla/ modules into subpackages and rewrite every reference (2026-11-24). Run from the checkout root:
--move once to move the files; without it, only rewrites references (use after merging in commits that still use old names)."""
import re, subprocess, sys
from pathlib import Path

LAYOUT = {
    "core": ["system", "tools", "trace", "scoring", "serve", "smalltest", "ifeval_rules", "quantize", "vendor"],
    "routers": ["strategy_router", "rl_router", "strategy_labels", "strategy_items", "label_loop"],
    "memory": ["memory_route", "graft_bridge", "longmemeval", "supersede_check"],
    "data": ["data", "splits", "leakage", "full_items", "calib_pool", "export_ruler"],
    "research": ["failure_audit", "model_audit", "oracle", "results_table", "error_subtypes", "usc_replay", "toy_gate", "eval_math500"],
    "legacy": ["router_a", "router_b", "router_b_lite", "router_data", "router_labels", "eval_router"],
}
DOCS = {
    "core": "The Flotilla loop: orchestration, tools, verifier rules, traces, scoring, serving and quantization.",
    "routers": "Strategy routers: route labels, the supervised routers and the live RL router (test 04).",
    "memory": "Memory routes: GRAFT facts from a question's own history, LongMemEval items, and the GRAFT bridge.",
    "data": "Datasets, small-test and test splits, leakage checks and benchmark item exports.",
    "research": "Audits and analyses of finished runs: failure causes, oracles, result tables, replays and gates.",
    "legacy": "Router A and router B (tests 02 and 03), kept so their runs can be reproduced; nothing new imports them.",
}
SUB = {m: s for s, ms in LAYOUT.items() for m in ms}
NAMES = "|".join(sorted(SUB, key=len, reverse=True))
# Records of what was actually run keep the old paths (see docs/reference/package_layout.md).
HISTORY = [r"^docs/reference/run_log\.md$", r"^docs/session/PROJECT_HISTORY\.md$", r"^docs/session/CHAT_HISTORY",
           r"^experiments/.*/runs/", r"\.jsonl(\.gz)?$", r"^reports/", r"^results/"]
TEXT = {".py", ".md", ".sh", ".sbatch", ".json", ".txt", ".toml", ".cfg", ".yaml", ".yml", ""}

def sh(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout

def move():
    for s, ms in LAYOUT.items():
        Path(f"flotilla/{s}").mkdir(exist_ok=True)
        Path(f"flotilla/{s}/__init__.py").write_text(f'"""{DOCS[s]}"""\n')
        sh("git", "add", f"flotilla/{s}/__init__.py")
        for m in ms:
            src = f"flotilla/{m}" if m == "vendor" else f"flotilla/{m}.py"
            sh("git", "mv", src, f"flotilla/{s}/{Path(src).name}")

def split_from_import(m):
    indent, names, tail = m.group(1), m.group(2), m.group(3)
    parts = [p.strip() for p in names.split(",") if p.strip()]
    groups = {}
    for p in parts:
        base = p.split()[0]
        if base not in SUB:
            return m.group(0)
        groups.setdefault(SUB[base], []).append(p)
    lines = [f"{indent}from flotilla.{s} import {', '.join(ps)}" for s, ps in groups.items()]
    lines[-1] += tail
    return "\n".join(lines)

def rewrite(text):
    # dotted first, on the original text: flotilla.x (imports, -m, patch targets, prose)
    text = re.sub(rf"(?<![\w/.$])flotilla\.({NAMES})(?![\w])", lambda m: f"flotilla.{SUB[m.group(1)]}.{m.group(1)}", text)
    # paths: flotilla/x.py and flotilla/x.attr (not scratch folders such as $SCRATCH/flotilla/data/)
    text = re.sub(rf"(?<![\w.$-])(?<!scratch/)(?<!SCRATCH/)flotilla/({NAMES})(?=\.py\b|\.[a-z_]+\b)",
                  lambda m: f"flotilla/{SUB[m.group(1)]}/{m.group(1)}", text)
    text = re.sub(r"(?<![\w.$-])flotilla/vendor/", "flotilla/core/vendor/", text)
    # from flotilla import a, b as c   (whole line, possibly several subpackages)
    text = re.sub(r"(?m)^([ \t]*)from flotilla import ([A-Za-z_][\w ,]*?)([ \t]*(?:#.*)?)$", split_from_import, text)
    # inline: ...; from flotilla import x as y; ...   (in -c strings)
    text = re.sub(rf"from flotilla import ({NAMES})\b", lambda m: f"from flotilla.{SUB[m.group(1)]} import {m.group(1)}", text)
    return text

def main():
    if "--move" in sys.argv:
        move()
    changed = []
    for f in sh("git", "ls-files").splitlines():
        p = Path(f)
        if any(re.search(h, f) for h in HISTORY) or p.suffix not in TEXT or not p.is_file():
            continue
        t = p.read_text(errors="strict") if p.stat().st_size < 3_000_000 else None
        if t is None:
            continue
        n = rewrite(t)
        if n != t:
            p.write_text(n); changed.append(f)
    print(len(changed), "files rewritten"); print("\n".join(changed))

main()
