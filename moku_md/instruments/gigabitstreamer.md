---
publish: "true"
type: reference
date: 2025-12-09
path_to_py_file: moku/instruments/_gs.py
title: GigabitStreamer
tags:
  - moku
  - api
  - instrument
  - streaming
  - udp
  - sfp
  - qsfp
  - network
version: 4.1.1.1
created: 2025-12-09
modified: 2025-12-10 05:03:15
accessed: 2025-12-10 05:03:15
---

# Overview

This module implements the `GigabitStreamer` and `GigabitStreamerPlus` instrument classes (new in v4.1.1.1). These instruments enable high-speed data streaming by transmitting and/or receiving UDP packets through the Moku's optical network interfaces.

| Class | Port Type | INSTRUMENT_ID | OPERATION_GROUP | Documentation |
|-------|-----------|---------------|-----------------|---------------|
| `GigabitStreamer` | SFP | 12 | `"gs"` | [gs reference](https://apis.liquidinstruments.com/reference/gs) |
| `GigabitStreamerPlus` | QSFP | 13 | `"gsp"` | [gsp reference](https://apis.liquidinstruments.com/reference/gsp) |

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode

> [!warning] Hardware Requirements
> - **GigabitStreamer**: Requires Moku device with SFP port(s)
> - **GigabitStreamerPlus**: Requires Moku device with QSFP port (typically Moku:Pro or Moku:Delta)

# Classes

## GigabitStreamer

High-speed UDP data streaming instrument via SFP ports.

```python
class GigabitStreamer(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 12
    OPERATION_GROUP = "gs"
```

### Initialization

```python
def __init__(
    self,
    ip=None,
    serial=None,
    force_connect=False,
    ignore_busy=False,
    persist_state=False,
    connect_timeout=15,
    read_timeout=30,
    slot=None,
    multi_instrument=None,
    **kwargs,
):
```

## GigabitStreamerPlus

Extended streaming instrument via QSFP port for higher bandwidth applications.

```python
class GigabitStreamerPlus(GigabitStreamer):
    INSTRUMENT_ID = 13
    OPERATION_GROUP = "gsp"
```

Inherits all methods from `GigabitStreamer`.

# Method Reference

## Configuration Methods

### set_defaults()

Reset instrument to default configuration.

```python
gs.set_defaults()
```

### set_frontend()

Configure input channel frontend settings.

```python
def set_frontend(
    self,
    channel,           # int: Target channel
    impedance,         # str: '1MOhm' | '50Ohm'
    coupling,          # str: 'AC' | 'DC'
    attenuation=None,  # str: '-20dB' | '0dB' | '14dB' | '20dB' | '32dB' | '40dB'
    gain=None,         # str: '20dB' | '0dB' | '-14dB' | '-20dB' | '-32dB' | '-40dB'
    bandwidth=None,    # str: '1MHz' | '30MHz' | '200MHz' | '300MHz' | '600MHz' | '2GHz'
    strict=True,
):
```

### get_frontend()

Get current frontend configuration for a channel.

```python
config = gs.get_frontend(channel=1)
```

### enable_input()

Enable or disable an input channel.

```python
gs.enable_input(channel=1, enable=True)
```

### set_acquisition()

Configure acquisition mode and sample rate.

```python
def set_acquisition(
    self,
    mode,         # str: 'Normal' | 'Precision'
    sample_rate,  # number: 5e3 to 5e9 samples/second
    strict=True,
):
```

**Example:**
```python
gs.set_acquisition(mode='Normal', sample_rate=1e9)  # 1 GSa/s
```

### set_interpolation()

Configure interpolation mode for data reconstruction.

```python
def set_interpolation(
    self,
    mode,       # str: 'None' | 'Linear'
    strict=True,
):
```

### set_output()

Configure output channel settings.

```python
def set_output(
    self,
    channel,    # int: Target channel
    enable,     # bool: Enable output signal
    gain,       # number: Gain in dB
    offset,     # number: Offset in V
    strict=True,
):
```

## Network Configuration Methods

### set_local_network()

Configure local network settings for the streaming interface.

```python
def set_local_network(
    self,
    ip_address,              # str: Local IP address
    port,                    # int: UDP port number
    multicast_ip_address=None,  # str: Optional multicast IP
    strict=True,
):
```

**Example:**
```python
gs.set_local_network(
    ip_address='10.0.0.100',
    port=5000,
    multicast_ip_address='239.0.0.1'  # Optional multicast
)
```

### set_remote_network()

Configure remote destination for outgoing data.

```python
def set_remote_network(
    self,
    ip_address,    # str: Remote IP address
    port,          # int: Remote UDP port number
    mac_address,   # str: Remote MAC address
    strict=True,
):
```

**Example:**
```python
gs.set_remote_network(
    ip_address='10.0.0.200',
    port=5001,
    mac_address='00:11:22:33:44:55'
)
```

### set_outgoing_packets()

Configure Maximum Transmission Unit (MTU) for outgoing packets.

```python
def set_outgoing_packets(
    self,
    mtu,        # str: '508bytes' | '576bytes' | '1500bytes' | '9000bytes' | '65535bytes'
    strict=True,
):
```

| MTU Value | Use Case |
|-----------|----------|
| `'508bytes'` | Minimum, maximum compatibility |
| `'576bytes'` | Internet minimum |
| `'1500bytes'` | Standard Ethernet (most common) |
| `'9000bytes'` | Jumbo frames (requires network support) |
| `'65535bytes'` | Maximum UDP payload |

## Streaming Control Methods

### start_sending()

Begin streaming data via UDP.

```python
def start_sending(
    self,
    duration,           # float: Duration in seconds
    delay=0,            # int: Delay before start (seconds)
    trigger_source=None,  # str: 'Input1' | 'Input2' | 'Input3' | 'Input4' |
                          #      'InputA' | 'InputB' | 'External'
    trigger_level=0,    # number: Trigger level (-5V to 5V)
    strict=True,
):
```

**Example:**
```python
# Stream for 1 second, triggered on Input1 crossing 0.5V
gs.start_sending(
    duration=1.0,
    trigger_source='Input1',
    trigger_level=0.5
)
```

### stop_sending()

Stop active streaming.

```python
gs.stop_sending()
```

### get_send_status()

Get current status of outgoing stream.

```python
status = gs.get_send_status()
# Returns dict with streaming state information
```

### get_receive_status()

Get current status of incoming stream.

```python
status = gs.get_receive_status()
# Returns dict with receive state information
```

## Settings Management

### save_settings()

Save current configuration to file.

```python
gs.save_settings('streamer_config.mokuconf')
```

### load_settings()

Load configuration from file.

```python
gs.load_settings('streamer_config.mokuconf')
```

### summary()

Get instrument summary information.

```python
info = gs.summary()
```

# Usage Examples

## Basic Streaming Setup

```python
from moku.instruments import GigabitStreamer, MultiInstrument

# Connect to Moku in multi-instrument mode
m = MultiInstrument('192.168.1.100', platform_id=4, force_connect=True)

try:
    # Deploy GigabitStreamer to slot 1
    gs = m.set_instrument(1, GigabitStreamer)

    # Configure frontend
    gs.set_frontend(
        channel=1,
        impedance='50Ohm',
        coupling='DC',
        attenuation='0dB'
    )

    # Configure acquisition
    gs.set_acquisition(mode='Normal', sample_rate=500e6)  # 500 MSa/s

    # Configure network
    gs.set_local_network(ip_address='10.0.0.100', port=5000)
    gs.set_remote_network(
        ip_address='10.0.0.200',
        port=5001,
        mac_address='00:11:22:33:44:55'
    )

    # Set MTU for jumbo frames (if network supports it)
    gs.set_outgoing_packets(mtu='9000bytes')

    # Enable input
    gs.enable_input(channel=1, enable=True)

    # Start streaming for 10 seconds
    gs.start_sending(duration=10.0)

    # Monitor status
    import time
    while True:
        status = gs.get_send_status()
        print(f"Status: {status}")
        if status.get('complete', False):
            break
        time.sleep(0.5)

finally:
    m.relinquish_ownership()
```

## Triggered Streaming

```python
from moku.instruments import GigabitStreamer, MultiInstrument, Oscilloscope

m = MultiInstrument('192.168.1.100', platform_id=4, force_connect=True)

try:
    gs = m.set_instrument(1, GigabitStreamer)
    osc = m.set_instrument(2, Oscilloscope)

    # Route signals
    connections = [
        dict(source="Input1", destination="Slot1InA"),
        dict(source="Input1", destination="Slot2InA"),  # Monitor on scope
    ]
    m.set_connections(connections=connections)

    # Configure streamer
    gs.set_frontend(1, '50Ohm', 'DC', attenuation='0dB')
    gs.set_acquisition(mode='Normal', sample_rate=1e9)
    gs.set_local_network(ip_address='10.0.0.100', port=5000)
    gs.set_remote_network(
        ip_address='10.0.0.200',
        port=5001,
        mac_address='00:11:22:33:44:55'
    )

    # Start triggered streaming - waits for signal to cross threshold
    gs.start_sending(
        duration=0.1,           # 100ms capture
        trigger_source='InputA',
        trigger_level=0.5       # Trigger at 0.5V
    )

finally:
    m.relinquish_ownership()
```

## GigabitStreamerPlus (QSFP)

```python
from moku.instruments import GigabitStreamerPlus, MultiInstrument

m = MultiInstrument('192.168.1.100', platform_id=4, force_connect=True)

try:
    # Use Plus variant for QSFP port
    gsp = m.set_instrument(1, GigabitStreamerPlus)

    # Configuration is identical to GigabitStreamer
    gsp.set_frontend(1, '50Ohm', 'DC')
    gsp.set_acquisition(mode='Normal', sample_rate=5e9)  # Up to 5 GSa/s
    # ... rest of configuration

finally:
    m.relinquish_ownership()
```

# Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Moku Device                              │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   ADC/DAC   │───▶│ GigabitStreamer  │───▶│   SFP/QSFP    │──┼──▶ UDP Packets
│  │   Inputs    │    │   (slot N)       │    │   Port        │  │
│  └─────────────┘    └──────────────────┘    └───────────────┘  │
│                              │                                   │
│                              ▼                                   │
│                     ┌──────────────────┐                        │
│                     │ Network Config:  │                        │
│                     │ - Local IP/Port  │                        │
│                     │ - Remote IP/Port │                        │
│                     │ - MAC Address    │                        │
│                     │ - MTU            │                        │
│                     └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Remote Receiver                             │
│  ┌───────────────┐    ┌──────────────────┐                      │
│  │   NIC/FPGA    │───▶│   UDP Socket     │───▶ Data Processing  │
│  │   (10GbE)     │    │   (port 5001)    │                      │
│  └───────────────┘    └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

# See Also

- [CustomInstrument](docs/N/moku_md/instruments/custominstrument.md) - Custom FPGA instruments
- [MultiInstrument](docs/N/moku_md/instruments/mim.md) - Multi-instrument mode management
- [Datalogger](docs/N/moku_md/instruments/datalogger.md) - File-based data logging (alternative to streaming)
- [Official GigabitStreamer Documentation](https://apis.liquidinstruments.com/reference/gs)
- [Official GigabitStreamerPlus Documentation](https://apis.liquidinstruments.com/reference/gsp)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/gigabitstreamer)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/gigabitstreamer.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/gigabitstreamer.md)
