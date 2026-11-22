"""Flotilla charts, drawn only from results/tables/*.csv (never from typed numbers).

    python docs/design/charts.py        -> results/figures/<test>.png, copied to experiments/<test>/figure.png
Theme: colours from the logo (navy shirt, duck yellow, neckerchief red, ivory, ink), Nunito 600/700/800.
"""
import csv
import os
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch

D = Path(__file__).resolve().parent
ROOT = D.parent.parent
TABLES, FIGS = ROOT / "results" / "tables", ROOT / "results" / "figures"
for w in ("600", "700", "800"):
    fm.fontManager.addfont(str(D / f"Nunito-{w}.ttf"))
plt.rcParams.update({"font.family": "Nunito", "font.weight": 600})
IVORY, INK, INK2, INK3, LINE = "#F3EFE6", "#2A2723", "#5F5A52", "#8E887D", "#E2DCCF"
NAVY, YELLOW, RED, STONE = "#22344A", "#F2C230", "#C8362E", "#C9C2B4"


def table(name: str) -> list[dict]:
    with open(TABLES / f"{name}.csv") as f:
        return list(csv.DictReader(f))


def num(v):
    return None if v in ("", None) else float(v)


def frame(fig, title, sub):
    fig.patch.set_facecolor(IVORY)
    fig.text(0.04, 0.945, title, fontsize=21, weight=800, color=INK)
    fig.text(0.04, 0.905, sub, fontsize=10.5, color=INK2)


def style(ax, labels):
    ax.set_facecolor(IVORY)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=11, color=INK, weight=700)
    ax.tick_params(axis="x", colors=INK3, labelsize=9, length=0)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.grid(axis="x", color=LINE, lw=1)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)


def save(fig, test: str):
    FIGS.mkdir(parents=True, exist_ok=True)
    out = FIGS / f"{test}.png"
    fig.savefig(out, facecolor=IVORY)
    plt.close(fig)
    shutil.copy(out, ROOT / "experiments" / test / "figure.png")
    print("wrote", out.relative_to(ROOT))


def test01():
    rows = table("test-01-quantization__table")
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(9, 6.0), dpi=200)
    frame(fig, "Which precision?", "MATH-500, all 500 questions · rule 4.1: 4-bit if within 1 point of 8-bit")
    col = {"16-bit reference": STONE, "8-bit": NAVY, "4-bit": YELLOW}
    for i, r in enumerate(rows):
        v = num(r["accuracy"])
        ax.barh(i, v, height=0.62, color=col[r["bits"]], zorder=3)
        ax.text(v + 0.006, i, f"{v:.3f}", va="center", fontsize=9.5, weight=800, color=INK)
    style(ax, [(f"{r['candidate']} · " if r.get("candidate", "")[:1] == "F" else "") + f"{r['model'].split('-')[0].replace('Qwen3.8', 'Qwen')} · {r['build']}" for r in rows])
    ax.set_xlim(0.70, 1.0)
    fig.legend(handles=[Patch(color=STONE, label="16-bit reference"), Patch(color=NAVY, label="8-bit"),
                        Patch(color=YELLOW, label="4-bit")], loc="upper left", bbox_to_anchor=(0.035, 0.885), ncol=3,
               frameon=False, fontsize=10, labelcolor=INK2, handlelength=1.1, handleheight=1.1)
    fig.text(0.04, 0.02, "Axis starts at 0.70. Qwen keeps 4-bit (0 points below 8-bit); Phi keeps 8-bit (3.4 below).",
             fontsize=9, color=INK3)
    plt.subplots_adjust(left=0.33, right=0.96, top=0.82, bottom=0.08)
    save(fig, "test-01-quantization")


def test02():
    rows = [r for r in table("test-02-model-small-test__table") if r["benchmark"] != "Mean over benchmarks"][::-1]
    fig, ax = plt.subplots(figsize=(9, 8.2), dpi=200)
    frame(fig, "Model-selection test", f"{sum(int(r['n']) for r in rows)} questions across {len(rows)} benchmarks · higher is better")
    bh, gap = 0.22, 0.26
    for i, r in enumerate(rows):
        for k, (key, c) in enumerate((("qwen", NAVY), ("gptoss", YELLOW), ("cmda", STONE))):
            y, v = i + (1 - k) * gap, num(r[key])
            if v is None:
                ax.text(0.01, y, "no image input", va="center", fontsize=8.5, color=INK3, style="italic")
                continue
            ax.barh(y, v, height=bh, color=c, zorder=3)
            if k == 0:
                ax.text(v + 0.025, y, f"{v:.2f}", va="center", fontsize=9.5, weight=800, color=NAVY)
    style(ax, [r["benchmark"] for r in rows])
    ax.set_xlim(0, 1.1)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xticklabels(["0", ".25", ".50", ".75", "1.0"])
    fig.legend(handles=[Patch(color=NAVY, label="Qwen3.8-27B · 4-bit"), Patch(color=YELLOW, label="gpt-oss-20b (dropped)"),
                        Patch(color=STONE, label="Command A+ (dropped)")], loc="upper left", bbox_to_anchor=(0.035, 0.89),
               ncol=3, frameon=False, fontsize=10, labelcolor=INK2, handlelength=1.1, handleheight=1.1, columnspacing=1.8)
    fig.text(0.04, 0.02, "20–66 questions per benchmark, so gaps under ~0.10 can be noise.", fontsize=9, color=INK3)
    plt.subplots_adjust(left=0.19, right=0.97, top=0.84, bottom=0.07)
    save(fig, "test-02-model-small-test")


