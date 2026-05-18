---
created: 2026-05-18
modified: 2026-05-18 17:14:46
accessed: 2026-05-18 17:28:04
---
# ProbeDriver2 — Design Specification

| Field        | Value                                          |
|:-------------|:-----------------------------------------------|
| Document     | ProbeDriver2 Hardware Design Specification     |
| Module       | `CustomInstrument` (Moku:Go custom instrument) |
| Version      | 1.0                                            |
| Date         | 2026-05-18                                     |
| Author       | _Project maintainers_                          |
| Status       | Draft                                          |
| Source RTL   | `design.v` (root of repository)                |
| Companion    | `README.md` (user-facing behavioral overview)  |

## Revision History

| Version | Date       | Author     | Summary                              |
|:--------|:-----------|:-----------|:-------------------------------------|
| 1.0     | 2026-05-18 | (initial)  | Initial formal design specification. |

## Glossary

| Term     | Definition                                                                  |
|:---------|:----------------------------------------------------------------------------|
| ARM      | Output-enable signal (control[0] bit 31); when low, outputs are forced 0.   |
| CDC      | Clock-Domain Crossing.                                                      |
| EMFI     | ElectroMagnetic Fault Injection — pulsed-field probing of microelectronics. |
| FSM      | Finite State Machine.                                                       |
| LSB      | Least-Significant Bit; also used as the unit of the Moku:Go DAC/ADC code.   |
| Moku:Go  | Liquid Instruments programmable instrument platform (Zynq-class FPGA host). |
| RESET    | Per-instrument command (control[0] bit 30); distinct from system `reset`.   |
| RTL      | Register-Transfer Level (the SystemVerilog source).                         |
| SEU      | Single-Event Upset — radiation-induced flip-flop bit error.                 |

---

## 1. Introduction

### 1.1 Purpose

This document specifies the design of the **ProbeDriver2** module: a voltage-triggered, dual-output, single-shot DC pulse generator implemented as a Moku:Go custom instrument. It captures the architectural intent, interface contract, design rationale, and verification approach in sufficient detail that:

- A reviewer can verify that `design.v` implements the intended behavior without reverse-engineering the RTL.
- An engineer can re-implement or port the design to another FPGA platform from this document alone.
- Every test in the verification plan is traceable to a numbered functional requirement.

### 1.2 Scope

In scope: the `CustomInstrument` module defined in `design.v`, including its FSM, register interface, timing behavior, and verification plan.

Out of scope: the Moku:Go platform wrapper, the host-side Python client, electrical characteristics of the analog front-end, and the downstream EMFI probe hardware.

### 1.3 Intended Use Case

ProbeDriver2 drives a NewAE Chipshouter EMFI probe (or similar pulsed-field injector) in a fault-injection research workflow. The instrument observes an analog signal — typically a power-rail event, a clock glitch trigger, or an external comparator output — and, when that signal crosses a programmable threshold, emits a single timed pulse on two independent DC outputs:

- `outputa` carries a **trigger voltage** intended for the probe's gate or arm input.
- `outputb` carries an **intensity voltage** intended for the probe's amplitude control.

A mandatory cooldown of twice the fire duration follows each pulse, and the instrument latches in a terminal state until the host explicitly re-arms it. This one-shot discipline prevents repeated firing from residual analog noise and limits thermal stress on the probe.

### 1.4 References

| Ref | Document                              | Location           |
|:----|:--------------------------------------|:-------------------|
| R1  | ProbeDriver2 README                   | `../README.md`     |
| R2  | ProbeDriver2 RTL                      | `../design.v`      |
| R3  | Moku:Go Custom Instrument bitstream   | `../bin/9856d70_mokugo_4.2.2_2_bitstreams.tar.xz` |
| R4  | Moku:Go Cloud Compile platform docs   | Liquid Instruments (external) |

---

## 2. System Context

### 2.1 Platform

| Property         | Value                                       |
|:-----------------|:--------------------------------------------|
| Target           | Moku:Go (Liquid Instruments)                |
| System clock     | 31.25 MHz (period 32 ns)                    |
| Analog I/O width | 16-bit signed, two's complement             |
| Voltage scaling  | `LSBs = volts × 6550.4`                     |
| Time scaling     | `cycles = microseconds × 31.25`             |
| Register API     | 16 × 32-bit `control`, 16 × 32-bit `status` |

