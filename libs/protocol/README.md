# Protocol Overview

This folder defines cross-channel and actuator-facing message contracts.

## v0.1 artifacts

- lane_message_schema.json: Canonical schema for FCC lane health + command exchange.
- canfd_wire_format.md: Fixed-size binary CAN-FD payload layout for lane exchange.
- actuator_canfd_wire_format.md: Generic actuator command and feedback frame format.

## Design intent

- Deterministic field set and bounded value ranges.
- Explicit lane identity and cycle timing metadata.
- Structured health flags to support voting and fault isolation.
- Integrity field (CRC) to support transport-level corruption checks.

## Next additions

- Message compatibility/versioning strategy.
- Vendor profile mappings for actuator adapters.
