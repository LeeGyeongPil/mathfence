"""mathfence: make LLM Markdown safe for ``$``-math renderers.

>>> import mathfence
>>> mathfence.normalize("It costs $5 and $10, area $x^2$.")
'It costs \\\\$5 and \\\\$10, area $x^2$.'
"""

from .core import PROFILES, Decision, Result, analyze, normalize
from .stream import StreamNormalizer, StreamStats

__version__ = "0.1.2"

__all__ = [
    "PROFILES",
    "Decision",
    "Result",
    "StreamNormalizer",
    "StreamStats",
    "__version__",
    "analyze",
    "normalize",
]
