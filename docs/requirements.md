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

### Axis coverage and extensibility

- FCS-AXIS-001: The baseline control architecture shall include pitch, roll, and yaw axes.
- FCS-AXIS-002: The architecture shall support optional flap and spoiler control axes.
- FCS-AXIS-003: The architecture shall allow additional unknown axes to be introduced without breaking existing axis contracts.
- FCS-AXIS-004: Axis command arbitration shall be deterministic when multiple providers command the same axis.

### Avionics command ingress

- FCS-AVX-001: The system shall support a normalized autopilot command interface independent of vendor-specific payload formats.
- FCS-AVX-002: The ingress architecture shall use vendor adapters to map payloads into normalized command objects.
- FCS-AVX-003: Unknown vendor payloads shall be ignored safely without affecting flight-control command integrity.

### Actuator interface

- FCS-ACT-001: The actuator interface shall be actuator-vendor agnostic at the protocol layer.
- FCS-ACT-002: Command messages shall support at least position, rate, and effort control modes.
- FCS-ACT-003: Feedback messages shall include position, rate, current, temperature, and supply voltage fields.
- FCS-ACT-004: Command and feedback messages shall include integrity protection (CRC).
- FCS-ACT-005: The architecture shall not rely on direct analog voltage control as the sole command method.
- FCS-ACT-006: The system shall support actuator profile adapters that map normalized axes to vendor-specific actuator IDs and limits.
- FCS-ACT-007: At least three actuator profile examples shall be provided, including one future thrust-axis bridge profile.
- FCS-ACT-008: Actuator feedback monitoring shall detect persistent communication timeouts and surface degradation events.
- FCS-ACT-009: Actuator feedback monitoring shall detect position mismatch and overtemperature conditions against configurable thresholds.

### Configurable control laws

- FCS-LAW-001: The system shall load control-law protection limits from user-editable configuration files.
- FCS-LAW-002: Control-law protections shall include minimum airspeed (stall protection), maximum airspeed (overspeed protection), and maximum bank angle protection.
- FCS-LAW-003: At least two example control-law profiles shall be provided for different GA aircraft classes.
- FCS-LAW-004: Protection activity flags shall be exposed for telemetry and test validation.

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
- FCS-VER-005: Tests shall verify configurable protection behavior for stall, overspeed, and excessive bank conditions.
- FCS-VER-006: Tests shall verify plugin/provider arbitration behavior for required, optional, and future axes.
- FCS-VER-007: Tests shall verify autopilot ingress normalization for at least one generic vendor adapter.
- FCS-VER-008: Tests shall verify actuator command and feedback codec roundtrip behavior and CRC rejection.
- FCS-VER-009: Tests shall verify actuator profile adapter mappings for baseline and future-axis profiles.
- FCS-VER-010: Tests shall verify actuator runtime monitoring for mismatch, timeout persistence, and event logging behavior.

## Notes

- This is a draft baseline for experimental development and will evolve with plant modeling and hardware constraints.
- Standards references are guidance only and do not imply certification compliance.
