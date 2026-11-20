"""Shared helpers for the test table builders: write a table as CSV + markdown, here and in results/tables/."""
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists() and Path(str(p) + ".gz").exists():
        p = Path(str(p) + ".gz")
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_table(test_dir: Path, name: str, rows: list[dict], note: str = "") -> None:
    """test_dir/<name>.csv and .md, copied to results/tables/<test>__<name>.csv/.md (the source for every chart)."""
    cols = list(rows[0]) if rows else []
    for out_dir, stem in ((test_dir, name), (ROOT / "results" / "tables", f"{test_dir.name}__{name}")):
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"{stem}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        def fmt(v):
            if v is None or v == "":
                return ""
            if isinstance(v, float):
                return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else f"{v:.0f}"
            return str(v)
        md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(fmt(r[c]) for c in cols) + " |" for r in rows]
        (out_dir / f"{stem}.md").write_text((note + "\n\n" if note else "") + "\n".join(md) + "\n")
