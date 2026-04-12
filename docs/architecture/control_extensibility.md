# Control Extensibility Architecture (v0.1)

This architecture sets a minimum 3-axis baseline and supports optional and future control axes.

## Baseline axes

Required core flight-control axes:

- pitch
- roll
- yaw

## Optional axes

Optional controls available when configured and physically present:

- flap
- spoiler

## Future extensibility

The provider architecture allows additional, unknown axes without schema breakage.

Examples:

- thrust command axis
- fadec_torque or power-management channels
- mission-specific high-lift or drag-device channels

## Provider model

Providers register with:

- provider name
- priority
- set of provided axes

At runtime, command resolution is deterministic:

- highest-priority provider wins per axis
- required axes default to neutral command when not provided
- unknown axes are passed through for future expansion

## Why this model

- Keeps first implementation simple and deterministic.
- Avoids hard-coding all future axis types now.
- Enables vendor integrations and experimental feature growth without rewriting core arbitration.
