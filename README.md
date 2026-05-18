---
created: 2026-05-15
modified: 2026-05-18 10:49:49
accessed: 2026-05-18 10:44:57
---
# ProbeDriver2 
## Overview
Your goal is to create a verilog module ("PD2" aka '`ProbeDriver2`)  that implements the [CustomInstrument](https://apis.liquidinstruments.com/mc/wrapper.html#custominstrument-architecture) interface defined by Liquid Instruments.  The PD2 ProbeDriver is a simple module designed to drive common fault injection Probes. The first pass of PD2 is limited to the following features:
- Detect when an input voltage exceeds a certain threshold, and then
- output two DC voltages of user specified values for a user specified time. 
This is the 'minimal viable product', that we will build off of in the future. 


Initially we will be driving he Riscure [DS1120](https://www.keysight.com/us/en/assets/9924-01969/user-manuals/DS1120A-Unidirectional-Fault-Injection-Probe-User-Manual.pdf) unidirectional EMFI probe.

 This project is split into two halves. the 'Backend' (which consists of a Moku Go running our custom bitstream), and a simple python FrontEnd that utilizes the `moku` pip package. 

## Pre-requisites / 

### [Moku Compiler](https://liquidinstruments.com/moku-compile/) 
Cloud hosted instance of Xilinx vivado. Given a well defined `CustomInstrument` it will deliver a compatible bitstream file.
See also

### [CustomInstsrument](https://apis.liquidinstruments.com/api/reference/custominstrument/)
``` verilog
module CustomInstrument (
    input wire clk,
    input wire reset,
    input wire [31:0] sync,

    input wire signed [15:0] inputa,
    input wire signed [15:0] inputb,
    input wire signed [15:0] inputc,
    input wire signed [15:0] inputd,

    input wire exttrig,

    output wire signed [15:0] outputa,
    output wire signed [15:0] outputb,
    output wire signed [15:0] outputc,
    output wire signed [15:0] outputd,

    input wire [31:0] control [0:15],
    output wire [31:0] status[0:15]
);
```
### [StatusRegisters](https://apis.liquidinstruments.com/mc/statusregs.html)
**`StatusRegisters`** are 32-bit wide registers available to the bitstream. **StatusRegisters** can be __read across the network__ 

### [ControlRegisters](https://apis.liquidinstruments.com/mc/controls.html)
`ControlRegisters` in this context can be thought of as 'Application level' control registers. `ControlRegisters` are **writeable** from the network. 



## Reference examples

### [DCSequencer](https://github.com/liquidinstruments/moku-examples/tree/main/mc/Advanced/DCSequencer)
The `DCSequencer` is a a reference example illustrating a simple DC sequencer.

### [EventCounter](https://github.com/liquidinstruments/moku-examples/tree/main/mc/Advanced/EventCounter)
Counts the number of pulses of defined width in a period. If a count threshold is exceeded, an output flag is raised.






# I/O
![](PD2/imgs/PD2-001-MIM.png)
## [MIM](https://liquidinstruments.com/multi-instrument-mode/) (Slots)

The PD2 module is expected to be loaded into **Slot2** in [multi instrument mode](https://liquidinstruments.com/multi-instrument-mode/). 
**Slot1** is resevered for a Oscilloscope instrument which can be used to observe the module and/or physical inputs.





## Input routing table

| PHy   | SLOT  | INPUT    | Descr            |
| ----- | ----- | -------- | ---------------- |
| `IN1` | SLOT2 | `InputA` | `**Trigger-In**` |
## Output routing table

| PHy    | SLOT  | INPUT     | Descr             |
| ------ | ----- | --------- | ----------------- |
| `OUT1` | SLOT2 | `OutputA` | `**Trigger-Out**` |
| `OUT2` | SLOT2 | `OutputB` | `**Intensity-Out**` |

# Requirements


## Backend (bitstream) requirements
- The PD2 backend has a simple control interface (`arm`, `reset`) implemented in the `Control0` register (detailed in the RTL section below)
- The PD2 module shall be implemented as simple state machine (details provided below).  
- The PD2 module shall use `Status0` to indicate its status across the network. 
- The PD2 module shall take the following input parameters: (`trig_in_v_threshold`,  `trig_out_v`, `intens_out_v`, `duration`)
- The internal state machine (described below) shall be visible in the bottom N bits of `Status0` so that it can be polled across the network.
#### Backend (bitstream) questions:
- Propose and document a simple register packing scheme to let the user transmit `trig_in_v_threshold`, `trig_out_v`, `intens_out_v`, `duration` into Control Registers 1-N. (The client will also need to be aware of this scheme)


### Reset behavior

#### Platform Reset
The Moku platform is responsible for providing a 'platform reset'. (This can be controlled via the Moku API and is automatically asserted on load). 
**We want to put minimal functionality inside this reset**. 


#### Application reset
Bit 30 of `control0` is designed as `Application Reset` for our purposes. On reset the `trig_v_threshold`, `trig_v_out` and `duration` values should be latched into local variables, and the module should enter the `S1-Idle` state.


## Design considerations / questions
- Should `Application reset` be triggered when Control0[30] is high, or when it transitions from high to low ?
- Any feedback / suggestions on the proposed RTL/backend API ? Bit packing should be designed to be intuitive for humans (we have plenty).


### Functional requirements

#### F1: Outputs  'blanked' when module is not armed.
I.e., the module should **never** have OutputA, OutputB, etc  non-zero under any circumstance __unless__ the `Armed` bit is set in Control0

#### F2: Trigger in 
When  `inputa` (trigger_in) exceeds the user supplied `trig_in_v_thresh` the module should immediately enter the 'firing' state.

#### F3: Firing
The module should remain in the `firing` state for exactly `duration` clk cycles. During this state outputa (`trig_out_v`) and outputb (`intensity_out_v`) should be set to the values provided by the user in th `trig_out_v` and `duration` input parameters that were supplied during reset.
#### F4: Cooldown
After `firing` the module should enter the `Cooldown` state for **`duration` times two** clk cycles. During `Cooldown` all output signals shall be zero.

#### F5: Fini
After `Cooldown` the module shall enter the `Fini` (finished) state. 
The only way to transiton out of `Fini` is via a `Reset`


### State definitions

| N      | Name      |
| ------ | --------- |
| `0x00` | `S_Reset` |
| `0x01` | `S_Idle`  |
| `0x02` | `S_Fire`  |
| `0x03` | `S_Cool`  |
| `0x04` | `S_Fini`  |

#### `S0_Reset` (`0x00`)
On reset the module shall: 
- latch all user provided input parameters into appropriate local variables. 
- enter the `S1_Idle` state

#### `S1_Idle` (`0x01`)
While in idle the module 
- shall wait an arbitrary amount of time in the `S1_IDLE` state, until  `trig_in`  exceeds the user supplied `trig_in_thresh`. It will then transition to `S2_Fire`


#### `S2_Fire` (`0x02`)
While in the `S2_Fire` state 
- `trigger_out` and `intensity_out` shall be set to the user specified values for `duration` clk ticks. 
- After this we move into `S3_Cool`

#### `S3_Cool` (`0x03`)
While in the `S3_Fire` state
- `trigger_out` and `intensity_out` will be set to `0v0` for `duration * 2` clk cycles.
- The module then moves into `S4_Fini`


#### `S4_Fini` (`0x04`)
While in the `S4_Fini` state:
-  `trigger_out` and `intensity_out` will be set to `0v0` 
- The only way to leave this state is via the `Reset` signal. 


## Assumptions
- Assume a target platform of `Moku-Go` for now (other models will be added later)





# RTL (Register 'API')

![](PD2/imgs/PD2-001-CR-ex.png)

## `Control0`
**`Control0`** is the 'top' level control register. It currently has two defined bits.

| BIT   |     | DESCR   | DESCR                 |
| ----- | --- | ------- | --------------------- |
| 31    | `A` | `ARM`   |                       |
| 30    | `R` | `RESET` | Resets module to high |
| 29..0 |     | RES     | Reserved              |
|       |     |         |                       |
 
##  trigger_out_v : `Control1[15:0]` 
##  duration : `Control2[15:0]`
##  threshold_v : `Control3[15:0]` 



### `ARM` 

The topmost bit in Control0. **When ARM is LOW the driver shall NEVER output a non-zero voltage** 


### `Reset` 



## Client (frontend)

```python
import moku 

```

The Client is responsible for:

### Client initialization

0. conecting to the moku
1. configuring the moku for MIM
2. loading the bitstream into **slot2**
3. configuring the `routing` between connections as shown above

### Client main loop

0. Ask user to validate parameters (`trig_in_threshold_v`, `duration`, etc)
1. Convert users input to the appropriate [Control Register](https://apis.liquidinstruments.com/mc/controls.html)
2. push control registers to device,
3. arm (#TODO)
4. poll [status registers](https://apis.liquidinstruments.com/mc/statusregs.html) - update UI
5. Repeat?

> [!NOTE]
> Be sure you encourage your AI to **document** the `RTL` interface between your Instrument and the Control Registers. 
> 

# Server (backend)

``` verilog



```

## Units (time, volts, ...)

## Time units

The **client** is responsible for converting all (human friendly) units of time into the target platforms **native clk** count. I.e., if the human inputs a duration of '20 microseconds' the client should convert this into a 'tick count' for the server to process. 

## Voltage units

For now, assumed a fixed voltage range (-5v0, +5v0) using the standard 16-bit ADC/DAC representation used on the moku go.

## Proposed RTL

