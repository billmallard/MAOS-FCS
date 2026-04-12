# Configurable Control Laws (v0.1)

This design supports sophisticated user configuration of envelope protections while preserving deterministic execution behavior.

## Goals

- Adaptable across a wide range of GA airframes.
- User-tunable limits without recompiling simulation tools.
- Protection behaviors that remain bounded and testable.

## Baseline protections

- Stall protection via minimum-airspeed threshold.
- Overspeed protection via maximum-airspeed threshold.
- Excessive bank-angle protection via maximum-bank threshold.

## Configuration model

Profiles are JSON files in configs/control_laws.

Current examples:

- ga_default.json
- ga_high_performance.json

## Runtime behavior

- Raw commands are accepted from providers/autopilot ingress.
- Protection logic clamps commands only when envelope limits are exceeded.
- Protection flags are emitted for telemetry and regression testing.

## Future enhancements

- gain scheduling by flap position and weight class
- AoA-based stall margin protection
- adaptive limits by flight phase and turbulence level
