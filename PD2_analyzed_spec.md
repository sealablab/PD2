---
created: 2026-05-18
modified: 2026-05-18 10:58:07
accessed: 2026-05-18 10:58:14
---
# ProbeDriver2

---

## Overview

ProbeDriver2 is a voltage-triggered dual-output pulse generator for the **Moku:Go** platform (31.25 MHz clock, 16-bit signed I/O). Monitors an analog input and, when a configurable threshold is exceeded, generates two independent DC voltage outputs for a specified duration followed by a mandatory cooldown period. Designed for driving fault injection probes (Riscure DS1120 EMFI probe) with single-shot trigger-to-pulse operation.

---

## Architecture

### State Machine

The module operates as a finite state machine with five states:

| State     | Encoding | Behavior |
|:----------|:--------:|:---------|
| `S_Reset` | 0x00     | Latch control[1] through control[4] into internal registers; transition immediately to S_Idle |
| `S_Idle`  | 0x01     | Monitor `inputa`; when `inputa > threshold_v`, transition to S_Fire |
| `S_Fire`  | 0x02     | Drive `outputa = trigger_out_v` and `outputb = intensity_out_v` for `duration` clock cycles; then transition to S_Cool |
| `S_Cool`  | 0x03     | Drive `outputa = 0` and `outputb = 0` for `duration × 2` clock cycles; then transition to S_Fini |
| `S_Fini`  | 0x04     | Drive `outputa = 0` and `outputb = 0` indefinitely; remain in this state until RESET command |

State transitions:
- S_Reset → S_Idle (immediate, on the cycle after RESET edge)
- S_Idle → S_Fire (when `inputa > threshold_v` while ARM is asserted)
- S_Fire → S_Cool (after `duration` clock cycles)
- S_Cool → S_Fini (after `duration × 2` clock cycles)
- Any state → S_Reset (on high-to-low transition of control[0] bit 30)

### Trigger Detection

In S_Idle state, the module continuously compares `inputa` to the latched `threshold_v` parameter. The comparison is strictly greater-than (not greater-or-equal): trigger occurs when `inputa > threshold_v`.

### Output Generation

Output behavior depends on both the current FSM state and the ARM signal (control[0] bit 31):

**When ARM = 1 (armed):**
- S_Fire: `outputa = trigger_out_v`, `outputb = intensity_out_v`
- All other states: `outputa = 0`, `outputb = 0`

**When ARM = 0 (disarmed):**
- All states: `outputa = 0`, `outputb = 0`

The ARM signal provides immediate output blanking regardless of state machine position.

### Timing

**Fire duration:** Outputs driven for exactly `duration` clock cycles (as specified in control[4]).

**Cooldown duration:** Outputs held at zero for exactly `duration × 2` clock cycles.

**Cycle counting:** The first cycle in S_Fire or S_Cool counts as cycle 1; state transition occurs after the final cycle completes.

**Example:** With `duration = 100`:
- Cycle N: Transition to S_Fire, outputs become non-zero
- Cycles N through N+99: Fire state (100 cycles total)
- Cycle N+100: Transition to S_Cool, outputs become zero
- Cycles N+100 through N+299: Cool state (200 cycles total)
- Cycle N+300: Transition to S_Fini

### Parameter Latching

The RESET command (high-to-low transition of control[0] bit 30) captures control[1] through control[4] into internal registers. These latched values remain constant throughout the subsequent Fire/Cool/Fini sequence, regardless of changes to control registers.

**Latched parameters:**
- `trigger_out_v` from control[1][15:0]
- `intensity_out_v` from control[2][15:0]
- `threshold_v` from control[3][15:0]
- `duration` from control[4][15:0]

This ensures that trigger threshold, output voltages, and timing remain stable during a single-shot sequence.

### Edge Case Handling

- **ARM = 0 during operation:** Outputs immediately forced to zero; FSM continues state progression internally
- **Threshold exactly equal:** If `inputa = threshold_v`, trigger does NOT occur (strict greater-than comparison)
- **Duration = 0:** Fire state duration is 0 cycles (immediate transition to Cool); Cool state duration is also 0 cycles (immediate transition to Fini)
- **RESET during Fire/Cool:** FSM immediately returns to S_Reset, re-latches parameters, transitions to S_Idle

---

## Control Registers

All control registers are 32-bit. Control[1] through control[4] are latched on RESET command; control[0] is read continuously every cycle.

| Register   | Bits    | Name            | Format        | Description |
|:-----------|:-------:|:----------------|:--------------|:------------|
| control[0] | [31]    | ARM             | Single-bit    | Output enable: 1 = outputs allowed per FSM state, 0 = outputs forced to zero |
| control[0] | [30]    | RESET           | Single-bit    | High-to-low transition latches control[1:4] and enters S_Reset state |
| control[0] | [29:0]  | reserved        | —             | Reserved for future use |
| control[1] | [15:0]  | trigger_out_v   | Signed 16-bit | DC voltage (LSBs) to drive `outputa` during Fire state |
| control[1] | [31:16] | unused          | —             | Ignored |
| control[2] | [15:0]  | intensity_out_v | Signed 16-bit | DC voltage (LSBs) to drive `outputb` during Fire state |
| control[2] | [31:16] | unused          | —             | Ignored |
| control[3] | [15:0]  | threshold_v     | Signed 16-bit | Trigger threshold (LSBs); Fire triggered when `inputa > threshold_v` in Idle state |
| control[3] | [31:16] | unused          | —             | Ignored |
| control[4] | [15:0]  | duration        | Unsigned 16-bit | Number of clock cycles for Fire state; Cooldown is 2× this value |
| control[4] | [31:16] | unused          | —             | Ignored |

