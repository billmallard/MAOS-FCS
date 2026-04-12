# CAN-FD Actuator Wire Format (v0.1)

This document defines generic command and feedback frames for smart flight-control actuators.

## Rationale

The interface is intentionally actuator-vendor agnostic. It supports position-control servos, electro-hydraulic valves, and future FADEC-adjacent channels with bounded numeric fields and explicit health status.

## Command frame

- Payload length: 18 bytes
- Endianness: little-endian

### Byte layout

- 0: protocol_version (u8)
- 1: actuator_id (u8)
- 2: control_mode (u8)
- 3: enable_flags (u8)
- 4-7: sequence (u32)
- 8-9: target_position_norm_x10000 (i16)
- 10-11: target_rate_norm_per_s_x1000 (u16)
- 12-13: max_effort_norm_x1000 (u16)
- 14-17: crc32 over bytes 0-13 (u32)

### control_mode enum

- 0: position
- 1: rate
- 2: effort
- 3: standby

### enable_flags bitfield

- bit 0: channel_enable
- bit 1: local_limit_enable
- bit 2: reserved
- bit 3: reserved

## Feedback frame

- Payload length: 22 bytes
- Endianness: little-endian

### Byte layout

- 0: protocol_version (u8)
- 1: actuator_id (u8)
- 2: feedback_mode (u8)
- 3: fault_flags (u8)
- 4-7: sequence_echo (u32)
- 8-9: measured_position_norm_x10000 (i16)
- 10-11: measured_rate_norm_per_s_x1000 (i16)
- 12-13: motor_current_a_x100 (u16)
- 14-15: temperature_c_x10 (i16)
- 16-17: supply_voltage_v_x100 (u16)
- 18-21: crc32 over bytes 0-17 (u32)

### fault_flags bitfield

- bit 0: overcurrent
- bit 1: overtemperature
- bit 2: position_mismatch
- bit 3: comm_timeout

## Notes

- This interface carries normalized commands, not raw analog voltage instructions.
- Local actuator loops are expected to enforce current and travel limits.
- Invalid CRC or invalid length frames are discarded.
