# MAOS-FCS

Open-source Fly-By-Wire Flight Control System for MAOS aircraft concepts.

## Status

Concept and architecture phase.

## Safety Notice

This repository is for research and experimental development only. It is not approved for manned flight and must not be used as-is in safety-critical operation without formal system safety assessment, verification, validation, and regulatory compliance.

This project targets the Experimental Amateur-Built category. FAA certification is not a current design constraint, but engineering decisions should still follow established fly-by-wire and safety-critical best practices.

## Mission

Build a practical, open-source, certifiable-style Flight Control System (FCS) architecture with:

- Triplex flight control computers (FCC-A, FCC-B, FCC-C)
- Redundant sensors and air data
- Fault-tolerant control-law execution
- Deterministic actuator command voting and monitoring
- Clear pathway from simulation to hardware-in-the-loop and flight test

## System Architecture (Triplex)

### 1. Redundant FCC lanes

Three independent FCC lanes run the same control laws on independent hardware:

- FCC-A
- FCC-B
- FCC-C

Each lane has:

- Its own MCU/SoC, clock source, and power feed
- Its own sensor inputs (or independently conditioned sensor feeds)
- Cross-channel data link to the other lanes
- Built-in tests (power-up BIT and continuous BIT)

Recommended baseline hardware class:

- STM32H7 or NXP S32K3 class MCU for deterministic hard real-time
- CAN-FD controllers with dual independent buses
- ECC memory and watchdog support

### 2. How they agree or disagree

Each control cycle (for example 200 Hz inner loop):

1. Each lane computes a commanded surface position/torque.
2. Lanes broadcast their command and health status on redundant cross-channel buses.
3. A voter computes majority or median-select output.
4. If one lane deviates beyond threshold, it is flagged failed and removed from authority.
5. Remaining two lanes continue in duplex mode with tighter monitoring.
6. If further degradation occurs, system transitions to direct/degraded law.

Typical voting methods:

- Mid-value select for analog-like commands
- 2-out-of-3 majority for discrete states
- Lane confidence weighting only after strict fault detection proof

Fault examples handled:

- Stuck-at output from one FCC lane
- Corrupted cross-channel packet (CRC fail)
- Sensor disagreement in one lane
- Missed deadlines (timing watchdog)

### 3. Actuation concept

Primary surfaces use smart electromechanical actuators with:

- Dual position feedback sensors per actuator
- Current, temperature, and travel monitoring
- Local rate/limit enforcement
- Fail-safe mode on lost command stream

For early phases, use servo-based benchtop actuators for development, then move to aviation-grade actuators for flight hardware.

## Sensor and Air Data Architecture

## Required sensor sets

### Flight dynamics

- 3x IMU sets (gyro + accelerometer), one per lane or one independent sensor cluster with triplicated conditioning
- 2x to 3x magnetometers (optional for high-rate control, useful for alignment and backup modes)
- GNSS (dual receiver preferred) for navigation and velocity aiding

### Air data

- Redundant pitot-static pressure sensing
- Angle-of-attack (AoA) vane or differential pressure AoA probe
- Optional sideslip measurement (beta vane or multi-hole probe)
- Total air temperature sensor

### Aircraft state and command inputs

- Control stick and pedal position sensors (dual-channel per axis)
- Surface position feedback sensors (dual-channel)
- Flap/trim/gear discrete and analog states
- Power system voltage/current telemetry

## Air Data Computer (ADC)

Recommended architecture:

- Two independent ADC modules (ADC-1, ADC-2)
- Each ADC has independent pressure sensor chain and MCU
- FCC lanes read both ADC outputs and perform reasonableness checks

Early development path:

- Prototype ADC with high-resolution pressure transducers and temperature compensation
- Validate against calibrated pitot-static test rig

## Software Stack

## What software we are writing

### Onboard real-time software

- Sensor drivers and sensor fusion
- Air data estimation
- Flight control laws (inner and outer loops)
- Mode logic (normal law, alternate law, direct law)
- Built-in test and fault management
- Actuator command and monitor interfaces
- Cross-channel synchronization and voting logic

### Offboard software

- Ground station for telemetry and health monitoring
- Log decode and fault replay tools
- Simulation and plant models
- Hardware-in-the-loop test harness

## Language choices

Recommended default for FCC firmware:

- C (C17 subset) for hard real-time embedded firmware and broad toolchain maturity

Recommended support languages:

- Python for simulation scripts, log analysis, and test orchestration
- Optional Rust for non-flight-critical support tooling if desired

Why C first:

- Deterministic runtime behavior
- Mature MCU support ecosystem
- Easier path toward certifiable development processes

## Deterministic timing targets

Initial timing budget proposal:

- Inner loop: 200 Hz to 500 Hz
- Outer loop: 50 Hz to 100 Hz
- Sensor acquisition: 500 Hz to 1 kHz for IMU path
- End-to-end command latency target: under 20 ms

## Initial Repository Plan

Planned layout:

- firmware/fcc  Triplex FCC embedded code
- firmware/adc  Air data computer firmware
- libs/control  Shared control law math library
- libs/protocol  Deterministic cross-channel and actuator protocol definitions
- sim  Plant models and closed-loop simulation
- hil  Hardware-in-the-loop test scenarios
- tools  Ground and analysis scripts
- docs  Architecture, safety, interface specs

## Verification Strategy

- Unit tests for control primitives and protocol parsing
- SIL (software-in-the-loop) closed-loop Monte Carlo testing
- HIL tests with injected faults (sensor bias, stuck actuator, lane dropout)
- Traceable requirements-to-test mapping
- Static analysis and coding-standard enforcement

## Certification-style References

Use these as best-practice references, not as claims of certification or compliance:

- ARP4754A (system development)
- ARP4761 (safety assessment)
- DO-178C (software)
- DO-254 (complex electronic hardware)

See CLAUDE.md for project policy language on certification scope and documentation constraints.

## First coding milestone (M1)

Build a deterministic triplex command-voting prototype that runs in simulation:

1. Simulate 3 FCC lanes producing elevator command.
2. Implement mid-value select and fault detection thresholds.
3. Inject one faulty lane and verify correct isolation.
4. Export logs and pass/fail report.

This milestone establishes the core redundancy behavior before hardware lock-in.

## Immediate next steps

1. Define flight phase and control mode requirements in docs/requirements.md.
2. Implement libs/protocol message schema for lane health and command exchange.
3. Implement sim/triplex_voter prototype and fault-injection tests.
4. Freeze hardware interfaces for FCC and ADC v0.1.
