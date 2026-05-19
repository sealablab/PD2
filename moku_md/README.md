---
publish: "true"
type: reference
created: 2025-11-17
modified: 2026-05-18
tags:
  - moku
  - api
  - reference
  - documentation
accessed: 2026-05-18
---
# Moku Python API Documentation

This directory contains comprehensive markdown documentation for the Moku Python API package (v4.2.2.1). The documentation mirrors the structure of the installed pip package and provides high-level overviews of all modules, classes, and functions.

## Package Structure

### Core Modules

- [init.md](init.md) - Main package initialization, `Moku` base class, and `MultiInstrumentSlottable` mixin
- [session.md](session.md) - HTTP session management and API communication (`RequestSession`)
- [finder.md](finder.md) - Device discovery via Zeroconf/mDNS (`Finder`)
- [exceptions.md](exceptions.md) - Exception hierarchy (15 exception classes)
- [utilities.md](utilities.md) - Utility functions (device discovery, version checking, config paths)
- [logging.md](logging.md) - Logging infrastructure (`LoggingContext`, logger configuration)
- [version.md](version.md) - Version constants and compatibility information
- [cli.md](cli.md) - Deprecated CLI entry point

### Instruments

- [instruments/init.md](instruments/init.md) - Instrument package exports (all 18 instruments)

#### Signal Generators
- [instruments/waveformgenerator.md](instruments/waveformgenerator.md) - Basic waveform generation (Sine, Square, Ramp, Pulse, Noise, DC)
- [instruments/awg.md](instruments/awg.md) - Arbitrary Waveform Generator with custom waveforms

#### Analyzers & Measurement
- [instruments/oscilloscope.md](instruments/oscilloscope.md) - Oscilloscope with triggering and data acquisition
- [instruments/spectrumanalyzer.md](instruments/spectrumanalyzer.md) - Frequency-domain analysis (0Hz-30MHz)
- [instruments/phasemeter.md](instruments/phasemeter.md) - Phase and amplitude measurement (2-200MHz)
- [instruments/logicanalyzer.md](instruments/logicanalyzer.md) - Digital signal analysis with protocol decoders
- [instruments/tfa.md](instruments/tfa.md) - Time-Frequency Analyzer with sub-nanosecond precision
- [instruments/fra.md](instruments/fra.md) - Frequency Response Analyzer

#### Signal Processing
- [instruments/digitalfilterbox.md](instruments/digitalfilterbox.md) - IIR digital filtering
- [instruments/firfilter.md](instruments/firfilter.md) - FIR digital filtering
- [instruments/lockinamp.md](instruments/lockinamp.md) - Lock-In Amplifier with dual-phase demodulation

#### Control & Feedback
- [instruments/pidcontroller.md](instruments/pidcontroller.md) - PID Controller with comprehensive control loops
- [instruments/laserlockbox.md](instruments/laserlockbox.md) - Laser frequency stabilization

#### Data Acquisition
- [instruments/datalogger.md](instruments/datalogger.md) - Voltage logging and waveform generation

#### Data Streaming
- [instruments/gigabitstreamer.md](instruments/gigabitstreamer.md) - `GigabitStreamer` (SFP) and `GigabitStreamerPlus` (QSFP) UDP streaming

#### Advanced Features
- [instruments/mim.md](instruments/mim.md) - Multi-Instrument Mode for slot-based management
- [instruments/custominstrument.md](instruments/custominstrument.md) - `CustomInstrument` / `CustomInstrumentPlus` — custom FPGA bitstream deployment (replaces deprecated `CloudCompile`)
- [instruments/nn.md](instruments/nn.md) - Neural Network inference engine
- [instruments/stream.md](instruments/stream.md) - Streaming infrastructure base class

### Neural Network Utilities

- [nn/__init__.md](nn/__init__.md) - Neural network package initialization
- [nn/_linn.md](_linn.md) - Keras to .linn model conversion utilities

## DPD Project Hot-Path

> [!tip] Working on DPD?
> See **[DPD-API-HOTPATH.md](docs/DPD-API-HOTPATH.md)** for a focused index of the specific Moku API methods used by the DPD project, including:
> - MultiInstrument slot configuration & routing
> - CustomInstrument register access patterns (`set_control`, `get_control`, `get_status`)
> - Oscilloscope HVS state observation
> - Common initialization sequences

## Quick Reference

### Most Common Classes

- **Device Management**: [Moku](init.md) - Base class for all Moku devices
- **Device Discovery**: [Finder](finder.md) - Find Moku devices on network
- **Session Management**: [RequestSession](session.md) - HTTP API communication

### Instrument Categories

| Category | Instruments |
|----------|-------------|
| **Generators** | [WaveformGenerator](instruments/waveformgenerator.md), [ArbitraryWaveformGenerator](instruments/awg.md) |
| **Oscilloscopes** | [Oscilloscope](instruments/oscilloscope.md) |
| **Spectrum** | [SpectrumAnalyzer](instruments/spectrumanalyzer.md), [Phasemeter](instruments/phasemeter.md) |
| **Filters** | [DigitalFilterBox](instruments/digitalfilterbox.md), [FIRFilterBox](instruments/firfilter.md) |
| **Control** | [PIDController](instruments/pidcontroller.md), [LaserLockBox](instruments/laserlockbox.md) |
| **Analysis** | [FrequencyResponseAnalyzer](instruments/fra.md), [LockInAmp](instruments/lockinamp.md), [TimeFrequencyAnalyzer](instruments/tfa.md) |
| **Digital** | [LogicAnalyzer](instruments/logicanalyzer.md) |
| **Data** | [Datalogger](instruments/datalogger.md) |
| **Streaming** | [GigabitStreamer / GigabitStreamerPlus](instruments/gigabitstreamer.md) |
| **Advanced** | [MultiInstrument](instruments/mim.md), [CustomInstrument](instruments/custominstrument.md), [NeuralNetwork](instruments/nn.md) |

## Documentation Format

Each markdown file includes:
- **YAML frontmatter** - Date, source file path, and title
- **Overview** - High-level description of the module's purpose
- **Key Dependencies** - Important imports and what they're used for
- **Classes** - Main classes with method signatures
- **Functions** - Module-level functions with parameters and return types
- **Obsidian callouts** - Important notes, warnings, and examples
- **See Also** - Links to related modules and official documentation

## About This Documentation

- **Source Package**: `moku` v4.2.2.1
- **Format**: Obsidian-friendly markdown
- **Level**: High-level overview focusing on public APIs
- **Generated**: 2025-11-17 (refreshed against v4.2.2.1 on 2026-05-18)
- **Original Package Location**: `/Users/johnycsh/DPD/UPD-001/PD2/.venv/lib/python3.12/site-packages/moku`

## Additional Resources

- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)
- Original Python package: `pip install moku`

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/README)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/README.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/README.md)
