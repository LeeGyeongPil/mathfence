"""AC-7: the command line."""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import mathfence
from mathfence.cli import main

ROOT = Path(__file__).resolve().parent.parent
ANSWER = ROOT / "examples" / "answer.md"


def run_cli(args, monkeypatch, capsys, stdin=None):
    monkeypatch.delenv("MATHFENCE_LANG", raising=False)
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin), encoding="utf-8"))
    code = main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_prints_the_normalized_text(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.md"
    f.write_text("It costs $5 and $x$ and \\(y\\).\n", encoding="utf-8")
    code, out, err = run_cli([str(f)], monkeypatch, capsys)
    assert (code, err) == (0, "")
    assert out == "It costs \\$5 and $x$ and $y$.\n"


def test_example_answer_keeps_code_and_urls(monkeypatch, capsys):
    code, out, _ = run_cli([str(ANSWER)], monkeypatch, capsys)
    assert code == 0
    assert 'echo "$1 costs $5"' in out
    assert "https://example.com/pricing?plan=$5" in out
    assert "costs \\$5 per month" in out


def test_reads_standard_input(monkeypatch, capsys):
    code, out, _ = run_cli(["-"], monkeypatch, capsys, stdin=b"pay $5\n")
    assert (code, out) == (0, "pay \\$5\n")
    code, out, _ = run_cli([], monkeypatch, capsys, stdin=b"pay $6\n")
    assert out == "pay \\$6\n"


def test_profile_option(monkeypatch, capsys):
    code, out, _ = run_cli(["--profile", "streamlit", "-"], monkeypatch, capsys, stdin=b"a \\[x\\] b")
    assert out == "a\n\n$$\nx\n$$\n\nb"


def test_explain_json_has_decisions(monkeypatch, capsys):
    code, out, _ = run_cli(["--explain", "--format", "json", str(ANSWER)], monkeypatch, capsys)
    assert code == 0
    report = json.loads(out)
    assert report["file"] == str(ANSWER)
    assert report["changed"] is True
    assert report["text"] == mathfence.normalize(ANSWER.read_text(encoding="utf-8"))
    assert report["decisions"]
    for d in report["decisions"]:
        assert {"line", "column", "action", "rule", "source", "kind", "reason"} <= d.keys()
        assert isinstance(d["line"], int) and isinstance(d["column"], int)


def test_explain_table_has_a_rule_column(monkeypatch, capsys):
    code, out, _ = run_cli(["--explain", "--lang", "en", str(ANSWER)], monkeypatch, capsys)
    assert code == 0
    header = out.splitlines()[0]
    assert header.split()[:3] == ["line:col", "action", "rule"]
    assert "body-edge-space" in out and "code-fence" in out
    assert "decision(s) in" in out


def test_explain_without_decisions(monkeypatch, capsys):
    code, out, _ = run_cli(["--explain", "--lang", "en", "-"], monkeypatch, capsys, stdin=b"nothing here\n")
    assert code == 0 and "No dollar signs" in out


def test_check_exit_codes(monkeypatch, capsys, tmp_path):
    dirty = tmp_path / "dirty.md"
    dirty.write_text("costs $5 and $6", encoding="utf-8")
    clean = tmp_path / "clean.md"
    clean.write_text("Solve $x^2$ now.\n", encoding="utf-8")
    code, out, _ = run_cli(["--check", "--lang", "en", str(clean)], monkeypatch, capsys)
    assert code == 0 and "nothing to change" in out
    code, out, _ = run_cli(["--check", "--lang", "en", str(clean), str(dirty)], monkeypatch, capsys)
    assert code == 1
    assert out.strip() == f"{dirty}: would change"


def test_missing_file_is_exit_2_with_a_hint(monkeypatch, capsys):
    code, out, err = run_cli(["--lang", "en", "nope/missing.md"], monkeypatch, capsys)
    assert code == 2 and out == ""
    assert "file not found: nope/missing.md" in err
    assert "'-'" in err


def test_directory_is_exit_2(monkeypatch, capsys, tmp_path):
    code, _, err = run_cli(["--lang", "en", str(tmp_path)], monkeypatch, capsys)
    assert code == 2 and "not a readable file" in err


def test_non_utf8_file_is_exit_2(monkeypatch, capsys, tmp_path):
    f = tmp_path / "latin.md"
    f.write_bytes(b"caf\xe9 $5")
    code, _, err = run_cli(["--lang", "en", str(f)], monkeypatch, capsys)
    assert code == 2 and "not valid UTF-8" in err and "iconv" in err


def test_bad_options_are_exit_2(monkeypatch, capsys):
    code, _, err = run_cli(["--lang", "en", "--profile", "gradio", "-"], monkeypatch, capsys, stdin=b"x")
    assert code == 2 and "remark, streamlit" in err
    code, _, err = run_cli(["--lang", "en", "--format", "xml", "-"], monkeypatch, capsys, stdin=b"x")
    assert code == 2 and "unknown format" in err
    code, _, err = run_cli(["--lang", "en", "--bogus"], monkeypatch, capsys)
    assert code == 2 and "--help" in err
    code, _, err = run_cli(["--lang", "fr", "-"], monkeypatch, capsys, stdin=b"x")
    assert code == 2 and "unknown language" in err


def test_explain_accepts_a_single_input(monkeypatch, capsys):
    code, _, err = run_cli(["--lang", "en", "--explain", str(ANSWER), str(ANSWER)], monkeypatch, capsys)
    assert code == 2 and "single input" in err


def test_several_files_get_headers(monkeypatch, capsys, tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("$5\n", encoding="utf-8")
    b.write_text("$6", encoding="utf-8")
    _, out, _ = run_cli([str(a), str(b)], monkeypatch, capsys)
    assert out == f"==> {a} <==\n\\$5\n==> {b} <==\n\\$6\n"


def test_version(monkeypatch, capsys):
    code, out, _ = run_cli(["--version"], monkeypatch, capsys)
    assert (code, out) == (0, f"mathfence {mathfence.__version__}\n")


def test_installed_script_runs_end_to_end():
    proc = subprocess.run(
        [sys.executable, "-m", "mathfence.cli", "-"],
        input="pay $5 and $x$",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout == "pay \\$5 and $x$"
