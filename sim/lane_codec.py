"""Binary lane message codec for CAN-FD prototype exchange.

Wire format (22 bytes, little-endian):
- byte 0: protocol_version (u8)
- byte 1: lane_id enum (u8)
- byte 2: mode enum (u8)
- byte 3: health bitfield (u8)
- byte 4: surface enum (u8)
- byte 5: reserved (u8)
- byte 6-9: cycle_counter (u32)
- byte 10-13: timestamp_ms (u32)
- byte 14-15: command_norm scaled by 10000 (i16)
- byte 16-17: rate_limit_norm_per_s scaled by 1000 (u16)
- byte 18-21: crc32 of bytes[0:18] (u32)
"""

from dataclasses import dataclass
import struct
import zlib

FRAME_LEN = 22

LANE_TO_ID = {"A": 0, "B": 1, "C": 2}
ID_TO_LANE = {v: k for k, v in LANE_TO_ID.items()}

MODE_TO_ID = {"triplex": 0, "degraded": 1, "duplex": 2, "failsafe": 3}
ID_TO_MODE = {v: k for k, v in MODE_TO_ID.items()}

SURFACE_TO_ID = {"elevator": 0, "aileron": 1, "rudder": 2, "flap": 3, "trim": 4}
ID_TO_SURFACE = {v: k for k, v in SURFACE_TO_ID.items()}


@dataclass(frozen=True)
class LaneHealth:
    bit_ok: bool
    sensor_ok: bool
    timing_ok: bool
    comm_ok: bool


@dataclass(frozen=True)
class LaneMessage:
    protocol_version: int
    lane_id: str
    mode: str
    health: LaneHealth
    surface: str
    cycle_counter: int
    timestamp_ms: int
    command_norm: float
    rate_limit_norm_per_s: float


def _encode_health(health: LaneHealth) -> int:
    value = 0
    value |= 1 if health.bit_ok else 0
    value |= 2 if health.sensor_ok else 0
    value |= 4 if health.timing_ok else 0
    value |= 8 if health.comm_ok else 0
    return value


def _decode_health(value: int) -> LaneHealth:
    return LaneHealth(
        bit_ok=bool(value & 1),
        sensor_ok=bool(value & 2),
        timing_ok=bool(value & 4),
        comm_ok=bool(value & 8),
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def encode_lane_message(msg: LaneMessage) -> bytes:
    """Encode LaneMessage to fixed-size binary frame."""

    lane = LANE_TO_ID[msg.lane_id]
    mode = MODE_TO_ID[msg.mode]
    surface = SURFACE_TO_ID[msg.surface]
    health_bits = _encode_health(msg.health)

    command_scaled = int(round(_clamp(msg.command_norm, -1.0, 1.0) * 10000.0))
    rate_scaled = int(round(_clamp(msg.rate_limit_norm_per_s, 0.0, 65.535) * 1000.0))

    header = struct.pack(
        "<6BIIhH",
        msg.protocol_version,
        lane,
        mode,
        health_bits,
        surface,
        0,
        msg.cycle_counter,
        msg.timestamp_ms,
        command_scaled,
        rate_scaled,
    )
    crc = zlib.crc32(header) & 0xFFFFFFFF
    return header + struct.pack("<I", crc)


def decode_lane_message(frame: bytes) -> LaneMessage:
    """Decode fixed-size binary frame into LaneMessage.

    Raises ValueError if size is invalid or CRC check fails.
    """

    if len(frame) != FRAME_LEN:
        raise ValueError("Invalid frame length")

    header = frame[:18]
    crc_expected = struct.unpack("<I", frame[18:22])[0]
    crc_actual = zlib.crc32(header) & 0xFFFFFFFF
    if crc_actual != crc_expected:
        raise ValueError("CRC mismatch")

    unpacked = struct.unpack("<6BIIhH", header)
    protocol_version, lane_id, mode_id, health_bits, surface_id, _reserved, cycle_counter, timestamp_ms, command_scaled, rate_scaled = unpacked

    return LaneMessage(
        protocol_version=protocol_version,
        lane_id=ID_TO_LANE[lane_id],
        mode=ID_TO_MODE[mode_id],
        health=_decode_health(health_bits),
        surface=ID_TO_SURFACE[surface_id],
        cycle_counter=cycle_counter,
        timestamp_ms=timestamp_ms,
        command_norm=command_scaled / 10000.0,
        rate_limit_norm_per_s=rate_scaled / 1000.0,
    )
