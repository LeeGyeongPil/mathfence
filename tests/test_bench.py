"""AC-9: the comparison script reproduces mathfence's lead."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))

import compare  # noqa: E402


def test_mathfence_leads_and_never_breaks_code_or_urls():
    rows = {r.name: r for r in compare.compare()}
    assert list(rows) == ["no processing", "escape every $", "regex recipe", "mathfence"]
    ours = rows["mathfence"]
    assert ours.broken == 0
    assert ours.passed == max(r.passed for r in rows.values())
    assert ours.passed > rows["regex recipe"].passed > 0
    assert rows["regex recipe"].broken > 0
    assert rows["escape every $"].broken > 0
    assert ours.flicker == 0


def test_script_prints_a_four_row_table():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "bench" / "compare.py")], capture_output=True, text=True, timeout=120, check=False
    )
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    assert lines[0].split() == ["approach", "pass", "score", "broken", "flicker"]
    assert len([ln for ln in lines[1:] if ln.startswith(("no processing", "escape", "regex", "mathfence"))]) == 4
