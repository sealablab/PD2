---
publish: "true"
type: reference
date: 2025-12-10
path_to_py_file: moku/instruments/_custominstrument.py
title: CustomInstrument
tags:
  - moku
  - api
  - instrument
  - fpga
  - custom
  - mcc
version: 4.1.1.1
created: 2025-12-10
modified: 2025-12-10 05:01:50
accessed: 2025-12-10 04:54:48
---

# Overview

This module implements the `CustomInstrument` and `CustomInstrumentPlus` classes (new in v4.1.1.1), which provide support for custom user-defined instruments created through Moku's cloud compilation service (MCC). These instruments load custom bitstream packages (tar/tar.gz files) and provide a generic interface for controlling custom hardware implementations.

| Class | INSTRUMENT_ID | OPERATION_GROUP | Use Case |
|-------|---------------|-----------------|----------|
| `CustomInstrument` | 255 | `"custominstrument"` | Standard custom instruments |
| `CustomInstrumentPlus` | 254 | `"custominstrumentplus"` | Larger custom designs |
| `CloudCompile` | 255 | `"custominstrument"` | **DEPRECATED** - alias for CustomInstrument |

> [!info] Key Dependencies
> - `tarfile` - For extracting bitstream packages
> - `tempfile` - For temporary extraction of bitstream files
> - `pathlib.Path` - For file path handling
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode
> - `moku.exceptions` - Custom exception types

> [!warning] Migration from CloudCompile
> `CloudCompile` is deprecated in v4.1.1.1. Replace:
> ```python
> # OLD (deprecated)
> from moku.instruments import CloudCompile
> mcc = CloudCompile('192.168.1.100', bitstream='my_design.tar.gz')
>
> # NEW (recommended)
> from moku.instruments import CustomInstrument
> mcc = CustomInstrument('192.168.1.100', bitstream='my_design.tar.gz')
> ```

# Classes

## CustomInstrument

A custom instrument interface that loads and controls user-defined FPGA bitstreams created through Moku's cloud compilation service.

```python
class CustomInstrument(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 255
    OPERATION_GROUP = "custominstrument"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False, bitstream=None,
                 connect_timeout=15, read_timeout=30, slot=None,
                 multi_instrument=None, **kwargs):
        ...
```

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, bitstream, connect_timeout, read_timeout, slot, multi_instrument, **kwargs)` - Initializes the instrument with a bitstream package
- `for_slot(slot, multi_instrument, **kwargs)` - Class method for multi-instrument mode configuration
- `save_settings(filename)` - Saves current instrument settings to a .mokuconf file
- `load_settings(filename)` - Loads settings from a .mokuconf file
- `set_control(idx, value, strict)` - Sets a single control register value
- `set_controls(controls, strict)` - Sets multiple control registers at once
- `get_control(idx, strict)` - Reads a single control register value (cached)
- `get_controls()` - Reads all control registers (cached)
- `get_status()` - **NEW in 4.1.1.1** - Reads all status registers from FPGA (live)
- `set_interpolation(channel, enable, strict)` - Enables/disables interpolation on a channel
- `get_interpolation(channel)` - Gets interpolation state for a channel
- `sync(mask, strict)` - Synchronization operation with mask parameter
- `summary()` - Returns instrument summary information

> [!note] Implementation Notes
> - The `bitstream` parameter is **required** and must be a path to a valid tar or tar.gz file
> - The bitstream package is extracted to a temporary directory during initialization
> - Inherits from both `MultiInstrumentSlottable` and `Moku` to support standalone and multi-instrument modes
> - The control interface provides generic register access (idx-based) since custom instruments can have arbitrary control schemes

> [!warning] Important
> - The bitstream file must exist at the specified path or initialization will fail with `FileNotFoundError`
> - If the bitstream package is invalid, a `MokuException` is raised with guidance to check the package
> - The `strict` parameter (default True) disables implicit type conversions when set
> - Settings files must have `.mokuconf` extension for compatibility with Moku tools

## CustomInstrumentPlus

Extended variant of CustomInstrument for larger custom designs requiring more FPGA resources.

```python
class CustomInstrumentPlus(CustomInstrument):
    INSTRUMENT_ID = 254
    OPERATION_GROUP = "custominstrumentplus"
```

Inherits all methods from `CustomInstrument`. Use this class when your MCC design requires the "Plus" bitstream variant.

## CloudCompile (DEPRECATED)

```python
class CloudCompile(CustomInstrument):
    # Deprecated in 4.1.1 - prints warning on instantiation
```

Legacy alias for backwards compatibility. **Use `CustomInstrument` instead.**

# Control vs Status Registers

## Control Registers (Write)

Control registers are written by the host to configure FPGA behavior:

```python
# Write single register
mcc.set_control(0, 12345)

