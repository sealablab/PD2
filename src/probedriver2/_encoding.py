"""Register encoding for ProbeDriver2.

All values traveling to the Moku:Go are 32-bit unsigned integers.  The RTL
interprets specific bit fields per `docs/DESIGN_SPEC.md` §6.3.  This module
is the single source of truth for those conversions and the only place where
platform scaling constants live.
"""

from __future__ import annotations

# Platform scaling (DESIGN_SPEC.md §2.1, Moku:Go).
VOLTS_TO_LSB = 6550.4
CYCLES_PER_US = 31.25

# Field limits (DESIGN_SPEC.md §6.3).
SIGNED16_MIN = -32768
SIGNED16_MAX = 32767
DURATION_MIN = 0
DURATION_MAX = 65535

# control[0] bit positions.
ARM_BIT = 31
RESET_BIT = 30


def volts_to_lsb(volts: float) -> int:
    """Convert a voltage to signed 16-bit LSB code."""
    lsb = round(volts * VOLTS_TO_LSB)
    if not SIGNED16_MIN <= lsb <= SIGNED16_MAX:
        raise ValueError(
            f"voltage {volts:g} V → {lsb} LSB is outside signed 16-bit range "
            f"[{SIGNED16_MIN}, {SIGNED16_MAX}]"
        )
    return lsb


def microseconds_to_cycles(time_us: float) -> int:
    """Convert microseconds to 31.25 MHz clock cycles (unsigned 16-bit)."""
    cycles = round(time_us * CYCLES_PER_US)
    if not DURATION_MIN <= cycles <= DURATION_MAX:
        raise ValueError(
            f"duration {time_us:g} µs → {cycles} cycles is outside "
            f"unsigned 16-bit range [{DURATION_MIN}, {DURATION_MAX}]"
        )
    return cycles


def pack_signed16(value: int) -> int:
    """Pack a signed 16-bit value into the low 16 bits of a uint32."""
    if not SIGNED16_MIN <= value <= SIGNED16_MAX:
        raise ValueError(f"value {value} outside signed 16-bit range")
    return value & 0xFFFF


def pack_unsigned16(value: int) -> int:
    """Pack an unsigned 16-bit value into the low 16 bits of a uint32."""
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"value {value} outside unsigned 16-bit range")
    return value & 0xFFFF


def pack_control0(*, arm: bool, reset: bool) -> int:
    """Build control[0] from ARM (bit 31) and RESET (bit 30) flags.

    Bits [29:0] are reserved and written as zero.  Bit 30 is held *high*
    while the host is preparing parameters; RESET-latching happens on the
    high→low edge inside the RTL (DESIGN_SPEC.md §6.3, DR-1).
    """
    word = 0
    if arm:
        word |= 1 << ARM_BIT
    if reset:
        word |= 1 << RESET_BIT
    return word


def fsm_state_from_status0(value: int) -> int:
    """Extract bits [4:0] from a status[0] read (DESIGN_SPEC.md §6.4)."""
    return value & 0x1F
