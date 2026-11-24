"""leakage --extra-targets: sets besides the test sets (the chat guide's source vs LongMemEval, 2026-11-22)."""
import json

from flotilla.data.leakage import extra_targets


def test_extra_targets_reads_task_or_text_and_skips_empty(tmp_path):
    """Checks that extra_targets reads each line's task, or its text when there is no task, and drops blank or missing ones.
    Guards against: blank strings or lines with neither field being added as leakage targets."""
    f = tmp_path / "u.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in ({"task": "a b c"}, {"text": "d e"}, {"task": "  "}, {"other": 1})) + "\n")
    assert extra_targets([f"lme={f}"]) == {"lme": ["a b c", "d e"]}
    assert extra_targets([]) == {}
