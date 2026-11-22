"""The approaches mathfence is compared with (research code, not part of the package)."""

from __future__ import annotations

import re


def raw(text: str) -> str:
    """Do nothing: hand the model output to the renderer as it is."""
    return text


def escape_all(text: str) -> str:
    """The forum one-liner: escape every dollar sign."""
    return text.replace("$", "\\$")


def regex_recipe(text: str) -> str:
    """A typical regex recipe: brackets to dollars, then escape a ``$`` before a digit.

    It is a representative composite of the snippets people paste into
    ``utils.py`` files, not a copy of any single project.
    """
    text = re.sub(r"\\\[(.+?)\\\]", r"$$\1$$", text, flags=re.S)
    text = re.sub(r"\\\((.+?)\\\)", r"$\1$", text, flags=re.S)
    return re.sub(r"(?<!\\)\$(?=\d)", r"\\$", text)
