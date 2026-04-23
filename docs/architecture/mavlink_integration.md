# MAVLink Integration Architecture (v0.1)

## Purpose

This document defines how MAVLink fits into the MAOS-FCS external interface
layer — what it is used for, what is explicitly out of scope, and the
concrete implementation plan.

---

## What MAVLink Is

MAVLink is a lightweight binary messaging protocol for drone and autopilot
systems, in production since 2009. It is the native protocol of ArduPilot and
PX4. Key properties relevant to MAOS:

- Binary framing, 8–14 bytes overhead per packet
- Publish-subscribe for data streams, point-to-point for commands
- Code-generated from XML dialect definitions — no runtime dependency on
  the generator
- Implementations in C, Python, Rust, and others
- Supported natively by QGroundControl and Mission Planner ground stations

---

## Scope: Where MAVLink Belongs in MAOS

MAVLink is an **external interface protocol**, not an internal bus. It sits
at system boundaries — between MAOS-FCS and ground stations, simulators,
and future external modules. It does not replace CAN-FIX for intra-aircraft
sensor data, and it does not replace the ControlProvider interface for
internal command routing.

| Boundary | Protocol | Rationale |
|----------|----------|-----------|
| Sensor → FCS (intra-aircraft) | CAN-FIX | Low-latency, deterministic, bus topology |
| Internal FCS command routing | ControlProvider protocol | Clean Python interface, no serialization overhead |
| FCS → Ground station (telemetry) | MAVLink | Ecosystem compatibility, QGroundControl support |
| FCS → Simulator (SIL) | MAVLink or X-Plane UDP | MAVLink preferred for new work; X-Plane UDP retained for direct X-Plane access |
| FCS → Future MAOS-AUTOPILOT | MAVLink or ControlProvider | TBD at MAOS-AUTOPILOT design time |

---

## Why Not Fork the Libraries

MAVLink is a code-generation workflow. The repositories are:

- **`mavlink/mavlink`** — XML message definitions and the generator toolchain.
  Consumed, not forked. The value of MAVLink is ecosystem compatibility;
  forking diverges from that.
- **`pymavlink`** — Python parsing/generation library. Used as a pip
  dependency, not forked.

Forking either repository would mean maintaining a private copy of the
protocol forever. MAOS instead defines a custom **dialect** (a small XML
extension file) that adds MAOS-specific messages on top of the standard
`common.xml` message set.

---

## Implementation Plan

### 1. MAOS Dialect XML (`maos.xml`)

A dialect file extending `common.xml` with MAOS-specific messages not
present in the standard set:

- Triplex operating mode (`TRIPLEX`, `DEGRADED`, `FAIL_SAFE`)
- Lane health status per lane (A, B, C)
- Active protection flags (stall, overspeed, bank, AoA, calibration mode)
- Calibration mode active flag

Location: `sim/mavlink/maos.xml`

The dialect is kept minimal. Standard flight data (attitude, position,
airspeed, actuator commands) uses existing `common.xml` messages directly.

### 2. Generated Python Module

The generator is run at development time (not at runtime) against `maos.xml`
to produce a Python module committed to the repo. No build-time code
generation dependency.

```bash
python3 -m pymavlink.tools.mavgen \
    --lang=Python \
    --wire-protocol=2.0 \
    --output=sim/mavlink/generated \
    sim/mavlink/maos.xml
```

### 3. MAVLink Telemetry Output (`sim/mavlink_telemetry.py`)

A lightweight module that serializes `FlightState` and `ProtectionResult`
into MAVLink messages and sends them over UDP to a ground station (default
port 14550 — QGroundControl default).

Messages sent each control cycle:
- `HEARTBEAT` — system type, mode
- `ATTITUDE` — roll, pitch, yaw, angular rates from `FlightState`
- `VFR_HUD` — airspeed, groundspeed, altitude, throttle
- `NAMED_VALUE_FLOAT` — protection flags (one message per active flag)
- MAOS dialect messages — triplex mode, lane health

This module is optional and runs alongside the existing FCS pipeline with
no effect on control outputs.

### 4. MAVLink SIL Bridge (`sim/mavlink_sil_bridge.py`)

Implements the `ControlProvider` protocol using MAVLink as the transport,
replacing the direct X-Plane UDP bridge for simulators that speak MAVLink
(ArduPilot SITL, Gazebo, JSBSim via MAVLink). The existing X-Plane UDP
bridge (`sim/xplane_bridge.py`) is retained for direct X-Plane integration
since X-Plane's native protocol is simpler for that use case.

---

## Standard Messages Used (no dialect needed)

| MAVLink Message | MAOS Use |
|-----------------|----------|
| `HEARTBEAT (0)` | System health, operating mode |
| `ATTITUDE (30)` | Roll, pitch, yaw, angular rates |
| `VFR_HUD (74)` | Airspeed, altitude, heading |
| `GLOBAL_POSITION_INT (33)` | GPS position, groundspeed |
| `SET_ATTITUDE_TARGET (82)` | Autopilot attitude commands in (future MAOS-AUTOPILOT → FCS path) |
| `HIL_ACTUATOR_CONTROLS (93)` | Normalized [-1, 1] actuator commands for SIL |
| `GPS_RAW_INT (24)` | Raw GPS fix data |
| `HIGHRES_IMU (105)` | IMU sensor data in SIL |
| `SYS_STATUS (1)` | Sensor health bitmap |

---

## MAOS-Specific Dialect Messages (proposed)

```xml
<message id="50000" name="MAOS_FCS_STATUS">
  <description>MAOS-FCS operating mode and lane health.</description>
  <field type="uint8_t" name="operating_mode" enum="MAOS_OPERATING_MODE">
    Triplex=0, Degraded=1, FailSafe=2
  </field>
  <field type="uint8_t" name="lane_health">
    Bitmask: bit0=LaneA, bit1=LaneB, bit2=LaneC (1=healthy)
  </field>
  <field type="uint16_t" name="protection_flags">
    Bitmask of active protection flags (stall, overspeed, bank, AoA, cal_mode)
  </field>
</message>
```

Full dialect definition to be written when the telemetry module is
implemented. Message IDs in the 50000+ range are reserved for
vendor-specific use in MAVLink v2.

---

## Development Tooling Benefit

With MAVLink telemetry output active, **QGroundControl** provides a
free real-time instrument panel during SIL and bench testing:

- Attitude indicator, airspeed, altitude, heading
- Custom parameter display (protection flags, lane health)
- Flight data logging (`.tlog` format)
- Replay of logged sessions

This eliminates the need to build custom debug instrumentation for
most development scenarios.

---

## Requirements Cross-Reference

This architecture supports the following SIL requirements from
`requirements.md`:

- FCS-SIL-001: External simulator as plant model via network interface
- FCS-SIL-004: Complete FCS pipeline exercised in SIL loop
- FCS-SIL-005: SIL events logged in standard format

New requirements to be added:

- FCS-MAV-001: MAOS-FCS shall output MAVLink telemetry over UDP each
  control cycle when a ground station address is configured.
- FCS-MAV-002: Telemetry output shall not affect control loop timing
  or voted command output.
- FCS-MAV-003: A MAOS dialect XML shall define MAOS-specific status
  messages not present in `common.xml`.
- FCS-MAV-004: The MAVLink SIL bridge shall implement `ControlProvider`
  so MAVLink-speaking simulators participate in the existing
  priority-arbitration path without special-casing.
