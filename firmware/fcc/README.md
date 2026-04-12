# FCC Firmware Scaffold (v0.1)

This folder is a deterministic scheduler and protocol-stub starting point for triplex FCC lanes.

## Current contents

- include/fcc_scheduler.h: scheduler interface
- src/fcc_scheduler.c: scheduler implementation
- src/main.c: minimal demonstration harness

## Design intent

- deterministic periodic execution model
- clear separation between scheduler, control law, and I/O/protocol layers
- straightforward path to MCU HAL integration

## Planned additions

- lane protocol encode/decode binding to transport drivers
- sensor acquisition and timing watchdog layer
- mode manager and built-in test hooks
