# CAN-FD Lane Wire Format (v0.1)

This document defines the compact binary wire format for lane-to-lane command exchange.

## Frame size

- Payload length: 22 bytes
- Intended transport: CAN-FD data field
- Endianness: little-endian

## Byte layout

- 0: protocol_version (u8)
- 1: lane_id (u8)
- 2: mode (u8)
- 3: health_flags (u8 bitfield)
- 4: surface (u8)
- 5: reserved (u8)
- 6-9: cycle_counter (u32)
- 10-13: timestamp_ms (u32)
- 14-15: command_norm_x10000 (i16)
- 16-17: rate_limit_norm_per_s_x1000 (u16)
- 18-21: crc32 over bytes 0-17 (u32)

## Enum maps

### lane_id

- 0: A
- 1: B
- 2: C

### mode

- 0: triplex
- 1: degraded
- 2: duplex
- 3: failsafe

### surface

- 0: elevator
- 1: aileron
- 2: rudder
- 3: flap
- 4: trim

## Health bitfield

- bit 0: bit_ok
- bit 1: sensor_ok
- bit 2: timing_ok
- bit 3: comm_ok

## Notes

- command_norm uses signed fixed-point scaling with factor 10000.
- rate_limit_norm_per_s uses unsigned fixed-point scaling with factor 1000.
- Frames with invalid length or CRC are discarded.
