"""Incremental normalization for token streams."""

from __future__ import annotations

from dataclasses import dataclass

from . import regions
from .core import check_input, run


@dataclass
class StreamStats:
    """Work counters of a :class:`StreamNormalizer`."""

    #: Characters passed through the normalizer so far (all feeds summed).
    reprocessed_chars: int = 0
    #: Characters already settled and never looked at again.
    committed_chars: int = 0


class StreamNormalizer:
    """Normalize a growing answer chunk by chunk.

    ``feed(chunk)`` returns the text to show *now*.  It never shows math that
    the finished answer would not contain: a closing ``$`` at the very end is
    held back (written as ``\\$``) until the next character arrives, and an
    unclosed code span is left alone.  Text before the last paragraph break
    that is outside code, HTML and lists is settled and not processed again.

    >>> sn = StreamNormalizer()
    >>> sn.feed("Pay $5 if $")
    'Pay \\\\$5 if \\\\$'
    """

    def __init__(self, *, profile: str = "remark") -> None:
        check_input("", profile)
        self.profile = profile
        self.stats = StreamStats()
        self._raw: list[str] = []
        self._committed = ""  # normalized text of settled paragraphs
        self._tail = ""  # raw text not settled yet
        self._finished = False

    @property
    def text(self) -> str:
        """All raw text received so far."""
        return "".join(self._raw)

    def feed(self, chunk: str) -> str:
        """Add ``chunk`` and return the normalized text of everything received.

        Raises:
            RuntimeError: ``finish()`` was already called.
            TypeError: ``chunk`` is not a ``str``.
        """
        if self._finished:
            raise RuntimeError("feed() called after finish(); create a new StreamNormalizer for the next answer")
        if not isinstance(chunk, str):
            raise TypeError(f"chunk must be str, got {type(chunk).__name__}")
        self._raw.append(chunk)
        self._tail += chunk
        if "\n" in chunk:
            boundaries = regions.scan(self._tail, streaming=True).boundaries
            if boundaries:
                cut = boundaries[-1]
                settled, self._tail = self._tail[:cut], self._tail[cut:]
                self._committed += run(settled, self.profile, False).text
                self.stats.reprocessed_chars += len(settled)
                self.stats.committed_chars += len(settled)
        self.stats.reprocessed_chars += len(self._tail)
        return self._committed + run(self._tail, self.profile, True).text

    def finish(self) -> str:
        """Return the final normalized text (equal to ``normalize(self.text)``)."""
        self._finished = True
        return run(self.text, self.profile, False).text
