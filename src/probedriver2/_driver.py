"""ProbeDriver2 host-side driver for a Moku:Go custom instrument.

Implements the operational concept of DESIGN_SPEC.md §2.3 over the Moku Cloud
Compile control/status register interface defined in §6.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from . import _encoding as enc
from ._state import State

if TYPE_CHECKING:
    from moku.instruments import CustomInstrument

# Control register addresses (DESIGN_SPEC.md §6.3).
CTRL_FLAGS = 0
CTRL_TRIGGER_V = 1
CTRL_INTENSITY_V = 2
CTRL_THRESHOLD_V = 3
CTRL_DURATION = 4


class ProbeDriver2:
    """Host driver for the ProbeDriver2 Moku:Go custom instrument.

    Typical use::

        with ProbeDriver2("192.168.1.42", "bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz") as pd:
            pd.configure(
                trigger_volts=2.5,
                intensity_volts=4.0,
                threshold_volts=1.0,
                duration_us=10.0,
            )
            pd.arm()
            pd.fire_and_wait()
    """

    def __init__(
        self,
        ip: str,
        bitstream: str | Path,
        *,
        force_connect: bool = False,
    ) -> None:
        # Imported lazily so the module is importable without `moku` installed
        # (e.g. for unit-testing the encoding helpers).
        from moku.instruments import CustomInstrument

        self._ci: CustomInstrument = CustomInstrument(
            ip,
            bitstream=str(bitstream),
            force_connect=force_connect,
        )
        # Track ARM state in the host so reset() can preserve it across the
        # two-write RESET-edge sequence (DR-1).
        self._armed = False
        # Sync hardware to a known starting point.
        self._write_flags(arm=False, reset=False)

    # ------------------------------------------------------------------
    # Context-manager / lifecycle
    # ------------------------------------------------------------------

    def __enter__(self) -> "ProbeDriver2":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Release the Moku for other clients."""
        relinquish = getattr(self._ci, "relinquish_ownership", None)
        if relinquish is not None:
            relinquish()

    @property
    def ci(self) -> "CustomInstrument":
        """Underlying Moku CustomInstrument handle (escape hatch)."""
        return self._ci

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(
        self,
        *,
        trigger_volts: float,
        intensity_volts: float,
        threshold_volts: float,
        duration_us: float,
    ) -> None:
        """Stage parameters into control[1..4] and pulse RESET to latch them.

        After this call the FSM is in S_Idle (or S_Reset transitioning to
        S_Idle on the next clock).  ARM is left in its prior state — call
        :meth:`arm` separately to enable outputs.
        """
        trigger_lsb = enc.volts_to_lsb(trigger_volts)
        intensity_lsb = enc.volts_to_lsb(intensity_volts)
        threshold_lsb = enc.volts_to_lsb(threshold_volts)
        duration_cycles = enc.microseconds_to_cycles(duration_us)

        # Write parameter registers first; RTL only reads them on the latch edge.
        # CustomInstrument.set_controls takes a list of {"id", "value"} maps.
        self._ci.set_controls(
            [
                {"id": CTRL_TRIGGER_V, "value": enc.pack_signed16(trigger_lsb)},
                {"id": CTRL_INTENSITY_V, "value": enc.pack_signed16(intensity_lsb)},
                {"id": CTRL_THRESHOLD_V, "value": enc.pack_signed16(threshold_lsb)},
                {"id": CTRL_DURATION, "value": enc.pack_unsigned16(duration_cycles)},
            ]
        )
        # Pulse RESET high→low to latch parameters and re-enter S_Idle.
        self._pulse_reset()

    # ------------------------------------------------------------------
    # ARM / RESET
    # ------------------------------------------------------------------

    def arm(self) -> None:
        """Set ARM=1.  Outputs are now allowed per FSM state."""
        self._armed = True
        self._write_flags(arm=True, reset=False)

    def disarm(self) -> None:
        """Set ARM=0.  Outputs forced to zero combinationally (DR-5)."""
        self._armed = False
        self._write_flags(arm=False, reset=False)

    def reset(self) -> None:
        """Issue a RESET edge: latches control[1..4] and returns FSM to S_Idle.

        ARM state is preserved across the edge.
        """
        self._pulse_reset()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def state(self) -> State:
        """Return the current FSM state (DESIGN_SPEC.md §6.4)."""
        raw = self._read_status0()
        return State(enc.fsm_state_from_status0(raw))

    def wait_for_state(
        self,
        target: State,
        timeout_s: float = 5.0,
        poll_interval_s: float = 0.01,
    ) -> None:
        """Block until `state() == target`, raising TimeoutError on expiry."""
        deadline = time.monotonic() + timeout_s
        while True:
            if self.state() is target:
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"timed out after {timeout_s:g}s waiting for state {target.name}"
                )
            time.sleep(poll_interval_s)

    def fire_and_wait(self, timeout_s: float = 5.0) -> None:
        """Block until the FSM reaches S_Fini (sequence complete)."""
        self.wait_for_state(State.FINI, timeout_s=timeout_s)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_flags(self, *, arm: bool, reset: bool) -> None:
        self._ci.set_control(CTRL_FLAGS, enc.pack_control0(arm=arm, reset=reset))

    def _pulse_reset(self) -> None:
        # RESET is edge-triggered (DR-1): drive high, then low.  Preserve
        # ARM state so a host-side `reset()` does not silently disarm.
        self._write_flags(arm=self._armed, reset=True)
        self._write_flags(arm=self._armed, reset=False)

    def _read_status0(self) -> int:
        """Return the integer value of status[0] from get_status()."""
        snapshot = self._ci.get_status()

        # If the API returns a bare list of status words, index directly.
        if isinstance(snapshot, list) and snapshot:
            return int(snapshot[0])

        # Common shapes the Moku API has used for status:
        #   {"status": [v0, v1, ...]}
        #   {"status": [{"id": 0, "value": v0}, ...]}
        #   {"status_0": v0, "status_1": v1, ...}
        #   {"status0": v0, ...}
        status = snapshot.get("status") if isinstance(snapshot, dict) else None
        if isinstance(status, list) and status:
            first = status[0]
            if isinstance(first, dict) and "value" in first:
                # List-of-{id,value} shape — find id == 0 explicitly so we
                # don't depend on registers arriving in order.
                for entry in status:
                    if entry.get("id") == 0:
                        return int(entry["value"])
                return int(first["value"])
            return int(first)
        if isinstance(status, dict) and 0 in status:
            return int(status[0])

        for key in ("status_0", "status0", "Status0"):
            if isinstance(snapshot, dict) and key in snapshot:
                return int(snapshot[key])

        raise RuntimeError(
            "could not locate status[0] in CustomInstrument.get_status() response; "
            f"keys present: {sorted(snapshot.keys()) if isinstance(snapshot, dict) else type(snapshot).__name__}"
        )