### 2.2 External Interfaces

The module signature is fixed by the Moku:Go custom-instrument wrapper. ProbeDriver2 uses a strict subset of this contract:

```
                  +----------------------------+
   clk     ──────►│                            │
   reset   ──────►│                            │
   inputa  ──────►│        ProbeDriver2        │──────► outputa  (trigger voltage)
   control ◄═════►│      (CustomInstrument)    │──────► outputb  (intensity voltage)
   status  ◄═════►│                            │
                  +----------------------------+
       inputb, inputc, inputd, exttrig, sync : not used
       outputc : tied to 0     outputd : not available on Moku:Go
```

### 2.3 Operational Concept

A complete operating cycle is:

1. **Configure** — host writes parameters into `control[1..4]`.
2. **Latch** — host pulses control[0] bit 30 high then low; the falling edge captures parameters.
3. **Arm** — host sets control[0] bit 31 = 1.
4. **Wait** — FSM sits in S_Idle, comparing `inputa` to the latched threshold.
5. **Fire** — when `inputa > threshold_v`, FSM emits both DC voltages for `duration` cycles.
6. **Cool** — outputs return to zero for `2 × duration` cycles.
7. **Finish** — FSM enters S_Fini and holds outputs at zero until the host issues another RESET.

---

## 3. Functional Requirements

| ID    | Requirement                                                                                                                                                | Verification |
|:------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------|
| FR-1  | On the falling edge of control[0] bit 30, the module shall capture control[1..4][15:0] into internal registers and enter S_Reset.                          | TC-2, TC-3   |
| FR-2  | In S_Idle, the module shall transition to S_Fire iff `inputa > threshold_v` (strict, signed) and ARM = 1.                                                  | TC-4, TC-5, TC-6 |
| FR-3  | S_Fire shall persist for exactly `duration` clock cycles, then transition to S_Cool.                                                                       | TC-7, TC-17  |
| FR-4  | S_Cool shall persist for exactly `2 × duration` clock cycles, then transition to S_Fini.                                                                   | TC-9, TC-17  |
| FR-5  | S_Fini shall be terminal: the module shall remain in S_Fini, with outputs at zero, until a RESET edge is received.                                         | TC-11, TC-12 |
| FR-6  | When ARM = 0, both `outputa` and `outputb` shall be zero in every state, with zero clock-cycle latency from ARM going low.                                 | TC-1, TC-14  |
| FR-7  | `status[0][4:0]` shall report the current FSM state code (0x00..0x04) on every clock cycle.                                                                | TC-19        |
| FR-8  | While in S_Fire, S_Cool, or S_Fini, the module shall not re-enter S_Fire from a threshold crossing; re-fire requires a RESET.                              | TC-18, TC-20 |
| FR-9  | A RESET edge shall return the FSM to S_Reset (and thus S_Idle on the next cycle) from any state.                                                           | TC-12, TC-15 |
| FR-10 | `trigger_out_v` and `intensity_out_v` shall be interpreted as signed 16-bit values, supporting the full range −32768..+32767.                              | TC-16        |

### 3.1 Non-Functional Requirements

| ID    | Requirement                                                                                                              |
|:------|:-------------------------------------------------------------------------------------------------------------------------|
| NFR-1 | All timed behavior shall be cycle-accurate and deterministic — no PLL, no asynchronous events, no non-deterministic FIFO.|
| NFR-2 | Threshold-crossing to state transition shall complete in 1 clock cycle.                                                  |
| NFR-3 | Internal state shall fit in: one 17-bit counter, four 16-bit parameter registers, two 16-bit output registers, one 5-bit state register, one 1-bit RESET history bit. |
| NFR-4 | The module shall contain no combinational feedback loops; all state lives in flip-flops clocked by `clk`.                |
| NFR-5 | A `reset = 1` system-reset shall force the FSM to S_Reset, the counter to 0, and all latched parameters and outputs to 0.|

---

## 4. Architecture

### 4.1 Block Diagram

