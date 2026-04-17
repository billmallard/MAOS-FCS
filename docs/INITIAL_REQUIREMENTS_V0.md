# MAOS-FCS Initial Requirements v0 (Program Seed)

Status: Draft / Working notes. Intentionally early and incomplete.
Purpose: Provide a concise seed set aligned with cross-repo project planning.

Note: Detailed FCS requirements already exist in docs/requirements.md. This file is the lightweight planning baseline for cross-project alignment.

## Functional Requirements

- FCS-SEED-001: The system shall support triplex FCC operation with deterministic lane health publication.
- FCS-SEED-002: The voter shall support triplex and degraded duplex operation modes.
- FCS-SEED-003: The control stack shall support normal, degraded, and fail-safe mode declarations.
- FCS-SEED-004: Control outputs shall be deterministic for a given input/state set.

## Interface Requirements

- FCS-SEED-IF-001: Cross-channel messages shall define cycle counters and integrity checks.
- FCS-SEED-IF-002: Actuator command/feedback interfaces shall be vendor-agnostic at the protocol level.
- FCS-SEED-IF-003: Control input/output units and sign conventions shall be explicitly versioned.
- FCS-SEED-IF-004: Timeout behavior for sensor and actuator interfaces shall be explicitly defined.

## Safety and Fault Requirements

- FCS-SEED-FLT-001: The system shall isolate a deviating lane when deviation exceeds configured threshold.
- FCS-SEED-FLT-002: Fewer than two healthy lanes shall force fail-safe behavior.
- FCS-SEED-FLT-003: Mode and fault transitions shall be logged with timestamp and reason code.
- FCS-SEED-FLT-004: Fault handling shall be deterministic and testable.

## Verification Requirements

- FCS-SEED-VER-001: SIL tests shall cover nominal triplex operation.
- FCS-SEED-VER-002: SIL tests shall cover lane outlier and lane dropout scenarios.
- FCS-SEED-VER-003: Requirements shall map to automated test evidence where practical.
- FCS-SEED-VER-004: Open requirement gaps shall be tracked explicitly.
