"""ProbeDriver2 — Python host driver for the Moku:Go custom instrument.

See ``docs/DESIGN_SPEC.md`` for the underlying hardware design.
"""

from ._driver import ProbeDriver2
from ._state import State

__all__ = ["ProbeDriver2", "State"]
__version__ = "0.1.0"