def test03():
    rows = table("test-03-router-b-models__table")[::-1]
    q = num(next(r for r in rows if r["system"] == "Qwen alone")["held_out_accuracy"])
    fig, ax = plt.subplots(figsize=(9, 5.0), dpi=200)
    frame(fig, "Why one model", f"{rows[0]['held_out_questions']} held-out pool questions · accuracy of each choice")
    for i, r in enumerate(rows):
        v = num(r["held_out_accuracy"])
        c = NAVY if r["system"] == "Qwen alone" else STONE if "Perfect" in r["system"] else YELLOW if "Router B" in r["system"] else STONE
        ax.barh(i, v, height=0.56, color=c, zorder=3, hatch="///" if "Perfect" in r["system"] else None, edgecolor=IVORY if "Perfect" in r["system"] else None)
        ax.text(v + 0.002, i, f"{v:.3f}  ({num(r['gain_over_qwen']):+.3f})" if r["system"] != "Qwen alone" else f"{v:.3f}",
                va="center", fontsize=9.5, weight=800, color=INK)
    ax.axvline(q, color=NAVY, lw=1.4, ls=(0, (4, 3)), zorder=2)
    short = {"Router B: ModernBERT-base fine-tune (final epoch, saved)": "Router B (ModernBERT)",
             "Baseline: bge-small + logistic regression": "bge + logistic regression"}
    style(ax, [(f"{r['candidate']} · " if r.get("candidate", "")[:1] == "F" else "") + short.get(r["system"], r["system"]) for r in rows])
    ax.set_xlim(0.83, 0.96)
    fig.text(0.04, 0.02, "Axis starts at 0.83. Keep rule: a router must add about 1 point; router B adds 0.4.",
             fontsize=9, color=INK3)
    plt.subplots_adjust(left=0.30, right=0.96, top=0.82, bottom=0.11)
    save(fig, "test-03-router-b-models")


def test04():
    rows = table("test-04-strategy-router__table")[::-1]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 5.8), dpi=200, sharey=True, gridspec_kw={"width_ratios": [1.25, 1]})
    done = [r for r in rows if num(r["accuracy"]) is not None]
    frame(fig, "Which route, per question?",
          f"Full labels: {done[0]['questions'] if done else 0} pool questions, every route on every question, fixed graders · Qwen 4-bit for all")
    best = max((num(r["accuracy"]) for r in done if not r["route"].startswith("Some route")), default=None)
    for i, r in enumerate(rows):
        v, g = num(r["accuracy"]), num(r["gpu_seconds_per_question"])
        if v is None:
            ax.text(0.01, i, "LongMemEval only: not offered on pool questions", va="center", fontsize=9.5, color=INK3, style="italic")
            continue
        oracle = r["route"].startswith("Some route")
        ax.barh(i, v, height=0.58, color=RED if oracle else YELLOW if v == best else NAVY, zorder=3)
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=9.5, weight=800, color=INK)
        if g is None:
            bx.text(0.3, i, "tries every route", va="center", fontsize=9.5, color=INK3, style="italic")
            continue
        bx.barh(i, g, height=0.58, color=STONE, zorder=3)
        bx.text(g + 0.3, i, f"{g:.1f}", va="center", fontsize=9.5, weight=800, color=INK)
    style(ax, [(f"{r['candidate']} · " if r.get("candidate", "")[:1] == "F" else "") + r["route"].replace(" (oracle)", "") for r in rows])
    style(bx, [(f"{r['candidate']} · " if r.get("candidate", "")[:1] == "F" else "") + r["route"].replace(" (oracle)", "") for r in rows])
    ax.set_xlim(0, 1.0)
    bx.set_xlim(0, max((num(r["gpu_seconds_per_question"]) or 0 for r in done), default=1) * 1.25)
    ax.set_title("Accuracy", loc="left", fontsize=11.5, weight=800, color=INK)
    bx.set_title("GPU-seconds per question", loc="left", fontsize=11.5, weight=800, color=INK)
    fig.text(0.04, 0.02, "Yellow: best single route. Red: some route right (what a perfect router would reach).",
             fontsize=9, color=INK3)
    plt.subplots_adjust(left=0.21, right=0.97, top=0.8, bottom=0.1, wspace=0.16)
    save(fig, "test-04-strategy-router")


def test05():
    rows = [r for r in table("test-05-graft-base-graph__table") if num(r["doc_entities_exact_overlap"]) is not None][::-1]
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=200)
    frame(fig, "How much of the documents does the base graph know?",
          "Share of document entities already in the base graph, by exact name (before Haiku linking)")
    for i, r in enumerate(rows):
        v = num(r["doc_entities_exact_overlap"])
        ax.barh(i, v, height=0.52, color=NAVY if v >= 0.5 else STONE, zorder=3)
        ax.text(v + 0.01, i, f"{v:.0%}  · {int(r['base_facts']):,} base facts", va="center", fontsize=9.5, weight=800, color=INK)
    style(ax, [r["variant"].split(" (")[0] for r in rows])
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    fig.text(0.04, 0.02, "Accuracy with each base is in the test table; the full T-REx runs are still going.", fontsize=9, color=INK3)
    plt.subplots_adjust(left=0.27, right=0.96, top=0.8, bottom=0.13)
    save(fig, "test-05-graft-base-graph")


if __name__ == "__main__":
    for f in (test01, test02, test03, test04, test05):
        f()
