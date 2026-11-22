"""AC-10: zero runtime dependencies and the quick-start example."""

import re
from pathlib import Path

import mathfence

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_quick_start_example():
    assert mathfence.normalize("It costs $5 and $10, area $x^2$.") == "It costs \\$5 and \\$10, area $x^2$."


def test_no_runtime_dependencies():
    assert re.search(r"^dependencies\s*=\s*\[\s*\]\s*$", PYPROJECT, re.MULTILINE)


def test_dev_dependencies_are_pinned_to_the_probed_versions():
    assert "markdown-it-py==4.3.0" in PYPROJECT
    assert "mdit-py-plugins==0.7.0" in PYPROJECT


def test_package_imports_only_the_standard_library():
    stdlib_only = {"__future__", "re", "json", "os", "sys", "argparse", "dataclasses", "bisect", "typing", "collections", "unicodedata"}
    for path in (ROOT / "src" / "mathfence").glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w]*)", line)
            if m and not line.lstrip().startswith("from ."):
                assert m.group(1) in stdlib_only | {"mathfence"}, (path.name, line)


def test_version_matches_pyproject():
    m = re.search(r'^version\s*=\s*"([^"]+)"', PYPROJECT, re.MULTILINE)
    assert m and m.group(1) == mathfence.__version__


def test_public_api():
    for name in mathfence.__all__:
        assert hasattr(mathfence, name)
    assert (ROOT / "src" / "mathfence" / "py.typed").exists()


def test_entry_point_is_declared():
    assert 'mathfence = "mathfence.cli:main"' in PYPROJECT
