# MAOS-FCS Hardware Target (v0.1 Draft)

This document defines practical hardware targets for early FBW prototype builds.

## FCC lane computer (x3)

Each lane should be independent in compute, power conditioning, watchdog behavior, and bus transceivers.

### Candidate MCU classes

- STM32H743/H753 class (high-performance Cortex-M7)
- NXP S32K3 class (automotive-oriented safety features)
- TI TMS570 class (lockstep-oriented safety lineage)

## Minimum lane capabilities

- CPU frequency: 200 MHz or higher
- Flash: 1 MB or higher
- RAM: 512 KB or higher
- Dual CAN-FD capability
- Hardware watchdog and brownout reset
- Timer resources for deterministic 200 to 500 Hz loop scheduling

## Cross-channel communication

- Dual redundant CAN-FD buses: CH-A and CH-B
- Physical bus separation and independent transceivers per lane
- Message CRC and cycle-counter checks at receiver

## Sensor architecture targets

- 3x IMU paths (at least one per lane)
- 2x independent air-data computer modules
- Dual-channel pilot input sensing on each control axis
- Dual-channel surface position feedback at each actuator

## Air data computer targets (x2)

- Independent pressure sensing chain per ADC module
- Dedicated MCU per ADC module
- Temperature compensation and calibration coefficients
- Broadcast air-data estimates to all FCC lanes

## Power architecture targets

- Independent regulated feed per FCC lane
- Separate sensor and actuator rail monitoring
- Lane-level power telemetry into health reporting

## Prototype progression

1. Bench prototype with development boards and simulated sensors
2. Integrated prototype with custom FCC PCB and redundant buses
3. Environmental and fault-injection testing before any flight-like campaign

## Not in scope for v0.1

- Formal certification evidence package
- Production airworthiness claims
- Final aircraft installation design approval