```
   control[0][31] ──── ARM ───────────────────────────────────────┐
                                                                  │
   control[0][30] ─► [reset_edge detector] ── reset_edge_w ──┐    │
                                                             ▼    │
   control[1..4][15:0] ───────────────► [Parameter Latch Bank]    │
                                          │ trigger_out_v_r        │
                                          │ intensity_out_v_r      │
                                          │ threshold_v_r          │
                                          │ duration_r             │
                                          ▼                         │
                       ┌──────────────────────────────────────┐    │
   inputa ───► [>]  ─► │              MAIN FSM                │    │
                       │  S_Reset ─► S_Idle ─► S_Fire ─►      │    │
                       │           S_Cool ─► S_Fini           │    │
                       └─────────┬────────────────────────────┘    │
                                 │ state_r, out_a_r, out_b_r        │
                                 ▼                                  ▼
                       [output mux ─ register]    [ARM combinational gate]
                                 │                            │
                                 ▼                            ▼
                          (out_a_r,out_b_r) ──── AND ────► outputa,outputb
                                                    │
                                 ┌──────────────────┘
                                 │
   status[0][4:0] ◄── state_r ───┘
```

### 4.2 Major Blocks

**Control signal extraction (combinational)** — `arm_w` and `reset_cmd_w` are continuous reads of control[0] bits 31 and 30. They drive the edge detector and the output gate respectively.

**RESET edge detector** — A one-bit register (`reset_cmd_prev_r`) captures the previous-cycle value of `reset_cmd_w`. The falling edge `reset_edge_w = reset_cmd_prev_r & ~reset_cmd_w` is asserted for exactly one cycle per host-issued RESET pulse.

**Parameter latch bank** — Four signed/unsigned registers (`trigger_out_v_r`, `intensity_out_v_r`, `threshold_v_r`, `duration_r`). They are updated only on `reset_edge_w` (or on system reset). All downstream logic reads from these registers, not from `control[]` directly.

**Main FSM** — Five states encoded sequentially 0x00..0x04. Transitions are computed on the rising edge of `clk` based on `state_r`, `cycle_count_r`, `trigger_w`, and `arm_w`. See §5 for the full state table.

**Cycle counter** — A 17-bit register (`cycle_count_r`). Width is chosen so that `2 × max(duration) = 131070` fits without overflow (see DR-3).

**Output register + ARM gate** — `out_a_r` and `out_b_r` are 16-bit signed registers driven by the FSM. Outputs are gated combinationally by `arm_w` so that disarming forces outputs to zero in the same cycle, regardless of FSM state.

### 4.3 Per-Cycle Data Flow

On each rising edge of `clk` (with `reset = 0`):

1. `reset_cmd_prev_r` samples the previous-cycle `reset_cmd_w`.
2. `reset_edge_w` is evaluated combinationally and gates whether the cycle is a "latch cycle" or a "FSM cycle."
3. If latch cycle: parameter latches update, `state_r ← S_Reset`, `cycle_count_r ← 0`, outputs cleared.
4. If FSM cycle: the case statement on `state_r` updates `state_r`, `cycle_count_r`, `out_a_r`, `out_b_r`.
5. Combinationally, `outputa = arm_w ? out_a_r : 0` and likewise for `outputb`; `status[0] = {27'b0, state_r}`.

---

## 5. FSM Specification

### 5.1 State Diagram

```
                  ┌──────────────────────────────────────┐
                  │            reset_edge_w              │
                  │  (from any state, including S_Reset) │
                  ▼                                      │
              ┌────────┐                                 │
              │ S_RESET│ ─── unconditional, next cycle ──┤
              │  0x00  │                                 │
              └────┬───┘                                 │
                   ▼                                     │
              ┌────────┐                                 │
              │ S_IDLE │ ◄───────────────────────────────┤
              │  0x01  │                                 │
              └────┬───┘                                 │
                   │ trigger_w & arm_w                   │
                   ▼                                     │
              ┌────────┐                                 │
              │ S_FIRE │                                 │
              │  0x02  │                                 │
              └────┬───┘                                 │
                   │ cycle_count_r >= duration_r         │
                   ▼                                     │
              ┌────────┐                                 │
              │ S_COOL │                                 │
              │  0x03  │                                 │
              └────┬───┘                                 │
                   │ cycle_count_r >= duration_r << 1    │
                   ▼                                     │
              ┌────────┐                                 │
              │ S_FINI │ ────────────────────────────────┘
              │  0x04  │   (waits for next reset_edge_w)
              └────────┘
```

