---
publish: "true"
type: reference
created: 2025-11-25
modified: 2026-05-18
tags:
  - moku
  - api
  - instruments
  - reference
accessed: 2026-05-18
---
# Moku Instruments

This directory contains documentation for all Moku instrument classes. Each instrument provides specialized measurement, generation, or signal processing capabilities.

## Reviewed Instruments

### [CustomInstrument](custominstrument.md)
**Module:** `moku.instruments.CustomInstrument`

Custom user-defined instruments created through Moku's cloud compilation service ("Moku Compile"). **Replaces `CloudCompile`.**

**Key Features:**
- Custom bitstream deployment (tar/tar.gz packages)
- Control register interface (`set_control`, `get_control`)
- Status register readback (`get_status`) — read live hardware state
- `CustomInstrumentPlus` variant for larger designs
- Multi-instrument mode support
- Settings save/load

> [!warning] Migration Note
> `CloudCompile` is deprecated. The class still ships in `moku.instruments` as a backwards-compat shim that prints a warning and forwards to `CustomInstrument`. Replace `CloudCompile` with `CustomInstrument` in any new code. See [custominstrument.md](custominstrument.md) for the migration guide.

### [MultiInstrument (MIM)](mim.md)
**Module:** `moku.instruments.MultiInstrument` ([source](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/mim.md))

Multi-Instrument Mode controller for running multiple instruments simultaneously on a single Moku platform.

**Key Features:**
- Slot-based instrument management
- Signal routing between instruments
- Frontend/output configuration per slot
- Digital I/O management
- Platform-level configuration

## Instrument Categories

### Signal Generators
- [waveformgenerator.md](waveformgenerator.md) - Basic waveform generation (Sine, Square, Ramp, Pulse, Noise, DC)
- [awg.md](awg.md) - Arbitrary Waveform Generator with custom waveforms

### Analyzers & Measurement
- [oscilloscope.md](oscilloscope.md) - Oscilloscope with triggering and data acquisition
- [spectrumanalyzer.md](spectrumanalyzer.md) - Frequency-domain analysis (0Hz-30MHz)
- [phasemeter.md](phasemeter.md) - Phase and amplitude measurement (2-200MHz)
- [logicanalyzer.md](logicanalyzer.md) - Digital signal analysis with protocol decoders
- [tfa.md](tfa.md) - Time-Frequency Analyzer with sub-nanosecond precision
- [fra.md](fra.md) - Frequency Response Analyzer

### Signal Processing
- [digitalfilterbox.md](digitalfilterbox.md) - IIR digital filtering
- [firfilter.md](firfilter.md) - FIR digital filtering
- [lockinamp.md](lockinamp.md) - Lock-In Amplifier with dual-phase demodulation

### Control & Feedback
- [pidcontroller.md](pidcontroller.md) - PID Controller with comprehensive control loops
- [laserlockbox.md](laserlockbox.md) - Laser frequency stabilization

### Data Acquisition
- [datalogger.md](datalogger.md) - Voltage logging and waveform generation

### Data Streaming
- [GigabitStreamer](gigabitstreamer.md) (ID=12) - UDP streaming via SFP ports at gigabit speeds
- [GigabitStreamerPlus](gigabitstreamer.md#gigabitstreamerplus) (ID=13) - UDP streaming via QSFP port at high gigabit speeds

### Infrastructure
- [stream.md](stream.md) - Streaming infrastructure base class
- [nn.md](nn.md) - Neural Network inference engine
- [init.md](init.md) - Instrument package initialization and exports

## Version 4.1.1.1 Changes Summary

> Captured when these classes first landed; still accurate in 4.2.2.1.

| Change | Description |
|--------|-------------|
| `CustomInstrument` | New class replacing `CloudCompile` |
| `CustomInstrumentPlus` | New variant for larger designs (ID=254) |
| `get_status()` | **NEW API** - Read status registers from FPGA |
| `GigabitStreamer` | New instrument for UDP streaming (SFP) |
| `GigabitStreamerPlus` | New instrument for high-speed UDP streaming (QSFP) |
| `force_deploy` | New parameter in `claim_ownership()` |
| `bandwidth` | New parameter in `MultiInstrument.set_frontend()` |
| Build system | Migrated from Poetry to Hatch (PEP 621) |
| Python | Minimum version now 3.8 (was 3.5) |

## See Also

- [Moku API Documentation](../README.md) - Main API documentation index
- [Official Moku Instruments Documentation](https://apis.liquidinstruments.com/instruments.html)
- [Moku Python Package](https://pypi.org/project/moku/)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/README)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/README.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/README.md)
