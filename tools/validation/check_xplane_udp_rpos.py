#!/usr/bin/env python3
"""Validate X-Plane legacy UDP using documented RPOS handshake.

Per Laminar's "Exchanging Data with X-Plane":
- Send to X-Plane receive port 49000
- Message prologue is 4-char label + NUL byte
- RPOS request payload is a NUL-terminated string with desired rate
  Example: b"RPOS\x00" + b"60\x00"
- X-Plane replies to the source IP/port of the sender

This script binds an ephemeral UDP port, sends RPOS request, and waits for reply.
"""

from __future__ import annotations

import socket
import struct
import sys
import time


def _parse_rpos(packet: bytes) -> dict[str, float] | None:
    # RPOS header is 5 bytes: b"RPOS" + one internal byte.
    if len(packet) < 5 or packet[:4] != b"RPOS":
        return None

    # After 5-byte header, fields are tightly packed:
    # double lon, double lat, double ele,
    # float agl, float pitch, float heading, float roll,
    # float vx, float vy, float vz,
    # float P, float Q, float R
    fmt = "<dddffffffffff"
    size = struct.calcsize(fmt)
    if len(packet) < 5 + size:
        return None

    vals = struct.unpack_from(fmt, packet, 5)
    return {
        "lon_deg": vals[0],
        "lat_deg": vals[1],
        "elev_m": vals[2],
        "agl_m": vals[3],
        "pitch_deg": vals[4],
        "heading_deg": vals[5],
        "roll_deg": vals[6],
        "vx_east_mps": vals[7],
        "vy_up_mps": vals[8],
        "vz_south_mps": vals[9],
        "p_radps": vals[10],
        "q_radps": vals[11],
        "r_radps": vals[12],
    }


def main() -> int:
    host = "127.0.0.1"
    xplane_port = 49000
    request_rate_hz = 20

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    sock.settimeout(2.0)

    local_ip, local_port = sock.getsockname()
    print(f"[udp-rpos] local listener: {local_ip}:{local_port}")

    # Correct request per doc: 4-char message + NUL, then NUL-terminated rate string.
    payload = b"RPOS\x00" + f"{request_rate_hz}".encode("ascii") + b"\x00"
    sock.sendto(payload, (host, xplane_port))
    print(f"[udp-rpos] sent RPOS request to {host}:{xplane_port} at {request_rate_hz} Hz")

    received = 0
    deadline = time.time() + 5.0

    while time.time() < deadline:
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue

        parsed = _parse_rpos(data)
        if parsed is None:
            continue

        received += 1
        print(
            "[udp-rpos] sample",
            received,
            f"from={addr[0]}:{addr[1]}",
            f"ias_proxy_v={parsed['vx_east_mps']:.2f} m/s",
            f"pitch={parsed['pitch_deg']:.2f} deg",
            f"roll={parsed['roll_deg']:.2f} deg",
            f"agl={parsed['agl_m']:.1f} m",
        )
        if received >= 3:
            break

    sock.close()

    if received == 0:
        print("[udp-rpos] no RPOS replies received")
        print("[udp-rpos] check X-Plane running, not paused, and network data enabled")
        print("[udp-rpos] if still failing, use Web API path (port 8086), which is already working")
        return 1

    print(f"[udp-rpos] success: received {received} RPOS packets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