### 5.2 State Table

| State    | Code  | Entry actions                           | Do-actions (each cycle)                                    | Exit condition                              | Outputs in state         |
|:---------|:------|:----------------------------------------|:------------------------------------------------------------|:--------------------------------------------|:-------------------------|
| S_Reset  | 0x00  | (entered only via reset_edge_w or system reset; latches parameters; clears counter) | None — single-cycle pass-through.                          | Unconditional, on next cycle.                | 0, 0                     |
| S_Idle   | 0x01  | None                                    | Compare `inputa > threshold_v_r`.                          | `trigger_w & arm_w` → S_Fire.                | 0, 0                     |
| S_Fire   | 0x02  | `cycle_count_r ← 1`; drive outputs.     | Hold outputs; increment counter.                           | `cycle_count_r >= duration_r` → S_Cool.      | `trigger_out_v_r`, `intensity_out_v_r` |
| S_Cool   | 0x03  | `cycle_count_r ← 1`; clear outputs.     | Hold outputs at 0; increment counter.                      | `cycle_count_r >= 2 × duration_r` → S_Fini.  | 0, 0                     |
| S_Fini   | 0x04  | None                                    | Hold outputs at 0.                                         | `reset_edge_w` → S_Reset (handled globally). | 0, 0                     |

Note: `out_a_r` and `out_b_r` are the registered outputs; the ARM gate may force the externally-observable `outputa`/`outputb` to 0 regardless of state.

### 5.3 Full Transition Table

| From state | Event                                    | Next state | Notes                                  |
|:-----------|:-----------------------------------------|:-----------|:---------------------------------------|
| Any        | system `reset = 1`                       | S_Reset    | Synchronous; clears all registers.     |
| Any        | `reset_edge_w`                           | S_Reset    | Latches control[1..4]; clears counter. |
| S_Reset    | (else)                                   | S_Idle     | Unconditional next cycle.              |
| S_Idle     | `trigger_w & arm_w`                      | S_Fire     | Counter loads with 1.                  |
| S_Idle     | `!trigger_w | !arm_w`                    | S_Idle     | Hold.                                  |
| S_Fire     | `cycle_count_r >= duration_r`            | S_Cool     | Counter resets to 1.                   |
| S_Fire     | `cycle_count_r <  duration_r`            | S_Fire     | Counter increments.                    |
| S_Cool     | `cycle_count_r >= duration_r << 1`       | S_Fini     | Counter clears to 0.                   |
| S_Cool     | `cycle_count_r <  duration_r << 1`       | S_Cool     | Counter increments.                    |
| S_Fini     | (else)                                   | S_Fini     | Hold until reset edge.                 |
| (unknown)  | (else)                                   | S_Reset    | Defensive default — see DR-9.          |

### 5.4 State Encoding Rationale

Sequential 5-bit encoding (0x00..0x04) was chosen over one-hot for two reasons:
1. **Status readability** — the host polls `status[0][4:0]` and benefits from a contiguous numeric mapping (0=Reset, 1=Idle, 2=Fire, 3=Cool, 4=Fini).
2. **Resource cost** — with only 5 states, one-hot saves no meaningful comparator logic and consumes the same flip-flop count after register packing.

---

## 6. Interface Specification

### 6.1 Clock and Reset

| Signal | Direction | Width | Description |
|:-------|:----------|:------|:------------|
| `clk`   | in | 1 | 31.25 MHz system clock (platform-supplied). |
| `reset` | in | 1 | Synchronous, active-high system reset. Forces all internal state to defaults. |

### 6.2 Analog I/O

