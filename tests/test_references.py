import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = re.compile(r"^(?:#\s*)?Sources:\s*(.+?)\s*(?:\(docs/reference/REFERENCES\.md\))?\s*$")


def reference_keys() -> set[str]:
    text = (ROOT / "docs/reference/REFERENCES.md").read_text()
    return set(re.findall(r"^\| `([^`]+)` \|", text, re.M))


def named_sources(path: Path) -> list[str] | None:
    for line in path.read_text(errors="replace").splitlines()[:30]:
        m = SOURCES.match(line.strip())
        if m:
            return [k.strip() for k in m.group(1).split(",") if k.strip()]
    return None


def scanned_files() -> list[Path]:
    pats = ["prompts/*.md", "flotilla/**/*.py", "scripts/**/*.py", "tests/*.py"]
    return sorted({Path(p) for pat in pats for p in glob.glob(str(ROOT / pat), recursive=True)})


def test_every_named_source_is_in_references():
    """Checks that every key in a file's Sources line (prompts, package code, scripts, tests) is listed in docs/reference/REFERENCES.md.
    Guards against: a file crediting a source that the references page does not cite, link or licence."""
    keys = reference_keys() | {"original"}
    missing = {str(p.relative_to(ROOT)): sorted(set(named_sources(p) or []) - keys) for p in scanned_files()}
    assert not {f: k for f, k in missing.items() if k}


def test_every_prompt_file_names_its_source():
    """Checks that every prompt file in prompts/ (legacy ones aside) has a Sources line near its top, original or borrowed.
    Guards against: a new prompt copied from a paper without saying so."""
    prompts = [p for p in (ROOT / "prompts").glob("*.md")]
    assert prompts and not [p.name for p in prompts if named_sources(p) is None]


def test_reference_entries_point_at_real_files():
    """Checks that every repository path named in REFERENCES.md exists, and that the main borrowed-code files carry a Sources line.
    Guards against: a references page that credits files which were renamed or deleted."""
    text = (ROOT / "docs/reference/REFERENCES.md").read_text()
    paths = {p for p in re.findall(r"`((?:flotilla|prompts|scripts|tests|docs|configs|notes)/[^`*]+)`", text)}
    assert not sorted(p for p in paths if not (ROOT / p).exists())
    for f in ("flotilla/memory_route.py", "flotilla/longmemeval.py", "flotilla/scoring.py", "prompts/vote_usc.v1.md"):
        assert named_sources(ROOT / f), f
