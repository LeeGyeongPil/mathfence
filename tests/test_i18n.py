"""AC-8: two languages and how one is chosen."""

import pytest

from mathfence import rules
from mathfence.cli import main
from mathfence.i18n import MESSAGES, resolve_lang

HANGUL = range(0xAC00, 0xD7A4)


def has_hangul(text):
    return any(ord(c) in HANGUL for c in text)


def run(args, capsys, env=None, monkeypatch=None, stdin=None):
    for var in ("MATHFENCE_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    code = main(args)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_both_languages_have_the_same_keys():
    assert set(MESSAGES) == {"en", "ko"}
    assert set(MESSAGES["en"]) == set(MESSAGES["ko"])


def test_every_rule_has_a_reason_in_both_languages():
    for lang in MESSAGES:
        for rule in rules.ALL_RULES:
            assert MESSAGES[lang].get("reason." + rule), (lang, rule)
        assert not [k for k in MESSAGES[lang] if k.startswith("reason.") and k[7:] not in rules.ALL_RULES]


def test_placeholders_match_between_languages():
    import string

    def fields(s):
        return {f for _, f, _, _ in string.Formatter().parse(s) if f}

    for key in MESSAGES["en"]:
        assert fields(MESSAGES["en"][key]) == fields(MESSAGES["ko"][key]), key


def test_korean_messages_are_korean_and_english_are_not():
    for key, text in MESSAGES["ko"].items():
        if key != "stdin.name":
            assert has_hangul(text), key
    for key, text in MESSAGES["en"].items():
        assert not has_hangul(text), key


def test_help_switches_language(capsys, monkeypatch):
    _, ko, _ = run(["--lang", "ko", "--help"], capsys, monkeypatch=monkeypatch)
    _, en, _ = run(["--lang", "en", "--help"], capsys, monkeypatch=monkeypatch)
    assert has_hangul(ko) and "사용법" in ko
    assert not has_hangul(en) and "usage:" in en
    assert ko != en


def test_explain_switches_language(capsys, monkeypatch, tmp_path):
    f = tmp_path / "a.md"
    f.write_text("pay $5 and $6", encoding="utf-8")
    _, ko, _ = run(["--lang", "ko", "--explain", str(f)], capsys, monkeypatch=monkeypatch)
    _, en, _ = run(["--lang", "en", "--explain", str(f)], capsys, monkeypatch=monkeypatch)
    assert "줄:칸" in ko and has_hangul(ko)
    assert "line:col" in en and not has_hangul(en)


@pytest.mark.parametrize(
    ("explicit", "env", "expected"),
    [
        ("ko", {"MATHFENCE_LANG": "en", "LANG": "en_US.UTF-8"}, "ko"),
        ("en", {"MATHFENCE_LANG": "ko", "LANG": "ko_KR.UTF-8"}, "en"),
        (None, {"MATHFENCE_LANG": "ko", "LC_ALL": "en_US.UTF-8"}, "ko"),
        (None, {"MATHFENCE_LANG": "en", "LC_ALL": "ko_KR.UTF-8"}, "en"),
        (None, {"LC_ALL": "ko_KR.UTF-8", "LC_MESSAGES": "en_US.UTF-8", "LANG": "en_US.UTF-8"}, "ko"),
        (None, {"LC_ALL": "en_US.UTF-8", "LC_MESSAGES": "ko_KR.UTF-8", "LANG": "ko_KR.UTF-8"}, "en"),
        (None, {"LC_MESSAGES": "ko_KR.UTF-8", "LANG": "en_US.UTF-8"}, "ko"),
        (None, {"LANG": "ko_KR.UTF-8"}, "ko"),
        (None, {"LANG": "ko"}, "ko"),
        (None, {"LANG": "fr_FR.UTF-8"}, "en"),
        (None, {"LANG": "C"}, "en"),
        (None, {"LC_ALL": "", "LANG": "ko_KR.UTF-8"}, "ko"),
        (None, {}, "en"),
    ],
)
def test_language_priority(explicit, env, expected):
    assert resolve_lang(explicit, env) == expected


def test_cli_reads_the_environment(capsys, monkeypatch):
    _, out, _ = run(["--help"], capsys, env={"MATHFENCE_LANG": "ko"}, monkeypatch=monkeypatch)
    assert has_hangul(out)
    _, out, _ = run(["--help"], capsys, env={"LANG": "ko_KR.UTF-8"}, monkeypatch=monkeypatch)
    assert has_hangul(out)
    _, out, _ = run(["--help"], capsys, env={"LANG": "ko_KR.UTF-8", "MATHFENCE_LANG": "en"}, monkeypatch=monkeypatch)
    assert not has_hangul(out)
    _, out, _ = run(["--help"], capsys, env={"MATHFENCE_LANG": "ko"}, monkeypatch=monkeypatch)
    code, _, err = run(["--lang", "en", "missing.md"], capsys, env={"MATHFENCE_LANG": "ko"}, monkeypatch=monkeypatch)
    assert code == 2 and not has_hangul(err)


def test_errors_are_localized(capsys, monkeypatch):
    code, _, err = run(["--lang", "ko", "missing.md"], capsys, monkeypatch=monkeypatch)
    assert code == 2 and has_hangul(err) and "missing.md" in err


@pytest.mark.parametrize("argv", [["-x"], ["--profile"], ["--prof", "remark"]])
def test_usage_errors_are_fully_korean(capsys, argv):
    assert main(["--lang", "ko", *argv]) == 2
    err = capsys.readouterr().err
    assert "오류" in err
    for english in ("unrecognized", "expected one argument", "error:"):
        assert english not in err


def test_usage_errors_in_english(capsys):
    assert main(["--lang", "en", "-x"]) == 2
    assert "unrecognized arguments: -x" in capsys.readouterr().err


def test_explain_table_columns_align_for_wide_characters(capsys, tmp_path):
    from mathfence.cli import _width

    f = tmp_path / "a.md"
    f.write_text("Pay $5 and `$x$` and $y$.\n", encoding="utf-8")
    assert main(["--lang", "ko", "--explain", str(f)]) == 0
    lines = capsys.readouterr().out.splitlines()
    table = [ln for ln in lines if ln.strip()][:-1]
    # Every row's last column (the reason) starts at the same display column.
    reasons = [v for k, v in MESSAGES["ko"].items() if k.startswith("reason.")]
    reason_col = _width(table[0][: table[0].index(MESSAGES["ko"]["explain.col.reason"])])
    for row in table[1:]:
        hit = [r for r in reasons if r in row]
        assert hit, row
        assert _width(row[: row.index(hit[0])]) == reason_col, row
