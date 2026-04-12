# Actuator Profile Adapters (v0.1)

This architecture defines profile adapters that map generic axis commands to specific actuator fleets.

## Why profiles

- Keep FCC and control-law core independent from actuator vendor details.
- Allow mixed hardware generations across development phases.
- Support future channels like thrust without changing core arbitration.

## Profile fields

- profile_name
- vendor_key
- default_mode
- max_rate_norm_per_s
- max_effort_norm
- enable_local_limits
- axis_to_actuator map

## Included profile examples

- generic_servo: baseline smart servo mapping for pitch/roll/yaw/flap
- smart_ema: higher-authority electromechanical mapping with rate mode
- fadec_bridge: future thrust axis mapping for FADEC bridge integration (vendor_key: fadec-bridge)

## Runtime flow

1. Choose profile by vendor_key.
2. Convert normalized axis commands into actuator command objects.
3. Encode via actuator codec for transport.
4. Process actuator feedback and health telemetry.

## Safety notes

- Profiles only map commands; they do not replace actuator qualification.
- Rate and effort limits in profile are bounded and explicitly configured.
- Local actuator limits should remain enabled in normal operation.
