"""FSM state encoding for ProbeDriver2 (DESIGN_SPEC.md §5)."""

from __future__ import annotations

from enum import IntEnum


class State(IntEnum):
    """ProbeDriver2 FSM state, matching `status[0][4:0]`."""

    RESET = 0x00
    IDLE = 0x01
    FIRE = 0x02
    COOL = 0x03
    FINI = 0x04

    @property
    def is_terminal(self) -> bool:
        return self is State.FINI

    @property
    def is_running(self) -> bool:
        return self in (State.FIRE, State.COOL)
