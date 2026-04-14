# MAOS-FCS

Open-source Fly-By-Wire Flight Control System for MAOS aircraft concepts.

## Role in MAOS Multi-Project Architecture

This repository owns the flight-control domain for the MAOS program.

- It is not the airframe authority (MAOS-DESIGN owns geometric and aircraft-level configuration baselines).
- It is not the ECS authority (MAOS-ECS owns thermal and pressurization subsystem design).
- It is responsible for FCS requirements, interfaces, implementation, and verification artifacts.

The repo split is intentional: each subsystem can progress independently while integration happens through explicit, versioned interfaces.

## Status

Concept and architecture phase.

## Safety Notice

This repository is for research and experimental development only. It is not approved for manned flight and must not be used as-is in safety-critical operation without formal system safety assessment, verification, validation, and regulatory compliance.

This project targets the Experimental Amateur-Built category. FAA certification is not a current design constraint, but engineering decisions should still follow established fly-by-wire and safety-critical best practices.

## Mission

Build a practical, open-source, certification-informed Flight Control System (FCS) architecture with:

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
- configs  User-tunable control-law profiles

## Interface-First Integration Rules

Before major feature work, freeze and version these interfaces:

- Control input/output units, signs, rates, and saturation semantics.
- Timing contracts (publish/subscribe rates, jitter budgets, timeout behavior).
- Fault semantics (degraded mode triggers, lane health states, fail-operational/fail-safe transitions).
- Logging and event taxonomies used by SIL/HIL and incident replay tools.

Cross-repo integration should depend on these contracts, not on implicit behavior.

Starter template: `INTERFACE_CONTROL_DOCUMENT_TEMPLATE.md`

## Verification Strategy

- Unit tests for control primitives and protocol parsing
- SIL (software-in-the-loop) closed-loop Monte Carlo testing
- HIL tests with injected faults (sensor bias, stuck actuator, lane dropout)
- Traceable requirements-to-test mapping
- Static analysis and coding-standard enforcement

## Robot Regression Harness

For unattended, repeatable X-Plane SIL runs, use the Robot Framework harness:

- Test suite: `tests/robot/sil_campaign.robot`
- Manifest suite: `tests/robot/sil_manifest.robot`
- Manifest keywords: `tests/robot/resources/sil_manifest_keywords.robot`
- Example manifest: `tests/robot/manifests/smoke_manifest.json`
- Runner: `tools/testing/run_robot_sil_tests.ps1`
- Campaign engine: `tools/testing/run_sil_campaign_webapi.py`

Examples:

- Smoke campaign suite:
	- `powershell -ExecutionPolicy Bypass -File tools/testing/run_robot_sil_tests.ps1 -Suite smoke`
- Default regression suite:
	- `powershell -ExecutionPolicy Bypass -File tools/testing/run_robot_sil_tests.ps1 -Suite regression`
- Manifest-driven suite:
	- `powershell -ExecutionPolicy Bypass -File tools/testing/run_robot_sil_tests.ps1 -Suite manifest`

Outputs:

- Robot reports: `logs/robot/`
- Campaign artifacts: `logs/sil_campaign/<timestamp>/`

The campaign engine also accepts a custom manifest directly:

- `python tools/testing/run_sil_campaign_webapi.py --manifest tests/robot/manifests/smoke_manifest.json`

Reset/startup flow (recommended for repeatability):

- Define `startup_flight` in manifest and set `reset_each_run: true`
- Optional settle delay: `reset_wait_s`
- Optional reset robustness tuning: `reset_request_timeout_s` and `reset_retries`
- Example manifest:
	- `tests/robot/manifests/reset_smoke_manifest.json`

Example command:

- `python tools/testing/run_sil_campaign_webapi.py --manifest tests/robot/manifests/reset_smoke_manifest.json --stabilize-on-exit`

Readiness handling:

- Default behavior classifies readiness failures as `INFRA_FAIL` per scenario and continues.
- Strict mode stops execution before scenarios:
	- `python tools/testing/run_sil_campaign_webapi.py --manifest tests/robot/manifests/smoke_manifest.json --strict-readiness`

Campaign summary outputs per run:

- `logs/sil_campaign/<timestamp>/campaign_summary.json`
- `logs/sil_campaign/<timestamp>/campaign_summary.md`
- `logs/sil_campaign/<timestamp>/summary.json` (legacy-compatible alias)

Safety cleanup controls:

- `--stabilize-on-exit` level wings and apply mild climb guidance toward target altitude
- `--cleanup-target-altitude-ft 2000` target climb altitude for cleanup guidance
- `--pause-on-exit` pause simulator at end of campaign (enabled by default)

## Knowledge Migration

- Article-derived subsystem migration notes: `docs/ARTICLE_KNOWLEDGE_MIGRATION_2026Q2.md`

## Licensing

This repository uses a dual-license model:

- Source code: PolyForm Noncommercial 1.0.0 (`LICENSE-CODE`)
- Documentation and non-code design content: CC BY-NC-SA 4.0 (`LICENSE-DOCS`)

Commercial use is not granted by default. For commercial licensing, contact `contact@aerocommons.org`.

Contribution and file classification guidance: `CONTRIBUTING.md`

## Security Scanning and Secret Hygiene

- GitHub CodeQL SAST runs via CI on push, pull request, and weekly schedule.
- GitHub CI secret scanning is enforced with Gitleaks on push, pull request, and weekly schedule.
- Local pre-commit hooks are available to catch private keys and common secret mistakes before commit.

See [SECURITY.md](SECURITY.md) for policy, reporting, and emergency secret rotation guidance.

## Certification-style References

Use these as best-practice references, not as claims of certification or compliance:

- ARP4754A (system development)
- ARP4761 (safety assessment)
- DO-178C (software)
- DO-254 (complex electronic hardware)

See CLAUDE.md for project policy language on certification scope and documentation constraints.

## Current Milestone State (As of 2026-04-14)

Recent completed milestone:

- Deterministic X-Plane SIL reset-per-scenario flow implemented.
- Airborne post-reset initialization path implemented.
- Readiness classification and infra-failure semantics implemented.
- Campaign summary artifacts standardized (`campaign_summary.json`, `campaign_summary.md`, `summary.json`).

Primary current gap:

- Propulsion-state initialization after airborne reset needs hardening for longer-duration scenario energy stability.

Near-term execution milestones:

1. Add throttle/energy hold in post-reset airborne initialization path.
2. Extend scenario duration windows after propulsion stabilization.
3. Re-run Robot manifest reset suite and verify PASS in `output.xml`.
4. Validate self-hosted `workflow_dispatch` campaign run and artifact upload end-to-end.

Reference handoff: `docs/CLAUDE_HANDOFF_2026-04-14.md`.