| Signal     | Direction | Width  | Use                                                    |
|:-----------|:----------|:-------|:-------------------------------------------------------|
| `inputa`   | in        | signed 16 | Trigger input. Compared against `threshold_v_r`.    |
| `inputb`   | in        | signed 16 | **Unused**; ignored.                                |
| `inputc`   | in        | signed 16 | **Unused**; ignored.                                |
| `inputd`   | in        | signed 16 | **Unused**; ignored.                                |
| `outputa`  | out       | signed 16 | Trigger voltage during S_Fire; 0 otherwise or when ARM=0. |
| `outputb`  | out       | signed 16 | Intensity voltage during S_Fire; 0 otherwise or when ARM=0. |
| `outputc`  | out       | signed 16 | **Tied to 0**.                                      |
| `outputd`  | out       | signed 16 | **Tied to 0** (not physically available on Moku:Go).|
| `exttrig`  | in        | 1         | **Unused**; reserved.                               |
| `sync`     | in        | 32        | **Unused**; reserved.                               |

### 6.3 Control Register Map

| Register   | Bits     | Name              | Type            | Description                                                                             |
|:-----------|:---------|:------------------|:----------------|:----------------------------------------------------------------------------------------|
| control[0] | [31]     | ARM               | bool            | Output enable. 0 forces `outputa`=`outputb`=0 combinationally.                          |
| control[0] | [30]     | RESET             | bool            | High-to-low edge latches control[1..4] and enters S_Reset.                              |
| control[0] | [29:0]   | _reserved_        | —               | Reserved; write 0.                                                                      |
| control[1] | [15:0]   | trigger_out_v     | signed 16       | DC voltage (LSBs) driven on `outputa` during S_Fire.                                    |
| control[1] | [31:16]  | _unused_          | —               | Ignored.                                                                                |
| control[2] | [15:0]   | intensity_out_v   | signed 16       | DC voltage (LSBs) driven on `outputb` during S_Fire.                                    |
| control[2] | [31:16]  | _unused_          | —               | Ignored.                                                                                |
| control[3] | [15:0]   | threshold_v       | signed 16       | Trigger threshold (LSBs). Strict greater-than comparison against `inputa`.              |
| control[3] | [31:16]  | _unused_          | —               | Ignored.                                                                                |
| control[4] | [15:0]   | duration          | unsigned 16     | S_Fire length in clock cycles. S_Cool length is `2 × duration`.                          |
| control[4] | [31:16]  | _unused_          | —               | Ignored.                                                                                |
| control[5..15] | [31:0] | _unused_        | —               | Reserved.                                                                               |

### 6.4 Status Register Map

| Register   | Bits     | Name              | Description                                                                              |
|:-----------|:---------|:------------------|:-----------------------------------------------------------------------------------------|
| status[0]  | [4:0]    | FSM_state         | 0x00=Reset, 0x01=Idle, 0x02=Fire, 0x03=Cool, 0x04=Fini.                                  |
| status[0]  | [31:5]   | _reserved_        | Read as 0.                                                                               |
| status[1..15] | [31:0] | _unused_        | Tied to 0.                                                                               |

---

## 7. Timing

### 7.1 Clock Domain

A single 31.25 MHz domain (`clk`). No clock-domain crossings; all I/O is synchronous to this clock. The Moku:Go wrapper is responsible for analog-front-end sampling and host-bus synchronization.

### 7.2 Reset Strategy

- **System `reset`** — synchronous, active-high, asserted by the Moku:Go wrapper at instrument load. Drives all registers to their default values.
- **Per-instrument RESET** — control[0] bit 30, edge-triggered (high-to-low). Treated as a one-cycle command pulse that latches parameters and re-enters S_Reset.

### 7.3 Sequence Timing Diagram

The diagram below shows a single full sequence with `duration = 4` (chosen for readability; real values typically 100s–1000s).

