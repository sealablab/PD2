"""Minimal CLI for ProbeDriver2.

Example::

    python -m probedriver2 \
        --ip 192.168.1.42 \
        --bitstream bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz \
        --trigger 2.5 --intensity 4.0 --threshold 1.0 --duration 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ProbeDriver2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="probedriver2")
    parser.add_argument("--ip", required=True, help="Moku:Go IP address")
    parser.add_argument(
        "--bitstream",
        required=True,
        type=Path,
        help="Path to ProbeDriver2 bitstream tarball",
    )
    parser.add_argument("--trigger", type=float, required=True, help="outputa voltage during Fire (V)")
    parser.add_argument("--intensity", type=float, required=True, help="outputb voltage during Fire (V)")
    parser.add_argument("--threshold", type=float, required=True, help="inputa trigger threshold (V)")
    parser.add_argument("--duration", type=float, required=True, help="Fire duration (µs)")
    parser.add_argument("--force", action="store_true", help="Force-connect to busy Moku")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for S_Fini")
    args = parser.parse_args(argv)

    with ProbeDriver2(args.ip, args.bitstream, force_connect=args.force) as pd:
        pd.configure(
            trigger_volts=args.trigger,
            intensity_volts=args.intensity,
            threshold_volts=args.threshold,
            duration_us=args.duration,
        )
        pd.arm()
        print(f"Armed.  State: {pd.state().name}.  Waiting for trigger event…")
        pd.fire_and_wait(timeout_s=args.timeout)
        print(f"Sequence complete.  State: {pd.state().name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
