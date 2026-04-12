# FCC Firmware Scaffold (v0.1)

This folder is a deterministic scheduler and protocol-stub starting point for triplex FCC lanes.

## Current contents

- include/fcc_scheduler.h: scheduler interface
- include/actuator_protocol.h: actuator frame pack/unpack interfaces
- src/fcc_scheduler.c: scheduler implementation
- src/actuator_protocol.c: actuator CRC and frame parsing helpers
- src/main.c: minimal demonstration harness
- src/test_actuator_protocol.c: C conformance test vectors for actuator protocol

## Design intent

- deterministic periodic execution model
- clear separation between scheduler, control law, and I/O/protocol layers
- straightforward path to MCU HAL integration

## Planned additions

- lane protocol encode/decode binding to transport drivers
- sensor acquisition and timing watchdog layer
- mode manager and built-in test hooks