```
cycle:        N-1   N   N+1  N+2  N+3  N+4  N+5  N+6  N+7  N+8  N+9  N+10 N+11 N+12 N+13
control[30]:  ‾‾\__|____|____|____|____|____|____|____|____|____|____|____|____|____|____
                  (falling edge at cycle N)
reset_edge:   ____/‾‾\_______________________________________________________________
state_r:       ??  RST  IDLE IDLE FIRE FIRE FIRE FIRE COOL COOL COOL COOL COOL COOL COOL FINI
                                  (trigger at N+3; duration=4, cool=8)
cycle_count:   ?   0    0    0    1    2    3    4    1    2    3    4    5    6    7    8 → 0
inputa>thr:    -   -    no   yes  yes  yes  yes  yes  -    -    -    -    -    -    -    -
out_a_r:       ?   0    0    0    Tv   Tv   Tv   Tv   0    0    0    0    0    0    0    0
outputa(ARM=1):?   0    0    0    Tv   Tv   Tv   Tv   0    0    0    0    0    0    0    0
```

Where `Tv` = `trigger_out_v_r`. Key observations:
- Parameter latch happens at the cycle of `reset_edge_w` (cycle N).
- S_Reset is a single-cycle pass-through; S_Idle is entered at cycle N+1.
- A trigger sampled at cycle N+3 causes the FSM to enter S_Fire at cycle N+3 as well (same-cycle output update because the case-statement drives `out_a_r` from the new state in the same always_ff block).
- S_Fire spans cycle_count 1..4 (4 cycles = `duration`).
- S_Cool spans cycle_count 1..8 (8 cycles = `2 × duration`).
- S_Fini is entered after the last S_Cool cycle and persists until the next RESET edge.

### 7.4 Cycle Accounting

- The cycle in which the counter equals 1 is "cycle 1" of the active state.
- The exit comparison is `cycle_count_r >= duration_r` (resp. `2 × duration_r`); the state transition takes effect on the cycle in which this comparison first holds.
- Therefore S_Fire occupies exactly `duration` cycles and S_Cool occupies exactly `2 × duration` cycles, end-to-end.

### 7.5 ARM-to-Output Latency

The ARM gate is purely combinational:
```
outputa = arm_w ? out_a_r : 16'sd0;
```
Driving ARM low forces both outputs to 0 within the same clock cycle (limited only by combinational propagation delay through the output mux). The FSM continues to advance internally; on the next ARM=1 cycle the FSM-driven outputs become visible again. This zero-cycle blanking is a safety property required for driving an EMFI probe.

---

## 8. Design Decisions and Rationale

| ID    | Decision                                                | Rationale                                                                                                                                            | Alternatives considered                                                                       |
|:------|:--------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------|
| DR-1  | RESET is edge-triggered (high-to-low).                  | A level-triggered RESET would either continuously re-latch (preventing operation) or require a separate "valid" strobe. An edge gives unambiguous, one-shot semantics with no extra register. | Level-triggered RESET + separate strobe; rising-edge RESET (chosen falling so the line idles high during operation). |
| DR-2  | Parameters are latched at RESET, not read live.         | A sequence is single-shot and physically dangerous (driving a probe). Live reads would let host-side races change `duration` or `threshold` mid-pulse. Latching freezes the contract for the whole sequence. | Live read of `control[1..4]` each cycle; double-buffered parameter bank.                       |
| DR-3  | Cycle counter is 17 bits.                               | `duration` is 16-bit unsigned (max 65535); cooldown target is `duration << 1` (max 131070). `⌈log₂(131071)⌉ = 17`, so 17 bits is the minimum non-overflowing width. | 16-bit (overflows at max duration); 32-bit (wastes 15 bits).                                  |
| DR-4  | Threshold comparison is strict greater-than.            | Removes boundary ambiguity. Hosts typically set threshold just below the expected event amplitude; `>` makes the on-threshold case a non-trigger and gives a deterministic edge. | `>=`; absolute-value comparison; hysteretic comparator.                                       |
| DR-5  | ARM gates outputs combinationally, not via the FSM.     | An EMFI probe driver must blank outputs immediately on disarm — even a one-cycle delay (32 ns) can correspond to several volts of pulse energy. A combinational mux gives zero-cycle response. | Registered ARM gate (one-cycle latency); routing ARM into the FSM as an exit condition.        |
| DR-6  | `out_a_r`/`out_b_r` are registered; only the ARM mux is combinational on the output path. | Keeps the path-to-pads short and timing-clean. Only one combinational level (`AND`/mux) sits between a flip-flop and the output pin. | Fully combinational outputs (longer paths); fully registered ARM (loses zero-cycle blanking).  |
| DR-7  | Cooldown is fixed at `2 × duration`.                    | A second timing register would double the host-side configuration surface. A 2× cool-to-fire ratio matches the typical Chipshouter thermal recovery profile and provides a useful default without parameter explosion. | Separate `cooldown` register; configurable cool-to-fire ratio; runtime-computed thermal model. |
| DR-8  | S_Fini is terminal; no auto-return to S_Idle.           | Re-arming automatically would let residual analog excursions immediately re-fire, defeating the single-shot guarantee. Explicit RESET forces the host to acknowledge completion. | Auto-return after cooldown; configurable repeat count.                                         |
| DR-9  | `default:` clause routes unknown states to S_Reset.     | Defensive against SEU or synthesis anomalies that produce an unreachable state encoding. Recovery to S_Reset is a known-safe destination (outputs go to 0). | `default: state_r <= state_r` (lock-up); explicit error signal; one-hot encoding (different failure mode). |
| DR-10 | `duration` is 16-bit unsigned, not signed.              | Duration is inherently non-negative; treating it as unsigned doubles addressable range to 65535 cycles (~2.097 ms at 31.25 MHz). The output voltages are signed because negative DC is meaningful; cycle counts are not. | Signed 16-bit (loses half the range); 32-bit unsigned (no need at current scaling).            |

