#!/usr/bin/env python3
"""Emergency X-Plane recovery helper for wings-level shallow climb.

This utility is intended for manual intervention when the aircraft repeatedly
re-enters an upset state after unpausing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import run_sil_campaign_webapi as api


def _set_best_effort(host: str, port: int, name: str, value: float) -> None:
    try:
        api._set_dataref_value(host, port, name, value)
        print(f"[recover] set {name}={value}")
    except Exception as exc:
        print(f"[recover] skip {name}: {exc}")


def _active_hold_loop(
    host: str,
    port: int,
    *,
    duration_s: float,
    rate_hz: float,
    target_pitch_deg: float,
    throttle_ratio: float,
) -> None:
    """Continuously command stick/trim to keep wings level and shallow climb."""
    dt = 1.0 / max(1.0, rate_hz)
    steps = max(1, int(duration_s * rate_hz))

    for i in range(steps):
        phi = api._get_dataref_value(host, port, "sim/flightmodel/position/phi")
        theta = api._get_dataref_value(host, port, "sim/flightmodel/position/theta")
        ias = api._get_dataref_value(host, port, "sim/cockpit2/gauges/indicators/airspeed_kts_pilot")
        if phi is None or theta is None or ias is None:
            print("[recover] telemetry unavailable; ending active hold")
            break

        roll_error = -phi
        pitch_error = target_pitch_deg - theta

        # Conservative P-controller tuned for emergency recovery, not precision AP.
        roll_cmd = max(-0.45, min(0.45, 0.020 * roll_error))
        pitch_cmd = max(-0.35, min(0.35, 0.030 * pitch_error))

        _set_best_effort(host, port, "sim/cockpit2/controls/yoke_roll_ratio", roll_cmd)
        _set_best_effort(host, port, "sim/cockpit2/controls/yoke_pitch_ratio", pitch_cmd)
        _set_best_effort(host, port, "sim/cockpit2/controls/yoke_heading_ratio", 0.0)

        # Keep trims near neutral while the active loop handles attitude.
        _set_best_effort(host, port, "sim/cockpit2/controls/aileron_trim", 0.0)
        _set_best_effort(host, port, "sim/cockpit2/controls/elevator_trim", 0.0)
        _set_best_effort(host, port, "sim/cockpit2/controls/rudder_trim", 0.0)

        try:
            api._set_first_available_dataref_value(
                host,
                port,
                [
                    "sim/cockpit2/engine/actuators/throttle_ratio_all",
                    "sim/cockpit2/engine/actuators/throttle_ratio[0]",
                    "sim/cockpit2/engine/actuators/throttle_ratio",
                ],
                throttle_ratio,
            )
        except Exception:
            pass

        if (i % max(1, int(rate_hz))) == 0:
            print(
                f"[recover] hold t={i*dt:4.1f}s phi={phi:+6.2f} theta={theta:+6.2f} "
                f"IAS={ias:6.1f} cmd_roll={roll_cmd:+.3f} cmd_pitch={pitch_cmd:+.3f}"
            )

        time.sleep(dt)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover aircraft to stable shallow climb")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8086)
    parser.add_argument("--target-alt-ft", type=float, default=3500.0)
    parser.add_argument("--duration-s", type=float, default=25.0)
    parser.add_argument("--rate-hz", type=float, default=15.0)
    parser.add_argument("--throttle", type=float, default=0.68)
    parser.add_argument("--mixture", type=float, default=1.0)
    parser.add_argument("--target-pitch-deg", type=float, default=2.0)
    args = parser.parse_args()

    host = args.host
    port = args.port

    api.check_web_api(host, port)
    api.force_pause(host, port)

    # Prevent hardware joystick input from immediately overwriting commanded controls.
    for dr in (
        "sim/operation/override/override_joystick",
        "sim/operation/override/override_joystick_pitch",
        "sim/operation/override/override_joystick_roll",
        "sim/operation/override/override_joystick_heading",
        "sim/operation/override/override_joystick_yaw",
    ):
        _set_best_effort(host, port, dr, 1.0)

    for dr, value in (
        ("sim/flightmodel/position/phi", 0.0),
        ("sim/flightmodel/position/theta", 2.0),
        ("sim/flightmodel/position/P", 0.0),
        ("sim/flightmodel/position/Q", 0.0),
        ("sim/flightmodel/position/R", 0.0),
        ("sim/cockpit2/controls/yoke_roll_ratio", 0.0),
        ("sim/cockpit2/controls/yoke_pitch_ratio", 0.0),
        ("sim/cockpit2/controls/yoke_heading_ratio", 0.0),
        ("sim/cockpit2/controls/aileron_trim", 0.0),
        ("sim/cockpit2/controls/elevator_trim", 0.0),
        ("sim/cockpit2/controls/rudder_trim", 0.0),
        ("sim/flightmodel/controls/ail_trim", 0.0),
        ("sim/flightmodel/controls/elv_trim", 0.0),
        ("sim/flightmodel/controls/rud_trim", 0.0),
    ):
        _set_best_effort(host, port, dr, value)

    try:
        used = api._set_first_available_dataref_value(
            host,
            port,
            [
                "sim/cockpit2/engine/actuators/throttle_ratio_all",
                "sim/cockpit2/engine/actuators/throttle_ratio[0]",
                "sim/cockpit2/engine/actuators/throttle_ratio",
            ],
            max(0.0, min(1.0, float(args.throttle))),
        )
        print(f"[recover] set throttle via {used}")
    except Exception as exc:
        print(f"[recover] skip throttle: {exc}")

    try:
        used = api._set_first_available_dataref_value(
            host,
            port,
            [
                "sim/cockpit2/engine/actuators/mixture_ratio_all",
                "sim/cockpit2/engine/actuators/mixture_ratio[0]",
                "sim/cockpit2/engine/actuators/mixture_ratio",
            ],
            max(0.0, min(1.0, float(args.mixture))),
        )
        print(f"[recover] set mixture via {used}")
    except Exception as exc:
        print(f"[recover] skip mixture: {exc}")

    api.force_unpause(host, port)
    _active_hold_loop(
        host,
        port,
        duration_s=args.duration_s,
        rate_hz=args.rate_hz,
        target_pitch_deg=args.target_pitch_deg,
        throttle_ratio=max(0.0, min(1.0, float(args.throttle))),
    )

    # Hand off to the gentler trim-based stabilizer once immediate upset is damped.
    api.stabilize_and_climb(
        host,
        port,
        target_altitude_ft=args.target_alt_ft,
        duration_s=min(12.0, max(4.0, args.duration_s * 0.4)),
        rate_hz=max(8.0, args.rate_hz),
    )

    phi = api._get_dataref_value(host, port, "sim/flightmodel/position/phi")
    theta = api._get_dataref_value(host, port, "sim/flightmodel/position/theta")
    ias = api._get_dataref_value(host, port, "sim/cockpit2/gauges/indicators/airspeed_kts_pilot")
    print(f"[recover] final phi={phi:+.2f} theta={theta:+.2f} IAS={ias:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
