"""Generic smart-actuator command/feedback codec for CAN-FD payloads."""

from dataclasses import dataclass
import struct
import zlib

CMD_LEN = 18
FB_LEN = 22

MODE_TO_ID = {"position": 0, "rate": 1, "effort": 2, "standby": 3}
ID_TO_MODE = {v: k for k, v in MODE_TO_ID.items()}


@dataclass(frozen=True)
class EnableFlags:
    channel_enable: bool
    local_limit_enable: bool


@dataclass(frozen=True)
class FaultFlags:
    overcurrent: bool
    overtemperature: bool
    position_mismatch: bool
    comm_timeout: bool


@dataclass(frozen=True)
class ActuatorCommand:
    protocol_version: int
    actuator_id: int
    control_mode: str
    enable: EnableFlags
    sequence: int
    target_position_norm: float
    target_rate_norm_per_s: float
    max_effort_norm: float


@dataclass(frozen=True)
class ActuatorFeedback:
    protocol_version: int
    actuator_id: int
    feedback_mode: str
    faults: FaultFlags
    sequence_echo: int
    measured_position_norm: float
    measured_rate_norm_per_s: float
    motor_current_a: float
    temperature_c: float
    supply_voltage_v: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pack_enable(flags: EnableFlags) -> int:
    v = 0
    v |= 1 if flags.channel_enable else 0
    v |= 2 if flags.local_limit_enable else 0
    return v


def _unpack_enable(v: int) -> EnableFlags:
    return EnableFlags(channel_enable=bool(v & 1), local_limit_enable=bool(v & 2))


def _pack_faults(flags: FaultFlags) -> int:
    v = 0
    v |= 1 if flags.overcurrent else 0
    v |= 2 if flags.overtemperature else 0
    v |= 4 if flags.position_mismatch else 0
    v |= 8 if flags.comm_timeout else 0
    return v


def _unpack_faults(v: int) -> FaultFlags:
    return FaultFlags(
        overcurrent=bool(v & 1),
        overtemperature=bool(v & 2),
        position_mismatch=bool(v & 4),
        comm_timeout=bool(v & 8),
    )


def encode_actuator_command(cmd: ActuatorCommand) -> bytes:
    mode = MODE_TO_ID[cmd.control_mode]
    enable = _pack_enable(cmd.enable)
    pos = int(round(_clamp(cmd.target_position_norm, -1.0, 1.0) * 10000.0))
    rate = int(round(_clamp(cmd.target_rate_norm_per_s, 0.0, 65.535) * 1000.0))
    effort = int(round(_clamp(cmd.max_effort_norm, 0.0, 1.0) * 1000.0))

    header = struct.pack(
        "<4BIhHH",
        cmd.protocol_version,
        cmd.actuator_id,
        mode,
        enable,
        cmd.sequence,
        pos,
        rate,
        effort,
    )
    crc = zlib.crc32(header) & 0xFFFFFFFF
    return header + struct.pack("<I", crc)


def decode_actuator_command(frame: bytes) -> ActuatorCommand:
    if len(frame) != CMD_LEN:
        raise ValueError("Invalid command frame length")

    header = frame[:14]
    crc_expected = struct.unpack("<I", frame[14:18])[0]
    if (zlib.crc32(header) & 0xFFFFFFFF) != crc_expected:
        raise ValueError("Command CRC mismatch")

    pv, actuator_id, mode_id, enable_v, sequence, pos, rate, effort = struct.unpack("<4BIhHH", header)
    return ActuatorCommand(
        protocol_version=pv,
        actuator_id=actuator_id,
        control_mode=ID_TO_MODE[mode_id],
        enable=_unpack_enable(enable_v),
        sequence=sequence,
        target_position_norm=pos / 10000.0,
        target_rate_norm_per_s=rate / 1000.0,
        max_effort_norm=effort / 1000.0,
    )


def encode_actuator_feedback(fb: ActuatorFeedback) -> bytes:
    mode = MODE_TO_ID[fb.feedback_mode]
    faults = _pack_faults(fb.faults)
    pos = int(round(_clamp(fb.measured_position_norm, -1.0, 1.0) * 10000.0))
    rate = int(round(_clamp(fb.measured_rate_norm_per_s, -32.768, 32.767) * 1000.0))
    current = int(round(_clamp(fb.motor_current_a, 0.0, 655.35) * 100.0))
    temp = int(round(_clamp(fb.temperature_c, -3276.8, 3276.7) * 10.0))
    volt = int(round(_clamp(fb.supply_voltage_v, 0.0, 655.35) * 100.0))

    header = struct.pack(
        "<4BIhhHhH",
        fb.protocol_version,
        fb.actuator_id,
        mode,
        faults,
        fb.sequence_echo,
        pos,
        rate,
        current,
        temp,
        volt,
    )
    crc = zlib.crc32(header) & 0xFFFFFFFF
    return header + struct.pack("<I", crc)


def decode_actuator_feedback(frame: bytes) -> ActuatorFeedback:
    if len(frame) != FB_LEN:
        raise ValueError("Invalid feedback frame length")

    header = frame[:18]
    crc_expected = struct.unpack("<I", frame[18:22])[0]
    if (zlib.crc32(header) & 0xFFFFFFFF) != crc_expected:
        raise ValueError("Feedback CRC mismatch")

    pv, actuator_id, mode_id, faults_v, sequence_echo, pos, rate, current, temp, volt = struct.unpack("<4BIhhHhH", header)
    return ActuatorFeedback(
        protocol_version=pv,
        actuator_id=actuator_id,
        feedback_mode=ID_TO_MODE[mode_id],
        faults=_unpack_faults(faults_v),
        sequence_echo=sequence_echo,
        measured_position_norm=pos / 10000.0,
        measured_rate_norm_per_s=rate / 1000.0,
        motor_current_a=current / 100.0,
        temperature_c=temp / 10.0,
        supply_voltage_v=volt / 100.0,
    )