# Write multiple registers
mcc.set_controls([
    {'id': 0, 'value': 100},
    {'id': 1, 'value': 200},
])

# Read back (returns cached value, not live FPGA state)
val = mcc.get_control(0)
all_controls = mcc.get_controls()  # {'control0': val, 'control1': val, ...}
```

## Status Registers (Read) - NEW in 4.1.1.1

Status registers are written by the FPGA to report hardware state back to the host:

```python
# Read all status registers (live FPGA values)
status = mcc.get_status()  # {'status0': val, 'status1': val, ...}
```

> [!info] get_status() vs get_control()
> - `get_control()` returns **cached** control register values (what you last wrote)
> - `get_status()` returns **live** FPGA status register values (what hardware is reporting)
>
> Use `get_status()` for:
> - Reading measurement results computed by FPGA
> - Monitoring hardware state (triggers, counters, flags)
> - Debugging FPGA behavior in real-time

# Platform-Specific Constants

Control register values often require platform-specific conversion. **Important:** There are TWO different clocks:

| Platform | ADC/DAC Clock | MCC Fabric Clock | ADC Bits | Notes |
|----------|---------------|------------------|----------|-------|
| Moku:Go | 125 MHz | **31.25 MHz** (÷4) | 12-bit | Entry-level |
| Moku:Lab | 500 MHz | **125 MHz** (÷4) | 12-bit | |
| Moku:Pro | 1250 MHz | **312.5 MHz** (÷4) | 10-bit* | High-performance |
| Moku:Delta | 5000 MHz | **1250 MHz** (÷4) | 14-bit* | Flagship |

\* Blended ADC architecture (secondary high-resolution ADC available)

> [!warning] MCC Fabric Clock vs ADC Clock
> **CustomInstrument uses the MCC Fabric Clock**, not the ADC/DAC sample rate. Timing registers (durations, delays) must be calculated using the fabric clock period.

| Platform | MCC Period | ADC Resolution (approx) |
|----------|------------|------------------------|
| Moku:Go | 32 ns | 1/6550.4 V/bit |
| Moku:Lab | 8 ns | 2/30000 V/bit |
| Moku:Pro | 3.2 ns | 1/29925 V/bit |
| Moku:Delta | 0.8 ns | 1/36440 V/bit |

**Runtime Platform Discovery:**
```python
description = moku.describe()
hardware = description['hardware']  # e.g., 'Moku:Go', 'Moku:Pro'

# Clock period lookup (seconds)
period_dict = {
    'Moku:Go': 32e-9,
    'Moku:Lab': 8e-9,
    'Moku:Pro': 3.2e-9,
    'Moku:Delta': 0.8e-9
}

# ADC resolution lookup (volts per bit)
resolution_dict = {
    'Moku:Go': 1/6550.4,
    'Moku:Lab': 2/30000,
    'Moku:Pro': 1/29925,
    'Moku:Delta': 1/36440
}
```

# Usage Examples

## Basic Standalone Usage

```python
from moku.instruments import CustomInstrument

# Connect and deploy custom bitstream
mcc = CustomInstrument(
    '192.168.1.100',
    bitstream='my_design.tar.gz',
    force_connect=True
)

try:
    # Configure control registers
    mcc.set_control(0, 1000)  # Set CR0
    mcc.set_control(1, 500)   # Set CR1

    # Read status registers (live from FPGA)
    status = mcc.get_status()
    print(f"Status: {status}")

finally:
    mcc.relinquish_ownership()
```

## Multi-Instrument Mode

```python
from moku.instruments import MultiInstrument, CustomInstrument, Oscilloscope

m = MultiInstrument('192.168.1.100', platform_id=4, force_connect=True)

try:
    # Deploy custom instrument to slot 1
    mcc = m.set_instrument(1, CustomInstrument, bitstream='my_design.tar.gz')

    # Deploy oscilloscope to slot 2 for monitoring
    osc = m.set_instrument(2, Oscilloscope)

    # Route signals
    m.set_connections([
        {'source': 'Input1', 'destination': 'Slot1InA'},
        {'source': 'Slot1OutA', 'destination': 'Slot2InA'},
        {'source': 'Slot1OutA', 'destination': 'Output1'},
    ])

    # Configure and run
    mcc.set_control(0, 12345)

finally:
    m.relinquish_ownership()
```

## Using Context Manager

```python
from moku.instruments import CustomInstrument

with CustomInstrument('192.168.1.100', bitstream='my_design.tar.gz') as mcc:
    mcc.set_control(0, 100)
    status = mcc.get_status()
    print(status)
# Automatically relinquishes ownership on exit
```

# See Also

- [MultiInstrument](mim.md) - Multi-instrument mode management
- [Moku Cloud Compile Documentation](https://apis.liquidinstruments.com/cloudcompile.html)
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/custominstrument)
- [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/custominstrument.md)
