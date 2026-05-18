---
created: 2026-05-18
modified: 2026-05-18 17:28:40
accessed: 2026-05-18 17:31:45
---
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This repo contains **two coupled components** that together make up ProbeDriver2, a voltage-triggered dual-output pulse generator for the Moku:Go platform (NewAE Chipshouter EMFI driver):

- **`design.v`** — SystemVerilog RTL implementing the `CustomInstrument` module that runs on the Moku:Go FPGA. Compiled to the bitstream in `bin/`.
- **`src/probedriver2/`** — Python host driver that talks to the running instrument via the Moku Cloud Compile control/status register interface (`moku` PyPI package).
- **`docs/DESIGN_SPEC.md`** — Formal design spec (numbered DR-* requirements). `README.md` is the user-facing behavioral overview.
- **`bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz`** — Pre-built bitstream; the Python driver loads this onto the Moku.

There is no test suite, lint config, or build script. The RTL bitstream is built externally (Moku Cloud Compile) and committed; the Python package is built via hatchling.

## Common commands

```bash
# Install Python driver (editable)
pip install -e .

# Run the CLI driver against a Moku:Go
python -m probedriver2 \
    --ip <moku-ip> \
    --bitstream bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz \
    --trigger 2.5 --intensity 4.0 --threshold 1.0 --duration 10
```

The RTL has `/* verilator lint_off UNUSEDSIGNAL */` annotated, suggesting verilator-compatible. No build target is wired up here, though.

## Architecture — the register contract

The RTL and the Python driver are decoupled and communicate **only** through the Moku custom-instrument register interface: 16 × 32-bit `control[]` (host→FPGA) and 16 × 32-bit `status[]` (FPGA→host). When changing behavior on one side, the other side must be updated in lockstep. The contract lives in `docs/DESIGN_SPEC.md` §6.3–§6.4.

**`src/probedriver2/_encoding.py` is the single source of truth** for register bit-packing and platform scaling constants (`VOLTS_TO_LSB = 6550.4`, `CYCLES_PER_US = 31.25`). Do not duplicate these elsewhere.

### Control register layout

| Reg | Bits | Field | Notes |
|---|---|---|---|
| `control[0]` | [31] | ARM | Read continuously; ARM=0 forces outputs to 0 combinationally |
| `control[0]` | [30] | RESET | **Edge-triggered** — high→low transition latches control[1..4] |
| `control[1..4]` | [15:0] | trigger_v, intensity_v, threshold_v, duration | Latched only on RESET edge |

### Status register

`status[0][4:0]` reports the FSM state. The `State` IntEnum in `_state.py` mirrors the RTL `localparam` values in `design.v` (RESET=0x00, IDLE=0x01, FIRE=0x02, COOL=0x03, FINI=0x04).

## Architecture — operational invariants

A few subtle behaviors that recur in both RTL and driver and are easy to break:

1. **RESET is edge-triggered, not level.** `_driver.py::_pulse_reset` writes the flag high then low; the RTL latches `control[1..4]` only on the high→low transition (`design.v`: `reset_edge_w = reset_cmd_prev_r & ~reset_cmd_w`). Configuration must be written *before* pulsing RESET — see `ProbeDriver2.configure`.

2. **`_pulse_reset` preserves the host-tracked ARM state** (`self._armed`). A `reset()` call must not silently disarm. If you add new host-side flags, they must be preserved across this two-write sequence the same way.

3. **ARM blanking is combinational in the RTL** (`assign outputa = arm_w ? out_a_r : 16'sd0`). The FSM continues to advance internally regardless of ARM; ARM only gates the output drivers.

4. **Trigger is strict greater-than**, not ≥ (`inputa > threshold_v_r`). Boundary tests in `README.md` "Test Plan" depend on this.

5. **Cooldown is hardware-enforced as `duration × 2`** via `cooldown_target_w = {duration_r, 1'b0}` (17-bit, no overflow). The host cannot configure cooldown independently.

6. **S_FINI is terminal.** The FSM holds in FINI with zero outputs until the next RESET edge. The host's `fire_and_wait` polls for FINI; do not assume the FSM auto-returns to IDLE.

7. **`duration = 0` is a legal edge case** — both FIRE and COOL collapse to zero cycles. Encoding validates `0 ≤ duration ≤ 65535`.

## Working with the Moku status response shape

`_driver.py::_read_status0` tolerates multiple shapes the Moku `getters()` API has returned across versions (`{"status": [...]}`, `{"status_0": ...}`, etc.). If you see a `RuntimeError: could not locate status[0]`, the Moku SDK shape changed — extend this helper rather than papering over it at the call site.
