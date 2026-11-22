"""``mathfence`` command line."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict
from typing import NoReturn

from . import __version__
from .core import PROFILES, Result, analyze
from .i18n import LANGS, message, resolve_lang

_FORMATS = ("text", "json")


class _UsageError(Exception):
    """A command-line mistake; ``key``/``params`` pick the localized message."""

    def __init__(self, key: str, **params: str) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # noqa: A002 - argparse API
        # Map argparse's English sentences to message keys so both languages work.
        unknown = re.match(r"unrecognized arguments: (.*)$", message)
        missing = re.match(r"argument (\S+): expected \S+ argument", message)
        if unknown:
            raise _UsageError("error.unknown_option", option=unknown.group(1))
        if missing:
            raise _UsageError("error.missing_value", option=missing.group(1))
        raise _UsageError("error.usage_generic")


def _build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="mathfence", add_help=False, allow_abbrev=False)
    p.add_argument("files", nargs="*")
    p.add_argument("--profile", default="remark")
    p.add_argument("--explain", action="store_true")
    p.add_argument("--format", dest="fmt", default="text")
    p.add_argument("--check", action="store_true")
    p.add_argument("--lang", default=None)
    p.add_argument("--version", action="store_true")
    p.add_argument("-h", "--help", action="store_true")
    return p


def _prescan_lang(argv: Sequence[str]) -> str | None:
    """Find ``--lang`` before full parsing so even usage errors use it."""
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def _read(path: str, lang: str) -> str:
    try:
        if path == "-":
            return sys.stdin.buffer.read().decode("utf-8")
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8")
    except FileNotFoundError:
        raise _Fail(message(lang, "error.file_not_found", path=path)) from None
    except (IsADirectoryError, PermissionError, OSError):
        raise _Fail(message(lang, "error.not_a_file", path=path)) from None
    except UnicodeDecodeError:
        raise _Fail(message(lang, "error.not_utf8", path=path)) from None


class _Fail(Exception):
    """A user-facing error: the text is printed and the exit status is 2."""


def _short(source: str, limit: int = 32) -> str:
    flat = source.replace("\n", "\\n")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _width(text: str) -> int:
    """Display width: East Asian wide characters take two columns."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int) -> str:
    return text + " " * (width - _width(text))


def _explain_table(result: Result, path: str, lang: str) -> str:
    if not result.decisions:
        return message(lang, "explain.none") + "\n"
    header = (
        message(lang, "explain.col.position"),
        message(lang, "explain.col.action"),
        message(lang, "explain.col.rule"),
        message(lang, "explain.col.source"),
        message(lang, "explain.col.reason"),
    )
    rows = [
        (
            f"{d.line}:{d.column}",
            d.action,
            d.rule,
            _short(d.source),
            message(lang, "reason." + d.rule),
        )
        for d in result.decisions
    ]
    widths = [max(_width(header[c]), *(_width(r[c]) for r in rows)) for c in range(4)]
    lines = []
    for row in (header, *rows):
        cells = [_pad(row[c], widths[c]) for c in range(4)] + [row[4]]
        lines.append("  ".join(cells).rstrip())
    lines.append("")
    lines.append(message(lang, "explain.summary", total=len(result.decisions), path=path))
    return "\n".join(lines) + "\n"


def _json_report(result: Result, path: str, profile: str, lang: str) -> str:
    decisions = []
    for d in result.decisions:
        item = asdict(d)
        item["reason"] = message(lang, "reason." + d.rule)
        decisions.append(item)
    report = {
        "file": path,
        "profile": profile,
        "changed": result.changed,
        "text": result.text,
        "decisions": decisions,
    }
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def _write(stream: object, text: str) -> None:
    write = getattr(stream, "write")
    write(text)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the exit status (0, 1 or 2)."""
    args_in = list(sys.argv[1:] if argv is None else argv)
    lang = resolve_lang(_prescan_lang(args_in), os.environ)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    try:
        args = _build_parser().parse_intermixed_args(args_in)
        if args.lang is not None:
            if args.lang not in LANGS:
                raise _Fail(message(lang, "error.lang", value=args.lang))
        if args.help:
            _write(sys.stdout, message(lang, "help.text"))
            return 0
        if args.version:
            _write(sys.stdout, f"mathfence {__version__}\n")
            return 0
        if args.profile not in PROFILES:
            raise _Fail(message(lang, "error.profile", value=args.profile, choices=", ".join(PROFILES)))
        if args.fmt not in _FORMATS:
            raise _Fail(message(lang, "error.format", value=args.fmt))
        paths = args.files or ["-"]
        if (args.explain or args.fmt == "json") and not args.check and len(paths) > 1:
            option = "--explain" if args.explain else "--format json"
            raise _Fail(message(lang, "error.single_input", option=option))
        return _run(args, paths, lang)
    except _UsageError as exc:
        _write(sys.stderr, message(lang, exc.key, **exc.params) + "\n")
        return 2
    except _Fail as exc:
        _write(sys.stderr, str(exc) + "\n")
        return 2


def _run(args: argparse.Namespace, paths: list[str], lang: str) -> int:
    if args.check:
        changed = 0
        for path in paths:
            if analyze(_read(path, lang), profile=args.profile).changed:
                changed += 1
                _write(sys.stdout, message(lang, "check.would_change", path=_name(path, lang)) + "\n")
        if not changed:
            _write(sys.stdout, message(lang, "check.clean", count=len(paths)) + "\n")
        return 1 if changed else 0
    outputs = []
    for path in paths:
        result = analyze(_read(path, lang), profile=args.profile)
        name = _name(path, lang)
        if args.fmt == "json":
            outputs.append(_json_report(result, name, args.profile, lang))
        elif args.explain:
            outputs.append(_explain_table(result, name, lang))
        elif len(paths) > 1:
            outputs.append(f"==> {name} <==\n{result.text}" + ("" if result.text.endswith("\n") else "\n"))
        else:
            outputs.append(result.text)
    _write(sys.stdout, "".join(outputs))
    return 0


def _name(path: str, lang: str) -> str:
    return message(lang, "stdin.name") if path == "-" else path


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
