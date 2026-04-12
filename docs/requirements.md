# MAOS-FCS Requirements (v0.1 Draft)

This document defines initial, testable requirements for the triplex FBW architecture.

## Scope

These requirements cover:

- Triplex FCC lane behavior
- Cross-channel voting behavior
- Degradation behavior
- Core timing for closed-loop control
- Baseline validation criteria for simulation

## Requirement IDs

### System timing

- FCS-SYS-001: The inner-loop control cycle shall execute at 200 Hz minimum.
- FCS-SYS-002: The design target inner-loop rate shall be configurable up to 500 Hz.
- FCS-SYS-003: End-to-end command latency from sensor sample to voted command output shall be less than 20 ms in nominal operation.

### Lane execution and health

- FCS-LANE-001: The system shall support three independent FCC lanes identified as A, B, and C.
- FCS-LANE-002: Each lane shall publish a command value and lane health status each control cycle.
- FCS-LANE-003: Each lane shall include a monotonic cycle counter in cross-channel messages.
- FCS-LANE-004: Each lane shall include message integrity protection (CRC) in cross-channel messages.

### Voting and fault isolation

- FCS-VOTE-001: In triplex mode, continuous command channels shall use mid-value select voting.
- FCS-VOTE-002: In triplex mode, discrete command channels shall use 2-out-of-3 majority voting.
- FCS-VOTE-003: If one lane command deviates from voted value by more than configured threshold, the lane shall be marked failed for that cycle.
- FCS-VOTE-004: With one failed lane, the system shall transition to degraded duplex operation.
- FCS-VOTE-005: In duplex operation, command output shall use average of the two healthy lanes unless a stricter strategy is configured.

### Degraded behavior

- FCS-DEG-001: The system shall expose operating mode as one of: triplex, degraded, or fail-safe.
- FCS-DEG-002: If fewer than two healthy lanes are available, the voter shall not output a normal command and shall enter fail-safe behavior.
- FCS-DEG-003: Mode transitions shall be logged with timestamp and reason code.

### Verification

- FCS-VER-001: Simulation tests shall include nominal triplex operation with no lane faults.
- FCS-VER-002: Simulation tests shall include single-lane command outlier injection and verify isolation.
- FCS-VER-003: Simulation tests shall include lane dropout resulting in duplex operation.
- FCS-VER-004: Requirement coverage shall map each implemented test to one or more requirement IDs.

## Notes

- This is a draft baseline for experimental development and will evolve with plant modeling and hardware constraints.
- Standards references are guidance only and do not imply certification compliance.