### Control Register Constraints

- **RESET trigger edge:** Parameter latching occurs on the high-to-low transition of control[0] bit 30
- **ARM behavior:** ARM (control[0] bit 31) is read continuously; toggling ARM during operation immediately affects output blanking
- **Duration limits:** `duration` can range from 0 to 65535 cycles (0 to ~2.097 ms at 31.25 MHz)
- **Voltage scaling:** Client software must convert user voltages to LSBs using platform scaling: `LSBs = volts × 6550.4`
- **Duration scaling:** Client software must convert user time (microseconds) to clock cycles: `cycles = time_us × 31.25`

---

## Status Registers

| Register   | Bits   | Name      | Description |
|:-----------|:------:|:----------|:------------|
| status[0]  | [4:0]  | FSM_state | Current state machine encoding (0x00=Reset, 0x01=Idle, 0x02=Fire, 0x03=Cool, 0x04=Fini) |
| status[0]  | [31:5] | reserved  | Reserved for future use |

### Status Register Polling

Client software can poll status[0] bits [4:0] to monitor operation progress:
- 0x01: Waiting for trigger
- 0x02: Fire in progress
- 0x03: Cooldown in progress
- 0x04: Sequence complete

---

## Inputs & Outputs

### Input Signals

| Signal   | Label          | Description |
|:---------|:---------------|:------------|
| `clk`    | Clock          | 31.25 MHz system clock |
| `reset`  | Reset          | Synchronous reset (active high) |
| `inputa` | Trigger Input  | Analog voltage input for threshold comparison (signed 16-bit LSBs) |

### Output Signals

| Signal    | Label             | Description |
|:----------|:------------------|:------------|
| `outputa` | Trigger Voltage   | DC pulse output (trigger voltage during Fire state) |
| `outputb` | Intensity Voltage | DC pulse output (intensity voltage during Fire state) |

### Unused Signal Behaviour

- `inputb` / `inputc` / `inputd`: tied to 0
- `outputc`: tied to 0 (available in 3-slot Moku:Go configuration but unused)
- `outputd`: not available on Moku:Go platform
- `control[5]` through `control[15]`: unused
- `status[1]` through `status[15]`: tied to 0
- `sync`: unused
- `exttrig`: unused

---

## Test Plan

1. **ARM output blanking:** Set ARM=0, verify `outputa` and `outputb` remain zero in all FSM states including Fire state
2. **RESET parameter latch:** Write control[1:4] with test values, assert RESET (1→0 transition), modify control[1:4], verify FSM uses original latched values during Fire state
3. **S_Reset to S_Idle transition:** Verify FSM transitions from S_Reset (0x00) to S_Idle (0x01) immediately (within 1 cycle) after RESET edge
4. **Threshold trigger (above):** In S_Idle with ARM=1, apply `inputa = threshold_v + 1`, verify transition to S_Fire (status[0]=0x02)
5. **Threshold boundary (equal):** In S_Idle with ARM=1, apply `inputa = threshold_v` exactly, verify FSM remains in S_Idle (no trigger)
6. **Threshold boundary (below):** In S_Idle with ARM=1, apply `inputa = threshold_v - 1`, verify FSM remains in S_Idle
7. **Fire duration accuracy:** Configure `duration = 100`, trigger Fire state, verify state remains S_Fire for exactly 100 cycles then transitions to S_Cool on cycle 101
8. **Fire output voltages:** Configure `trigger_out_v = 1000`, `intensity_out_v = 2000`, verify during S_Fire: `outputa = 1000` and `outputb = 2000`
9. **Cooldown duration accuracy:** Configure `duration = 100`, verify S_Cool state lasts exactly 200 cycles (2× duration) then transitions to S_Fini
10. **Cooldown output zero:** Verify `outputa = 0` and `outputb = 0` throughout entire S_Cool state
11. **S_Fini indefinite hold:** Verify FSM remains in S_Fini (status[0]=0x04) indefinitely after cooldown completes, with outputs at zero
12. **RESET from S_Fini:** While in S_Fini state, assert RESET (1→0), verify FSM returns to S_Idle and can trigger new sequence
13. **Zero duration edge case:** Configure `duration = 0`, trigger Fire, verify immediate transition through S_Fire→S_Cool→S_Fini (total 0 cycles Fire, 0 cycles Cool)
14. **ARM toggle during Fire:** Enter S_Fire state, toggle ARM=0 mid-pulse, verify outputs immediately forced to zero; restore ARM=1, verify outputs resume non-zero values
15. **RESET during Fire:** Enter S_Fire state at cycle N, assert RESET at cycle N+50, verify FSM immediately enters S_Reset (interrupts Fire sequence), then transitions to S_Idle
16. **Negative voltage outputs:** Configure `trigger_out_v = -16384`, `intensity_out_v = -8192`, verify signed outputs driven correctly during Fire state
17. **Maximum duration:** Configure `duration = 65535`, verify Fire state lasts 65535 cycles and Cool state lasts 131070 cycles (2× duration, wraps to 16-bit unsigned arithmetic correctly)
18. **Rapid re-arm sequence:** Complete full Fire→Cool→Fini sequence, immediately assert RESET and trigger new sequence, verify correct operation (no residual state)
19. **Status register encoding verification:** Step through FSM states, verify status[0][4:0] reports correct encoding at each state (0x00, 0x01, 0x02, 0x03, 0x04)
20. **Multi-cycle trigger persistence:** Apply `inputa > threshold_v` for 5 consecutive cycles in S_Idle, verify FSM triggers on first cycle and does not re-trigger (single-shot behavior)
