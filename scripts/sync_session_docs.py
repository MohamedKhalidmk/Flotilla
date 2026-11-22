"""Keep the session documents (docs/session/: HANDOFF, WORKING_SETUP, PROJECT_HISTORY; markdown only) identical in both
repos. Flotilla's copy is the source; GRAFT gets a byte-for-byte copy.

    python scripts/sync_session_docs.py [--graft ../SGAR]     # from the Flotilla repo root

1. Make the source's links portable: a relative link to anything outside docs/session/ becomes an absolute link to
   Flotilla's work branch on GitHub, so the same bytes work in both repos (links between session files stay relative).
2. Copy every session file to GRAFT's docs/session/.
3. Write scripts/SHA256SUMS (the session files' hashes) in both repos. tests/test_session_docs.py (in both repos) fails if a session file
   no longer matches it, so an edit to one copy without a sync shows up in that repo's own tests.
"""
import argparse
import hashlib
import os
import re
import shutil
from pathlib import Path

FLOTILLA_URL = "https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/"
SESSION = Path("docs/session")
LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def portable(text: str) -> str:
    def repl(m):
        target = m.group(2)
        path, _, anchor = target.partition("#")
        if not path or re.match(r"^[a-z]+:", path) or "/" not in path and (SESSION / path).exists():
            return m.group(0)  # a URL, an anchor, or another session file
        resolved = os.path.normpath(SESSION / path)
        if resolved.startswith(".."):
            return m.group(0)
        return m.group(1) + FLOTILLA_URL + resolved + ("#" + anchor if anchor else "") + m.group(3)
    return LINK.sub(repl, text)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graft", default="../SGAR", help="the GRAFT checkout (default ../SGAR)")
    a = ap.parse_args()
    files = sorted(p for p in SESSION.iterdir() if p.suffix == ".md")
    for p in files:
        if p.suffix == ".md":
            t = p.read_text()
            u = portable(t)
            if u != t:
                p.write_text(u)
                print(f"portable links: {p}")
    sums = "".join(f"{sha(p)}  {p.name}\n" for p in files)
    Path("scripts/SHA256SUMS").write_text(sums)
    dest = Path(a.graft) / SESSION
    dest.mkdir(parents=True, exist_ok=True)
    for p in files:
        shutil.copyfile(p, dest / p.name)
    (Path(a.graft) / "scripts" / "SHA256SUMS").write_text(sums)
    print(f"{len(files)} session files synced to {dest}; scripts/SHA256SUMS written in both repos")


if __name__ == "__main__":
    main()
