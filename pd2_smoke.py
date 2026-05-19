"""ProbeDriver2 cold smoke test.

Walks the FSM through every state with ARM=0 so the output drivers stay at 0 V
regardless of what is physically connected.  Reports the observed state at each
step and the raw status[0] word so we can see if any reserved bits look wrong.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from probedriver2 import ProbeDriver2
from probedriver2._driver import CTRL_FLAGS, CTRL_TRIGGER_V, CTRL_INTENSITY_V, CTRL_THRESHOLD_V, CTRL_DURATION
from probedriver2._state import State

IP = "192.168.13.199"
BITSTREAM = Path("/Users/johnycsh/DPD/UPD-001/PD2/bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz")


def dump_status(pd: ProbeDriver2, tag: str) -> None:
    raw = pd._read_status0()
    fsm = raw & 0x1F
    try:
        name = State(fsm).name
    except ValueError:
        name = f"UNKNOWN(0x{fsm:02x})"
    reserved = raw & ~0x1F
    print(f"  [{tag:>14}]  status[0]=0x{raw:08x}  fsm=0x{fsm:02x} ({name})"
          f"  reserved_bits=0x{reserved:08x}")


def poll_until(pd: ProbeDriver2, target: State, tag: str, timeout_s: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pd.state() is target:
            dump_status(pd, tag)
            return True
        time.sleep(0.005)
    dump_status(pd, f"{tag} TIMEOUT")
    return False


def main() -> int:
    print(f"Connecting to Moku at {IP} and loading bitstream...")
    print(f"  bitstream: {BITSTREAM.name}")
    try:
        pd = ProbeDriver2(IP, BITSTREAM, force_connect=False)
    except Exception as e:
        print(f"  connect failed: {type(e).__name__}: {e}")
        print("  retrying with force_connect=True...")
        pd = ProbeDriver2(IP, BITSTREAM, force_connect=True)
    print("Connected.\n")

    try:
        # ----- Phase 0 : baseline ------------------------------------------------
        print("Phase 0: post-connect baseline (driver __init__ wrote ARM=0 RESET=0)")
        dump_status(pd, "baseline")
        snap = pd._ci.get_status()
        print(f"  get_status() top-level type: {type(snap).__name__}; "
              f"keys: {sorted(snap.keys()) if isinstance(snap, dict) else 'n/a'}")

        # ----- Phase 1 : configure with non-firing threshold, ARM still off -----
        print("\nPhase 1: configure(trig=2.5V, int=4.0V, thr=2.5V, dur=10us); ARM stays OFF")
        pd.configure(trigger_volts=2.5, intensity_volts=4.0,
                     threshold_volts=2.5, duration_us=10.0)
        # After the RESET edge, FSM should land in IDLE within a few cycles.
        poll_until(pd, State.IDLE, "after configure", timeout_s=0.5)

        # ----- Phase 2 : arm, verify still IDLE (no trigger source) -------------
        print("\nPhase 2: arm with high threshold -> should remain IDLE (no trigger)")
        pd.arm()
        time.sleep(0.05)
        dump_status(pd, "armed/idle")
        if pd.state() is not State.IDLE:
            print("  WARNING: not IDLE after arm with high threshold!")
        pd.disarm()
        dump_status(pd, "disarmed")

        # ----- Phase 3 : force the FSM through FIRE->COOL->FINI, ARM=0 ----------
        # threshold = -4.9V guarantees inputa > threshold for any plausible
        # input level (including floating/0V).  ARM=0 keeps outputs at 0V.
        # Full sequence is FIRE(10us)+COOL(20us)=30us at 31.25MHz — far faster
        # than a network status poll, so the FSM will almost certainly already
        # be in FINI by the time we read.  We only assert that it *reached*
        # FINI, not that we observed every intermediate state.
        print("\nPhase 3: force FSM cycle with threshold=-4.9V, ARM stays OFF (safe)")
        pd.configure(trigger_volts=2.5, intensity_volts=4.0,
                     threshold_volts=-4.9, duration_us=10.0)
        dump_status(pd, "post-reconfig")
        ok_fini = poll_until(pd, State.FINI, "reached FINI", timeout_s=0.5)
        if not ok_fini:
            print("  FAIL: FSM never reached FINI — trigger comparator or FSM stuck")

        # ----- Phase 4 : verify FINI is terminal --------------------------------
        print("\nPhase 4: confirm FINI is sticky")
        time.sleep(0.1)
        dump_status(pd, "FINI sticky?")
        st = pd.state()
        if st is not State.FINI:
            print(f"  WARNING: FSM left FINI on its own (now {st.name}) — RTL bug?")
        else:
            print("  FINI held (terminal as expected)")

        # ----- Phase 5 : pulse RESET, expect IDLE again -------------------------
        print("\nPhase 5: pulse RESET from FINI -> expect IDLE")
        pd.reset()
        poll_until(pd, State.IDLE, "post-reset", timeout_s=0.2)

        print("\nSummary:")
        print(f"  Phase 3 reached FINI : {ok_fini}")
        print("Smoke test done.")
        return 0
    finally:
        pd.close()


if __name__ == "__main__":
    sys.exit(main())
