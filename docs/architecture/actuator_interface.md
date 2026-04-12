# Actuator Interface Guidance (v0.1)

## Do we need one specific actuator now?

No. The first-pass architecture should remain actuator-vendor agnostic.

## Common control patterns

Most flight-control actuators are not driven by a single analog voltage command from FCC to motor.

Typical pattern:

- FCC sends digital command setpoints (position, rate, or effort).
- Local actuator controller closes the fast motor/current loop.
- Actuator reports feedback and health telemetry.

## Why not voltage-only control

Voltage-only control is usually too weak for robust FBW behavior because it lacks standardized semantics, integrity checks, and explicit fault feedback.

## Recommended first-pass contract

- Command modes: position, rate, effort, standby.
- Feedback: measured position, measured rate, motor current, temperature, supply voltage.
- Integrity: CRC on each frame.
- Transport: CAN-FD in v0.1 simulation model.

## Future integration path

- Create vendor adapter profiles that map this generic contract to specific actuator products.
- Keep FCC control laws independent from vendor-specific packet formats.
- Add actuator qualification tests per profile before hardware flight-like testing.