---

## 9. Verification Plan

### 9.1 Coverage Model

At minimum, the testbench shall exercise:

- Every state visited at least once (`state coverage`).
- Every transition arc in §5.3 taken at least once (`transition coverage`).
- Threshold cases: `inputa < threshold_v`, `inputa = threshold_v`, `inputa > threshold_v` in S_Idle.
- ARM cases: ARM=1 and ARM=0 in each of S_Idle, S_Fire, S_Cool, S_Fini.
- Boundary `duration` values: 0, 1, 65535.
- Negative output voltages (signed boundary).

### 9.2 Test Case → Requirement Map

(Test cases TC-1..TC-20 are those enumerated in `README.md` §Test Plan, items 1–20.)

| Test case (README #) | Description                              | Requirement(s) covered |
|:---------------------|:-----------------------------------------|:-----------------------|
| TC-1                 | ARM output blanking                      | FR-6                   |
| TC-2                 | RESET parameter latch                    | FR-1                   |
| TC-3                 | S_Reset → S_Idle transition (1 cycle)    | FR-1, NFR-2            |
| TC-4                 | Threshold trigger (above)                | FR-2                   |
| TC-5                 | Threshold boundary (equal)               | FR-2                   |
| TC-6                 | Threshold boundary (below)               | FR-2                   |
| TC-7                 | Fire duration accuracy                   | FR-3                   |
| TC-8                 | Fire output voltages                     | FR-3                   |
| TC-9                 | Cooldown duration accuracy               | FR-4                   |
| TC-10                | Cooldown output zero                     | FR-4                   |
| TC-11                | S_Fini indefinite hold                   | FR-5                   |
| TC-12                | RESET from S_Fini                        | FR-5, FR-9             |
| TC-13                | Zero duration edge case                  | FR-3, FR-4             |
| TC-14                | ARM toggle during Fire                   | FR-6                   |
| TC-15                | RESET during Fire                        | FR-9                   |
| TC-16                | Negative voltage outputs                 | FR-10                  |
| TC-17                | Maximum duration                         | FR-3, FR-4, DR-3       |
| TC-18                | Rapid re-arm sequence                    | FR-8, FR-9             |
| TC-19                | Status register encoding                 | FR-7                   |
| TC-20                | Multi-cycle trigger persistence          | FR-8                   |

### 9.3 Recommended Testbench Structure

- A directed test per FR-N, executed with Verilator (`verilator --binary` or `verilator --cc` against a C++ harness).
- A small randomized sweep over `(duration, threshold)` pairs verifying that:
  - Fire length = `duration`,
  - Cool length = `2 × duration`,
  - No spurious transitions out of S_Fini except on RESET edge.
- Linting: `verilator --lint-only design.v` shall produce zero warnings (the existing `lint_off UNUSEDSIGNAL` pragma is the only suppression).

### 9.4 Acceptance Criteria

- All 20 README test cases pass.
- `verilator --lint-only` clean.
- Manual review confirms `status[0][4:0]` matches FSM state for every cycle of a representative run.

---

## 10. Known Limitations and Future Work

- **No `exttrig` support.** The platform's external trigger input is wired but ignored. Future revisions could OR `exttrig` into the trigger condition or expose it via a control bit.
- **No fine-grained progress reporting.** `status[0]` reports only the FSM state, not the current `cycle_count_r`. A polling host cannot tell how far into Fire or Cool the instrument is.
- **Fixed 2:1 cool:fire ratio.** Cannot model probes whose thermal recovery is shorter (e.g. 1:1) or longer (e.g. 10:1) than 2× without rebuilding the bitstream.
- **Single trigger channel.** Only `inputa` is monitored; `inputb`/`inputc`/`inputd` are wasted on this platform.
- **No event log or timestamp.** Useful for fault-injection campaigns where the trigger time relative to a clock source is significant.
- **Single-shot only.** No mode for repeated burst output without host intervention.

---

## 11. Traceability Matrix

Implementation line numbers refer to `design.v` at the revision matching this spec (commit `32712b1`).

| Requirement | Implementation (design.v)                                                   | Tests           |
|:------------|:----------------------------------------------------------------------------|:----------------|
| FR-1        | `reset_edge_w` detection (lines 102–111); parameter latch (lines 176–185).  | TC-2, TC-3      |
| FR-2        | `trigger_w` (line 125); S_Idle transition (lines 199–210).                  | TC-4, TC-5, TC-6 |
| FR-3        | S_Fire body (lines 212–226), exit comparison line 217.                      | TC-7, TC-17     |
| FR-4        | `cooldown_target_w` (line 118); S_Cool body (lines 228–240).                | TC-9, TC-17     |
| FR-5        | S_Fini body (lines 242–247).                                                | TC-11, TC-12    |
| FR-6        | ARM gate (lines 132–133).                                                   | TC-1, TC-14     |
| FR-7        | `status[0]` assignment (line 141).                                          | TC-19           |
| FR-8        | S_Fire/S_Cool/S_Fini bodies never sample `trigger_w` (lines 212–247).       | TC-18, TC-20    |
| FR-9        | `reset_edge_w` priority in always_ff (lines 176–185 before case).           | TC-12, TC-15    |
| FR-10       | Signed declarations on `out_a_r`/`out_b_r` and `outputa`/`outputb` (lines 37–38, 88–89, 132–133); `$signed(...)` casts on latch (lines 180–182). | TC-16 |
| NFR-1       | All state in `always_ff @(posedge clk)` (lines 164, 102).                   | Inspection      |
| NFR-2       | Trigger evaluated combinationally in S_Idle, state update next cycle.       | TC-3            |
| NFR-3       | Register declarations (lines 66–89).                                        | Inspection      |
| NFR-4       | No `always_comb` with feedback; only the ARM mux is combinational.          | Inspection      |
| NFR-5       | `if (reset)` branch in always_ff (lines 165–174, 103–104).                  | Inspection      |
| DR-1        | Edge detector (line 111).                                                   | TC-2            |
| DR-2        | Parameter latch only in `reset_edge_w` branch (lines 176–185).              | TC-2            |
| DR-3        | `cycle_count_r` width `[16:0]` (line 79); `cooldown_target_w` width `[16:0]` (line 82). | TC-17 |
| DR-4        | `>` comparator (line 125).                                                  | TC-5            |
| DR-5        | Combinational ARM gate (lines 132–133).                                     | TC-14           |
| DR-6        | Registered `out_a_r`/`out_b_r` (lines 88–89, 207–222).                      | Inspection      |
| DR-7        | Hardwired `duration << 1` (line 118).                                       | TC-9            |
| DR-8        | S_Fini self-loop with no trigger sampling (lines 242–247).                  | TC-11           |
| DR-9        | `default:` clause (lines 249–255).                                          | Formal/inspection |
| DR-10       | `logic [15:0] duration_r` — unsigned (line 73).                             | TC-17           |
