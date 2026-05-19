---
date: 2025-11-17
path_to_py_file: moku/instruments/__init__.py
title: instruments.__init__
created: 2025-11-19
modified: 2025-12-10 05:02:56
accessed: 2025-12-10 05:03:20
---

# Overview

This module serves as the main entry point for the Moku instruments package. It provides a centralized import interface for all available instrument classes, making them accessible through a single import statement.

> [!info] Key Dependencies
> This module imports 18 different instrument implementations from private modules:
> - `_awg` - Arbitrary Waveform Generator
> - `_custominstrument` - Custom Instrument (replaces deprecated CloudCompile)
> - `_datalogger` - Data logging functionality
> - `_digitalfilterbox` - Digital filtering operations
> - `_firfilter` - FIR (Finite Impulse Response) filter
> - `_fra` - Frequency Response Analyzer
> - `_gs` - GigabitStreamer and GigabitStreamerPlus (UDP streaming)
> - `_laserlockbox` - Laser locking capabilities
> - `_lockinamp` - Lock-in Amplifier
> - `_logicanalyzer` - Logic analysis tools
> - `_mim` - Multi-Instrument mode
> - `_oscilloscope` - Oscilloscope functionality
> - `_phasemeter` - Phase measurement
> - `_pidcontroller` - PID (Proportional-Integral-Derivative) controller
> - `_spectrumanalyzer` - Spectrum analysis
> - `_waveformgenerator` - Waveform generation
> - `_tfa` - Time-Frequency Analyzer
> - `_nn` - Neural Network

# Classes

## ArbitraryWaveformGenerator

Imported from `_awg` module. Provides arbitrary waveform generation capabilities for creating custom signal patterns.

## CustomInstrument

Imported from `_custominstrument` module. Deploys custom user-defined instruments created via Moku's cloud compilation service. Provides control register interface and status register readback.

## CustomInstrumentPlus

Imported from `_custominstrument` module. Variant of CustomInstrument for larger custom designs.

## CloudCompile

Imported from `_custominstrument` module. **DEPRECATED** subclass of `CustomInstrument` — prints a warning on instantiation and forwards to `CustomInstrument`. Use `CustomInstrument` directly in new code.

## Datalogger

Imported from `_datalogger` module. Provides data logging and recording functionality for capturing instrument measurements.

## DigitalFilterBox

Imported from `_digitalfilterbox` module. Implements digital filtering operations for signal processing.

## FIRFilterBox

Imported from `_firfilter` module. Provides FIR (Finite Impulse Response) filtering capabilities for signal processing applications.

## FrequencyResponseAnalyzer

Imported from `_fra` module. Analyzes frequency response characteristics of systems and signals.

## LaserLockBox

Imported from `_laserlockbox` module. Provides laser locking and stabilization functionality for optical applications.

## LockInAmp

Imported from `_lockinamp` module. Implements lock-in amplifier functionality for precision signal measurement in noisy environments.

## LogicAnalyzer

Imported from `_logicanalyzer` module. Provides digital logic analysis and debugging capabilities.

## MultiInstrument

Imported from `_mim` module. Enables multiple instrument modes to operate simultaneously on a single Moku device.

## Oscilloscope

Imported from `_oscilloscope` module. Provides oscilloscope functionality for time-domain signal visualization and measurement.

## Phasemeter

Imported from `_phasemeter` module. Measures phase relationships between signals with high precision.

## PIDController

Imported from `_pidcontroller` module. Implements PID (Proportional-Integral-Derivative) control algorithms for feedback control systems.

## SpectrumAnalyzer

Imported from `_spectrumanalyzer` module. Analyzes signals in the frequency domain for spectral content.

## WaveformGenerator

Imported from `_waveformgenerator` module. Generates standard waveforms (sine, square, triangle, etc.) for testing and signal generation.

## TimeFrequencyAnalyzer

Imported from `_tfa` module. Provides time-frequency analysis capabilities for signals that vary in both domains.

## NeuralNetwork

Imported from `_nn` module. Implements neural network functionality on the Moku platform.

## GigabitStreamer

Imported from `_gs` module. Provides UDP data streaming via SFP ports at gigabit speeds.

## GigabitStreamerPlus

Imported from `_gs` module. Provides UDP data streaming via QSFP port at higher speeds.

# Functions

This module contains no standalone functions. It serves solely as a package-level import aggregator.

> [!note] Implementation Notes
> All imports use the `# noqa` comment to suppress linter warnings about unused imports. This is appropriate for an `__init__.py` file that exists to re-export classes from submodules. The pattern allows users to import instruments directly from the `moku.instruments` package rather than navigating to individual private modules.

# See Also

- Individual instrument modules in the `moku.instruments` package
- Each class is implemented in its corresponding private module (prefixed with underscore)
