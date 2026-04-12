# Actuator Codec Conformance (v0.1)

This note records cross-language conformance between Python simulation codec and C firmware stubs.

## Reference vectors

Generated from sim/actuator_codec.py with:

- command: protocol=1, actuator=3, mode=position, sequence=77, position=0.25, rate=1.5, effort=0.8
- feedback: protocol=1, actuator=3, mode=position, sequence_echo=77, position=0.24, rate=1.4, current=2.5 A, temp=45.2 C, voltage=27.9 V

Hex frames:

- command: 010300034d000000c409dc0520036f9175e2
- feedback: 010300004d00000060097805fa00c401e60a46264cd9

## C coverage

The firmware test executable validates:

- command unpack and field values
- feedback unpack and field values
- CRC rejection for corrupted command frame

## Why this matters

This keeps simulation and firmware binary framing aligned while the project is still in rapid architecture evolution.
