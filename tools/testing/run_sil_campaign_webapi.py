#!/usr/bin/env python3
"""Run unattended SIL test campaigns against X-Plane Web API.

This script is designed for high-volume autonomous test execution.
It can:
- Verify X-Plane Web API connectivity
- Force sim unpause through dataref write
- Run multiple SIL scenarios in sequence
- Repeat campaigns N times
- Write per-run JSONL logs to a timestamped directory

Usage examples:
    python tools/testing/run_sil_campaign_webapi.py
    python tools/testing/run_sil_campaign_webapi.py --repeats 20 --host 127.0.0.1
    python tools/testing/run_sil_campaign_webapi.py --include-gust --repeats 5
    python tools/testing/run_sil_campaign_webapi.py --manifest tests/robot/manifests/smoke_manifest.json

Manifest options:
    startup_flight           JSON object used as payload for POST /api/v3/flight
    reset_each_run           If true, re-initialize flight before every scenario
    reset_wait_s             Seconds to wait after reset before scenario starts
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


DEFAULT_SCENARIOS: List[Dict[str, Any]] = [
    {"name": "runway_idle_baseline", "cycles": 200, "hz": 20, "gust": False},
    {"name": "runway_idle_highrate", "cycles": 500, "hz": 50, "gust": False},
    {"name": "runway_idle_longrun", "cycles": 1200, "hz": 20, "gust": False},
]

SMOKE_SCENARIOS: List[Dict[str, Any]] = [
    {"name": "smoke_baseline", "cycles": 80, "hz": 20, "gust": False},
    {"name": "smoke_highrate", "cycles": 100, "hz": 40, "gust": False},
]


def _validate_manifest_scenarios(scenarios: List[Dict[str, Any]]) -> None:
    if not scenarios:
        raise ValueError("Manifest must define at least one scenario")
    for i, scenario in enumerate(scenarios, start=1):
        missing = [k for k in ("name", "cycles", "hz") if k not in scenario]
        if missing:
            raise ValueError(f"Manifest scenario #{i} missing required keys: {missing}")


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a JSON object")
    if "scenarios" not in data:
        raise ValueError("Manifest must contain 'scenarios' list")
    scenarios = data["scenarios"]
    if not isinstance(scenarios, list):
        raise ValueError("Manifest 'scenarios' must be a list")
    _validate_manifest_scenarios(scenarios)
    return data


def _api_base(host: str, port: int) -> str:
    return f"http://{host}:{port}/api/v3"


def _api_base_v2(host: str, port: int) -> str:
    return f"http://{host}:{port}/api/v2"


def check_web_api(host: str, port: int, timeout_s: float = 3.0) -> None:
    url = f"http://{host}:{port}/api/capabilities"
    resp = requests.get(url, timeout=timeout_s)
    resp.raise_for_status()
    body = resp.json()
    version = body.get("x-plane", {}).get("version", "unknown")
    versions = body.get("api", {}).get("versions", [])
    print(f"[campaign] X-Plane {version} reachable, API versions: {versions}")


def _get_dataref_id(host: str, port: int, dataref_name: str) -> int | None:
    url = f"{_api_base(host, port)}/datarefs"
    resp = requests.get(url, timeout=5.0)
    resp.raise_for_status()
    for dr in resp.json().get("data", []):
        if dr.get("name") == dataref_name:
            return int(dr["id"])
    return None


def _get_dataref_value(host: str, port: int, dataref_name: str) -> float | None:
    dr_id = _get_dataref_id(host, port, dataref_name)
    if dr_id is None:
        return None
    url = f"{_api_base(host, port)}/datarefs/{dr_id}/value"
    resp = requests.get(url, timeout=3.0)
    resp.raise_for_status()
    data = resp.json().get("data")
    try:
        return float(data)
    except (TypeError, ValueError):
        return None


def _is_paused(host: str, port: int) -> bool | None:
    paused = _get_dataref_value(host, port, "sim/time/paused")
    if paused is None:
        return None
    return paused >= 0.5


def _get_command_id(host: str, port: int, command_name: str) -> int | None:
    url = f"{_api_base_v2(host, port)}/commands?filter[name]={command_name}"
    resp = requests.get(url, timeout=5.0)
    resp.raise_for_status()
    items = resp.json().get("data", [])
    if not items:
        return None
    return int(items[0]["id"])


def _activate_command(host: str, port: int, command_id: int, duration: float = 0.0) -> None:
    url = f"{_api_base_v2(host, port)}/command/{command_id}/activate"
    resp = requests.post(url, json={"duration": duration}, timeout=3.0)
    resp.raise_for_status()


def _start_flight(
    host: str,
    port: int,
    startup_flight: Dict[str, Any],
    *,
    timeout_s: float = 90.0,
) -> None:
    """Start/reset flight using X-Plane v3 Flight API."""
    url = f"{_api_base(host, port)}/flight"
    if "data" in startup_flight and isinstance(startup_flight["data"], dict):
        payload = startup_flight
    else:
        payload = {"data": startup_flight}
    resp = requests.post(url, json=payload, timeout=timeout_s)
    resp.raise_for_status()


def _teleport_airborne(
    host: str,
    port: int,
    *,
    altitude_agl_ft: float = 3000.0,
    airspeed_kias: float = 100.0,
    wait_s: float = 3.0,
) -> None:
    """After a ground reset, teleport aircraft to altitude with forward velocity.

    Reads current OpenGL local position and true heading from X-Plane, then
    writes local_y (altitude), local_vx/vy/vz (velocity) so the FCS loop
    receives real airspeed rather than IAS=0 on the ground.

    Note: airborne starts can take a few simulation frames to stabilise fully.
    The caller should insert a short settle delay before starting the SIL loop.
    """
    import math

    alt_m = altitude_agl_ft * 0.3048
    speed_ms = airspeed_kias * 0.514444  # KIAS → m/s (approximate at low altitude)

    # Read current local position and heading.
    local_y = _get_dataref_value(host, port, "sim/flightmodel/position/local_y")
    psi = _get_dataref_value(host, port, "sim/flightmodel/position/psi")  # true heading, degrees
    if local_y is None or psi is None:
        raise RuntimeError("Could not read position datarefs for airborne teleport")

    heading_rad = math.radians(psi)
    # X-Plane OpenGL local frame: +X=East, +Y=Up, -Z=North
    vx = speed_ms * math.sin(heading_rad)
    vy = 0.0
    vz = -speed_ms * math.cos(heading_rad)

    new_y = local_y + alt_m

    _set_dataref_value(host, port, "sim/flightmodel/position/local_y", new_y)
    _set_dataref_value(host, port, "sim/flightmodel/position/local_vx", vx)
    _set_dataref_value(host, port, "sim/flightmodel/position/local_vy", vy)
    _set_dataref_value(host, port, "sim/flightmodel/position/local_vz", vz)
    # Level wings and set a gentle nose-up attitude.
    _set_dataref_value(host, port, "sim/flightmodel/position/phi", 0.0)
    _set_dataref_value(host, port, "sim/flightmodel/position/theta", 3.0)

    print(
        f"[campaign] airborne teleport: alt_agl={altitude_agl_ft:.0f}ft "
        f"heading={psi:.1f}° speed={airspeed_kias:.0f}KIAS "
        f"vx={vx:.1f} vy={vy:.1f} vz={vz:.1f} m/s"
    )

    if wait_s > 0:
        time.sleep(wait_s)


def force_unpause(host: str, port: int) -> None:
    # Try deterministic dataref write first, then command fallback if write is blocked.
    dr_name = "sim/time/paused"
    dr_id = _get_dataref_id(host, port, dr_name)
    if dr_id is None:
        raise RuntimeError(f"Could not resolve dataref: {dr_name}")

    url = f"{_api_base(host, port)}/datarefs/{dr_id}/value"
    errors: List[str] = []

    try:
        resp = requests.patch(url, json={"data": 0}, timeout=3.0)
        resp.raise_for_status()
        time.sleep(0.1)
        paused_after = _is_paused(host, port)
        if paused_after is False:
            print("[campaign] sim unpause via dataref write (sim/time/paused=0)")
            return
        errors.append("dataref write did not clear paused state")
    except Exception as exc:
        errors.append(f"dataref write failed: {exc}")

    # Fallback to command API.
    for cmd_name in ("sim/operation/pause_off", "sim/operation/pause_toggle"):
        try:
            cmd_id = _get_command_id(host, port, cmd_name)
            if cmd_id is None:
                errors.append(f"command not found: {cmd_name}")
                continue
            _activate_command(host, port, cmd_id, duration=0.0)
            time.sleep(0.15)
            paused_after = _is_paused(host, port)
            if paused_after is False:
                print(f"[campaign] sim unpause via command: {cmd_name}")
                return
            errors.append(f"command executed but sim still paused: {cmd_name}")
        except Exception as exc:
            errors.append(f"command failed ({cmd_name}): {exc}")

    raise RuntimeError("; ".join(errors))


def force_pause(host: str, port: int) -> None:
    # Try deterministic dataref write first, then command fallback.
    dr_name = "sim/time/paused"
    dr_id = _get_dataref_id(host, port, dr_name)
    if dr_id is None:
        raise RuntimeError(f"Could not resolve dataref: {dr_name}")

    url = f"{_api_base(host, port)}/datarefs/{dr_id}/value"
    errors: List[str] = []

    try:
        resp = requests.patch(url, json={"data": 1}, timeout=3.0)
        resp.raise_for_status()
        time.sleep(0.1)
        paused_after = _is_paused(host, port)
        if paused_after is True:
            print("[campaign] sim paused via dataref write (sim/time/paused=1)")
            return
        errors.append("dataref write did not set paused state")
    except Exception as exc:
        errors.append(f"dataref write failed: {exc}")

    for cmd_name in ("sim/operation/pause_on", "sim/operation/pause_toggle"):
        try:
            cmd_id = _get_command_id(host, port, cmd_name)
            if cmd_id is None:
                errors.append(f"command not found: {cmd_name}")
                continue
            _activate_command(host, port, cmd_id, duration=0.0)
            time.sleep(0.15)
            paused_after = _is_paused(host, port)
            if paused_after is True:
                print(f"[campaign] sim paused via command: {cmd_name}")
                return
            errors.append(f"command executed but sim not paused: {cmd_name}")
        except Exception as exc:
            errors.append(f"command failed ({cmd_name}): {exc}")

    raise RuntimeError("; ".join(errors))


def _set_dataref_value(host: str, port: int, dataref_name: str, value: float) -> None:
    dr_id = _get_dataref_id(host, port, dataref_name)
    if dr_id is None:
        raise RuntimeError(f"Could not resolve dataref: {dataref_name}")
    url = f"{_api_base(host, port)}/datarefs/{dr_id}/value"
    resp = requests.patch(url, json={"data": float(value)}, timeout=3.0)
    resp.raise_for_status()


def _get_first_available_dataref_value(
    host: str,
    port: int,
    dataref_names: List[str],
) -> float | None:
    for name in dataref_names:
        value = _get_dataref_value(host, port, name)
        if value is not None:
            return value
    return None


def _set_first_available_dataref_value(
    host: str,
    port: int,
    dataref_names: List[str],
    value: float,
) -> str:
    last_error: str | None = None
    for name in dataref_names:
        try:
            _set_dataref_value(host, port, name, value)
            return name
        except Exception as exc:
            last_error = str(exc)
            continue
    if last_error is None:
        last_error = "no candidate datarefs provided"
    raise RuntimeError(last_error)


def _apply_post_reset_propulsion_state(
    host: str,
    port: int,
    *,
    throttle_ratio: float,
    mixture_ratio: float | None = None,
    hold_s: float = 0.0,
) -> None:
    """Apply best-effort throttle/mixture state after reset and teleport."""

    throttle = max(0.0, min(1.0, float(throttle_ratio)))
    throttle_targets = [
        "sim/cockpit2/engine/actuators/throttle_ratio_all",
        "sim/cockpit2/engine/actuators/throttle_ratio[0]",
        "sim/cockpit2/engine/actuators/throttle_ratio",
    ]
    used_throttle = _set_first_available_dataref_value(host, port, throttle_targets, throttle)

    mixture_targets = [
        "sim/cockpit2/engine/actuators/mixture_ratio_all",
        "sim/cockpit2/engine/actuators/mixture_ratio[0]",
        "sim/cockpit2/engine/actuators/mixture_ratio",
    ]
    used_mixture = ""
    if mixture_ratio is not None:
        mixture = max(0.0, min(1.0, float(mixture_ratio)))
        used_mixture = _set_first_available_dataref_value(host, port, mixture_targets, mixture)

    if hold_s > 0:
        end_t = time.monotonic() + hold_s
        while time.monotonic() < end_t:
            try:
                _set_first_available_dataref_value(host, port, throttle_targets, throttle)
                if mixture_ratio is not None:
                    _set_first_available_dataref_value(host, port, mixture_targets, mixture)
            except Exception:
                break
            time.sleep(0.25)

    rpm_readbacks = [
        "sim/cockpit2/engine/indicators/engine_speed_rpm[0]",
        "sim/cockpit2/engine/indicators/engine_speed_rpm",
        "sim/flightmodel/engine/ENGN_N2_[0]",
    ]
    observed_rpm = _get_first_available_dataref_value(host, port, rpm_readbacks)
    if observed_rpm is None:
        print(
            "[campaign] propulsion init: "
            f"throttle={throttle:.2f} via {used_throttle}"
            + ("" if not used_mixture else f" mixture via {used_mixture}")
        )
    else:
        print(
            "[campaign] propulsion init: "
            f"throttle={throttle:.2f} via {used_throttle} rpm={observed_rpm:.0f}"
            + ("" if not used_mixture else f" mixture via {used_mixture}")
        )


def _active_recovery_hold(
    host: str,
    port: int,
    *,
    duration_s: float,
    rate_hz: float,
    target_pitch_deg: float,
    throttle_ratio: float,
    mixture_ratio: float | None,
    override_controls: bool,
) -> None:
    """Actively hold wings-level and shallow climb after unpause.

    This dampens upset recurrence when one-shot paused-state writes do not persist
    once physics resumes.
    """

    dt = 1.0 / max(1.0, rate_hz)
    steps = max(1, int(duration_s * rate_hz))

    if override_controls:
        for dr in (
            "sim/operation/override/override_joystick",
            "sim/operation/override/override_joystick_pitch",
            "sim/operation/override/override_joystick_roll",
            "sim/operation/override/override_joystick_heading",
        ):
            try:
                _set_dataref_value(host, port, dr, 1.0)
            except Exception:
                continue

    for i in range(steps):
        phi = _get_dataref_value(host, port, "sim/flightmodel/position/phi")
        theta = _get_dataref_value(host, port, "sim/flightmodel/position/theta")
        ias = _get_dataref_value(host, port, "sim/cockpit2/gauges/indicators/airspeed_kts_pilot")
        if phi is None or theta is None or ias is None:
            print("[campaign] preflight recovery: telemetry unavailable; stopping active hold")
            break

        roll_error = -phi
        pitch_error = target_pitch_deg - theta

        roll_cmd = max(-0.45, min(0.45, 0.020 * roll_error))
        pitch_cmd = max(-0.35, min(0.35, 0.030 * pitch_error))

        try:
            _set_dataref_value(host, port, "sim/cockpit2/controls/yoke_roll_ratio", roll_cmd)
            _set_dataref_value(host, port, "sim/cockpit2/controls/yoke_pitch_ratio", pitch_cmd)
            _set_dataref_value(host, port, "sim/cockpit2/controls/yoke_heading_ratio", 0.0)
            _set_dataref_value(host, port, "sim/cockpit2/controls/aileron_trim", 0.0)
            _set_dataref_value(host, port, "sim/cockpit2/controls/elevator_trim", 0.0)
            _set_dataref_value(host, port, "sim/cockpit2/controls/rudder_trim", 0.0)
        except Exception:
            pass

        throttle_targets = [
            "sim/cockpit2/engine/actuators/throttle_ratio_all",
            "sim/cockpit2/engine/actuators/throttle_ratio[0]",
            "sim/cockpit2/engine/actuators/throttle_ratio",
        ]
        try:
            _set_first_available_dataref_value(host, port, throttle_targets, throttle_ratio)
        except Exception:
            pass

        if mixture_ratio is not None:
            mixture_targets = [
                "sim/cockpit2/engine/actuators/mixture_ratio_all",
                "sim/cockpit2/engine/actuators/mixture_ratio[0]",
                "sim/cockpit2/engine/actuators/mixture_ratio",
            ]
            try:
                _set_first_available_dataref_value(host, port, mixture_targets, mixture_ratio)
            except Exception:
                pass

        if (i % max(1, int(rate_hz))) == 0:
            print(
                f"[campaign] preflight recovery t={i*dt:4.1f}s "
                f"phi={phi:+6.2f} theta={theta:+6.2f} IAS={ias:6.1f} "
                f"cmd_roll={roll_cmd:+.3f} cmd_pitch={pitch_cmd:+.3f}"
            )

        time.sleep(dt)

    print("[campaign] preflight recovery: active hold complete")


def _inject_scenario_position(
    host: str,
    port: int,
    *,
    lat_deg: float,
    lon_deg: float,
    heading_deg: float = 90.0,
    airspeed_kias: float = 100.0,
    init_pitch_deg: float = 3.0,
    init_bank_deg: float = 0.0,
    init_elev_trim: float = 0.0,
    settle_s: float = 2.0,
) -> None:
    """Move the aircraft to a specific lat/lon with a clean, repeatable initial state.

    Pauses the sim before writing any datarefs so all state changes land
    atomically from the physics engine's perspective, then unpauses and waits
    for the flight model to settle.  This prevents the violent heading snap and
    airspeed collapse that occur when position/attitude are changed mid-flight.

    X-Plane's Web API does not allow writing latitude/longitude directly (403).
    Uses local_x/local_z delta relative to the current position instead.

    State written while paused:
      local_x, local_z         — lateral position (meters delta from current)
      psi                      — heading (degrees true)
      phi                      — bank angle → 0°
      theta                    — pitch angle → init_pitch_deg
      local_vx, local_vy,      — velocity vector matching heading at airspeed_kias
      local_vz
      elv_trim                 — elevator trim → init_elev_trim (negative = nose down)
      ail_trim, rud_trim        — neutral (0)

    local frame: +x = East, +y = Up, +z = South (−z = North)
    """
    import math

    # Pause first so all writes reach X-Plane's physics engine atomically.
    force_pause(host, port)

    try:
        cur_lat = _get_dataref_value(host, port, "sim/flightmodel/position/latitude")
        cur_lon = _get_dataref_value(host, port, "sim/flightmodel/position/longitude")
        cur_x   = _get_dataref_value(host, port, "sim/flightmodel/position/local_x")
        cur_z   = _get_dataref_value(host, port, "sim/flightmodel/position/local_z")

        if any(v is None for v in (cur_lat, cur_lon, cur_x, cur_z)):
            raise RuntimeError("Could not read current position datarefs for injection")

        dlat = lat_deg - cur_lat
        dlon = lon_deg - cur_lon
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(cur_lat))

        new_x = cur_x + dlon * m_per_deg_lon
        new_z = cur_z - dlat * m_per_deg_lat  # +z = South, northward delta → negative z

        # Position
        _set_dataref_value(host, port, "sim/flightmodel/position/local_x", new_x)
        _set_dataref_value(host, port, "sim/flightmodel/position/local_z", new_z)

        # Attitude: heading, bank, pitch
        _set_dataref_value(host, port, "sim/flightmodel/position/psi",   heading_deg)
        _set_dataref_value(host, port, "sim/flightmodel/position/phi",   init_bank_deg)
        _set_dataref_value(host, port, "sim/flightmodel/position/theta", init_pitch_deg)

        # Velocity vector matching heading and target airspeed
        speed_ms    = airspeed_kias * 0.514444
        heading_rad = math.radians(heading_deg)
        _set_dataref_value(host, port, "sim/flightmodel/position/local_vx",  speed_ms * math.sin(heading_rad))
        _set_dataref_value(host, port, "sim/flightmodel/position/local_vy",  0.0)
        _set_dataref_value(host, port, "sim/flightmodel/position/local_vz", -speed_ms * math.cos(heading_rad))

        # Trim reset — neutral lateral/directional; elevator uses init_elev_trim
        for dref, val in (
            ("sim/flightmodel/controls/elv_trim", init_elev_trim),
            ("sim/flightmodel/controls/ail_trim", 0.0),
            ("sim/flightmodel/controls/rud_trim", 0.0),
        ):
            try:
                _set_dataref_value(host, port, dref, val)
            except Exception:
                pass

        dist_km = math.sqrt((dlat * 111.32) ** 2 + (dlon * m_per_deg_lon / 1000) ** 2)
        print(
            f"[campaign] position inject: target=({lat_deg:.5f},{lon_deg:.5f}) "
            f"hdg={heading_deg:.0f}° bank={init_bank_deg:.1f}° pitch={init_pitch_deg:.1f}° "
            f"IAS={airspeed_kias:.0f}kts dist={dist_km:.1f}km from ({cur_lat:.5f},{cur_lon:.5f})"
        )

    finally:
        # Always unpause even if a write failed — sim must not be left stuck paused.
        force_unpause(host, port)

    if settle_s > 0:
        time.sleep(settle_s)


def _engage_xplane_autopilot(host: str, port: int) -> None:
    """Engage X-Plane altitude hold + heading hold autopilot modes.

    Called after position injection so the aircraft holds level flight during
    long SIL runs.  The SIL loop tests FCS computation logic, not flight
    dynamics, so X-Plane's own autopilot keeping the aircraft stable is correct
    behaviour.  Failures are best-effort — a warning is printed but the run
    continues.
    """
    # Altitude hold — keeps aircraft from descending during long runs
    for cmd_name in ("sim/autopilot/altitude_hold", "sim/autopilot/fdir_servos_up_one"):
        try:
            cmd_id = _get_command_id(host, port, cmd_name)
            if cmd_id is not None:
                _activate_command(host, port, cmd_id)
                print(f"[campaign] autopilot: engaged {cmd_name}")
                break
        except Exception as exc:
            print(f"[campaign] autopilot: {cmd_name} failed: {exc}")

    # Heading hold — prevents drifting turns
    for cmd_name in ("sim/autopilot/heading", "sim/autopilot/wing_leveler"):
        try:
            cmd_id = _get_command_id(host, port, cmd_name)
            if cmd_id is not None:
                _activate_command(host, port, cmd_id)
                print(f"[campaign] autopilot: engaged {cmd_name}")
                break
        except Exception as exc:
            print(f"[campaign] autopilot: {cmd_name} failed: {exc}")

    # Brief settle so autopilot takes hold before SIL starts
    time.sleep(1.5)


def stabilize_and_climb(
    host: str,
    port: int,
    *,
    target_altitude_ft: float = 2000.0,
    duration_s: float = 20.0,
    rate_hz: float = 10.0,
) -> None:
    """Best-effort cleanup: level wings and pitch for climb toward target altitude.

    This is intentionally conservative and does not attempt full autopilot behavior.
    """

    dt = 1.0 / max(rate_hz, 1.0)
    target_alt_m = target_altitude_ft * 0.3048
    steps = max(1, int(duration_s * rate_hz))

    dref_alt_msl = "sim/flightmodel/position/elevation"
    dref_bank = "sim/flightmodel/position/phi"
    dref_pitch = "sim/flightmodel/position/theta"
    dref_pitch_trim = "sim/flightmodel/controls/elv_trim"
    dref_roll_trim = "sim/flightmodel/controls/ail_trim"

    print(f"[campaign] cleanup: stabilize+climb start target_alt_ft={target_altitude_ft:.0f}")

    for _ in range(steps):
        alt_m = _get_dataref_value(host, port, dref_alt_msl)
        bank_deg = _get_dataref_value(host, port, dref_bank)
        pitch_deg = _get_dataref_value(host, port, dref_pitch)

        if alt_m is None or bank_deg is None or pitch_deg is None:
            break

        # Mild climb command below target, gentle hold near/above target.
        target_pitch_deg = 6.0 if alt_m < (target_alt_m - 25.0) else 2.0
        pitch_error = target_pitch_deg - pitch_deg
        roll_error = -bank_deg

        pitch_cmd = max(-0.25, min(0.25, 0.018 * pitch_error))
        roll_cmd = max(-0.30, min(0.30, 0.025 * roll_error))

        _set_dataref_value(host, port, dref_pitch_trim, pitch_cmd)
        _set_dataref_value(host, port, dref_roll_trim, roll_cmd)

        # Exit early if leveled and close enough to target altitude.
        if abs(bank_deg) < 3.0 and alt_m >= (target_alt_m - 10.0):
            break

        time.sleep(dt)

    # Neutralize roll trim at end so plane doesn't keep banking between tests.
    try:
        _set_dataref_value(host, port, dref_roll_trim, 0.0)
    except Exception:
        pass

    print("[campaign] cleanup: stabilize+climb complete")


def evaluate_readiness(host: str, port: int) -> List[Dict[str, str]]:
    """Return readiness failures with reason codes for campaign classification."""
    failures: List[Dict[str, str]] = []
    try:
        check_web_api(host, port)
    except Exception as exc:
        failures.append(
            {
                "reason_code": "INFRA_FAIL_WEBAPI_UNREACHABLE",
                "message": str(exc),
            }
        )

    # Only treat unpause failures as readiness errors if sim is actually paused.
    try:
        paused = _is_paused(host, port)
    except Exception as exc:
        failures.append(
            {
                "reason_code": "INFRA_FAIL_PAUSE_STATE_UNAVAILABLE",
                "message": str(exc),
            }
        )
        paused = None

    if paused is True:
        try:
            force_unpause(host, port)
        except Exception as exc:
            failures.append(
                {
                    "reason_code": "INFRA_FAIL_UNPAUSE_BLOCKED",
                    "message": str(exc),
                }
            )

    return failures


def _extract_reason_counts(log_path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if not log_path.exists():
        return counts

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            reason = obj.get("reason_code")
            if isinstance(reason, str) and reason:
                counts[reason] = counts.get(reason, 0) + 1
    return counts


def _merge_reason_counts(total: Dict[str, int], add: Dict[str, int]) -> None:
    for reason, count in add.items():
        total[reason] = total.get(reason, 0) + int(count)


def _write_campaign_markdown(
    summary_md_path: Path,
    *,
    host: str,
    port: int,
    repeats: int,
    total_runs: int,
    failures: int,
    reason_counts: Dict[str, int],
    results: List[Dict[str, Any]],
) -> None:
    lines: List[str] = []
    lines.append("# Campaign Summary")
    lines.append("")
    lines.append(f"- Host: `{host}`")
    lines.append(f"- Port: `{port}`")
    lines.append(f"- Repeats: `{repeats}`")
    lines.append(f"- Total Runs: `{total_runs}`")
    lines.append(f"- Failures: `{failures}`")
    lines.append("")

    lines.append("## Reason Code Counts")
    lines.append("")
    lines.append("| Reason Code | Count |")
    lines.append("|---|---:|")
    if reason_counts:
        for reason in sorted(reason_counts):
            lines.append(f"| {reason} | {reason_counts[reason]} |")
    else:
        lines.append("| (none) | 0 |")
    lines.append("")

    lines.append("## Scenario Results")
    lines.append("")
    lines.append("| Repeat | Scenario ID | Status | Return Code | Artifact |")
    lines.append("|---:|---|---|---:|---|")
    for r in results:
        lines.append(
            "| "
            f"{r.get('repeat', '')} | "
            f"{r.get('scenario_id', r.get('scenario', ''))} | "
            f"{r.get('status', 'UNKNOWN')} | "
            f"{r.get('return_code', '')} | "
            f"`{r.get('log', '')}` |"
        )

    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_one_sil(repo_root: Path, host: str, scenario: Dict[str, Any], log_path: Path) -> int:
    sil_script = repo_root / "sim" / "examples" / "sil_xplane_webapi.py"

    cmd = [
        sys.executable,
        str(sil_script),
        "--host",
        host,
        "--cycles",
        str(int(scenario["cycles"])),
        "--hz",
        str(int(scenario["hz"])),
        "--log",
        str(log_path),
    ]
    if scenario.get("gust", False):
        cmd.append("--gust")
    extra = scenario.get("extra_sil_args", [])
    if extra:
        cmd.extend([str(a) for a in extra])

    print(
        "[campaign] start",
        f"scenario={scenario['name']}",
        f"cycles={scenario['cycles']}",
        f"hz={scenario['hz']}",
        f"gust={scenario.get('gust', False)}",
    )
    result = subprocess.run(cmd, cwd=repo_root)
    return int(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run autonomous SIL campaigns via X-Plane Web API")
    parser.add_argument("--host", default="127.0.0.1", help="X-Plane host")
    parser.add_argument("--port", type=int, default=8086, help="X-Plane Web API port")
    parser.add_argument("--repeats", type=int, default=1, help="Number of campaign repetitions")
    parser.add_argument("--include-gust", action="store_true", help="Add gust-enabled runs")
    parser.add_argument(
        "--pause-on-exit",
        action="store_true",
        default=True,
        help="Pause sim when campaign exits (default: enabled)",
    )
    parser.add_argument(
        "--no-pause-on-exit",
        action="store_false",
        dest="pause_on_exit",
        help="Do not pause sim at campaign exit",
    )
    parser.add_argument(
        "--stabilize-on-exit",
        action="store_true",
        help="Before pause/exit, run best-effort level-and-climb cleanup",
    )
    parser.add_argument(
        "--cleanup-target-altitude-ft",
        type=float,
        default=2000.0,
        help="Target altitude for stabilize-on-exit cleanup (feet MSL)",
    )
    parser.add_argument(
        "--cleanup-duration-s",
        type=float,
        default=20.0,
        help="Duration of stabilize-on-exit cleanup window in seconds",
    )
    parser.add_argument(
        "--strict-readiness",
        action="store_true",
        help="Stop campaign when readiness checks fail. Default behavior classifies failures as INFRA_FAIL and continues.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Path to scenario manifest JSON. If set, overrides --profile and --include-gust.",
    )
    parser.add_argument(
        "--profile",
        choices=("default", "smoke"),
        default="default",
        help="Campaign size: default for full run, smoke for short verification",
    )
    parser.add_argument(
        "--preflight-active-recovery",
        action="store_true",
        help="Before each scenario, run an active hold loop for wings-level shallow-climb recovery.",
    )
    parser.add_argument(
        "--preflight-recovery-duration-s",
        type=float,
        default=20.0,
        help="Duration in seconds for preflight active recovery hold.",
    )
    parser.add_argument(
        "--preflight-recovery-rate-hz",
        type=float,
        default=15.0,
        help="Loop rate for preflight active recovery hold.",
    )
    parser.add_argument(
        "--preflight-target-pitch-deg",
        type=float,
        default=2.0,
        help="Target pitch for preflight active recovery hold.",
    )
    parser.add_argument(
        "--preflight-throttle-ratio",
        type=float,
        default=0.68,
        help="Throttle ratio maintained during preflight active recovery hold.",
    )
    parser.add_argument(
        "--preflight-mixture-ratio",
        type=float,
        default=1.0,
        help="Mixture ratio maintained during preflight active recovery hold.",
    )
    parser.add_argument(
        "--preflight-override-controls",
        action="store_true",
        help="Enable X-Plane joystick control override during preflight active recovery hold.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_root = repo_root / "logs" / "sil_campaign"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    host = args.host
    port = args.port
    repeats = args.repeats
    startup_flight: Dict[str, Any] | None = None
    reset_each_run = False
    reset_wait_s = 8.0
    reset_request_timeout_s = 90.0
    reset_retries = 2
    airborne_after_reset = False
    airborne_each_run = False
    pause_during_airborne_setup = True
    airborne_altitude_agl_ft = 3000.0
    airborne_airspeed_kias = 100.0
    airborne_wait_s = 3.0
    post_reset_throttle_ratio: float | None = None
    post_reset_mixture_ratio: float | None = None
    post_reset_propulsion_hold_s = 0.0
    preflight_active_recovery = bool(args.preflight_active_recovery)
    preflight_recovery_duration_s = float(args.preflight_recovery_duration_s)
    preflight_recovery_rate_hz = float(args.preflight_recovery_rate_hz)
    preflight_target_pitch_deg = float(args.preflight_target_pitch_deg)
    preflight_throttle_ratio = max(0.0, min(1.0, float(args.preflight_throttle_ratio)))
    preflight_mixture_ratio: float | None = max(
        0.0, min(1.0, float(args.preflight_mixture_ratio))
    )
    preflight_override_controls = bool(args.preflight_override_controls)
    engage_autopilot_after_reset = False

    scenarios: List[Dict[str, Any]]
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = (repo_root / manifest_path).resolve()
        manifest = load_manifest(manifest_path)
        host = manifest.get("host", host)
        port = int(manifest.get("port", port))
        repeats = int(manifest.get("repeats", repeats))
        startup_flight = manifest.get("startup_flight")
        reset_each_run = bool(manifest.get("reset_each_run", False))
        reset_wait_s = float(manifest.get("reset_wait_s", reset_wait_s))
        reset_request_timeout_s = float(
            manifest.get("reset_request_timeout_s", reset_request_timeout_s)
        )
        reset_retries = int(manifest.get("reset_retries", reset_retries))
        airborne_after_reset = bool(manifest.get("airborne_after_reset", airborne_after_reset))
        airborne_each_run = bool(manifest.get("airborne_each_run", airborne_each_run))
        pause_during_airborne_setup = bool(
            manifest.get("pause_during_airborne_setup", pause_during_airborne_setup)
        )
        airborne_altitude_agl_ft = float(
            manifest.get("airborne_altitude_agl_ft", airborne_altitude_agl_ft)
        )
        airborne_airspeed_kias = float(
            manifest.get("airborne_airspeed_kias", airborne_airspeed_kias)
        )
        airborne_wait_s = float(manifest.get("airborne_wait_s", airborne_wait_s))
        if "post_reset_throttle_ratio" in manifest:
            post_reset_throttle_ratio = float(manifest["post_reset_throttle_ratio"])
        if "post_reset_mixture_ratio" in manifest:
            post_reset_mixture_ratio = float(manifest["post_reset_mixture_ratio"])
        post_reset_propulsion_hold_s = float(
            manifest.get("post_reset_propulsion_hold_s", post_reset_propulsion_hold_s)
        )
        preflight_active_recovery = bool(
            manifest.get("preflight_active_recovery", preflight_active_recovery)
        )
        preflight_recovery_duration_s = float(
            manifest.get("preflight_recovery_duration_s", preflight_recovery_duration_s)
        )
        preflight_recovery_rate_hz = float(
            manifest.get("preflight_recovery_rate_hz", preflight_recovery_rate_hz)
        )
        preflight_target_pitch_deg = float(
            manifest.get("preflight_target_pitch_deg", preflight_target_pitch_deg)
        )
        preflight_throttle_ratio = max(
            0.0,
            min(
                1.0,
                float(manifest.get("preflight_throttle_ratio", preflight_throttle_ratio)),
            ),
        )
        if "preflight_mixture_ratio" in manifest:
            preflight_mixture_ratio = max(0.0, min(1.0, float(manifest["preflight_mixture_ratio"])))
        preflight_override_controls = bool(
            manifest.get("preflight_override_controls", preflight_override_controls)
        )
        engage_autopilot_after_reset = bool(
            manifest.get("engage_autopilot_after_reset", False)
        )
        scenarios = [dict(s) for s in manifest["scenarios"]]
        print(f"[campaign] using manifest: {manifest_path}")
    else:
        base_scenarios = DEFAULT_SCENARIOS if args.profile == "default" else SMOKE_SCENARIOS
        scenarios = [dict(s) for s in base_scenarios]
        if args.include_gust:
            scenarios.append({"name": "runway_idle_gust", "cycles": 600, "hz": 20, "gust": True})

    readiness_failures = evaluate_readiness(host, port)
    readiness_ok = len(readiness_failures) == 0
    for rf in readiness_failures:
        print(f"[campaign] readiness: {rf['reason_code']} - {rf['message']}")
    if (not readiness_ok) and args.strict_readiness:
        print("[campaign] strict readiness enabled: campaign will not execute scenarios")

    summary: List[Dict[str, Any]] = []
    total = 0
    failures = 0
    reason_counts: Dict[str, int] = {}

    if (not readiness_ok) and args.strict_readiness:
        for rf in readiness_failures:
            reason_counts[rf["reason_code"]] = reason_counts.get(rf["reason_code"], 0) + 1

        summary_json = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "host": host,
            "port": port,
            "repeats": repeats,
            "total_runs": 0,
            "failures": len(readiness_failures),
            "readiness_ok": False,
            "readiness_failures": readiness_failures,
            "reason_counts": reason_counts,
            "results": [],
        }

        campaign_summary_json = run_dir / "campaign_summary.json"
        campaign_summary_md = run_dir / "campaign_summary.md"
        legacy_summary = run_dir / "summary.json"
        with campaign_summary_json.open("w", encoding="utf-8") as f:
            json.dump(summary_json, f, indent=2)
        with legacy_summary.open("w", encoding="utf-8") as f:
            json.dump(summary_json, f, indent=2)
        _write_campaign_markdown(
            campaign_summary_md,
            host=host,
            port=port,
            repeats=repeats,
            total_runs=0,
            failures=len(readiness_failures),
            reason_counts=reason_counts,
            results=[],
        )
        print(f"[campaign] artifacts: {campaign_summary_json.relative_to(repo_root)}")
        print(f"[campaign] artifacts: {campaign_summary_md.relative_to(repo_root)}")
        if args.stabilize_on_exit:
            try:
                stabilize_and_climb(
                    host,
                    port,
                    target_altitude_ft=args.cleanup_target_altitude_ft,
                    duration_s=args.cleanup_duration_s,
                )
            except Exception as exc:
                print(f"[campaign] warning: cleanup stabilize failed: {exc}")
        if args.pause_on_exit:
            try:
                force_pause(host, port)
            except Exception as exc:
                print(f"[campaign] warning: could not pause sim at exit: {exc}")
        return 2

    for rep in range(1, repeats + 1):
        print(f"[campaign] repetition {rep}/{repeats}")
        for scenario in scenarios:
            total += 1
            log_name = f"{rep:03d}_{scenario['name']}.jsonl"
            log_path = run_dir / log_name
            scenario_id = scenario.get("scenario_id", scenario["name"])

            if readiness_ok and reset_each_run and startup_flight is not None:
                reset_error = None
                attempts = max(1, reset_retries + 1)
                for attempt in range(1, attempts + 1):
                    try:
                        print(
                            f"[campaign] reset: start_flight before scenario={scenario['name']} "
                            f"attempt={attempt}/{attempts} timeout_s={reset_request_timeout_s:.1f}"
                        )
                        _start_flight(
                            host,
                            port,
                            startup_flight,
                            timeout_s=reset_request_timeout_s,
                        )
                        reset_error = None
                        break
                    except requests.Timeout as exc:
                        reset_error = (
                            f"timeout on reset attempt {attempt}/{attempts}: {exc}"
                        )
                        if attempt < attempts:
                            time.sleep(1.0)
                    except Exception as exc:
                        reset_error = str(exc)
                        break

                if reset_error is not None:
                    rc = 2
                    ok = False
                    status = "INFRA_FAIL"
                    code = "INFRA_FAIL_STARTUP_RESET"
                    reason_counts[code] = reason_counts.get(code, 0) + 1
                    scenario_reason_counts = {code: 1}
                    failures += 1
                    summary.append(
                        {
                            "repeat": rep,
                            "scenario_id": scenario_id,
                            "scenario": scenario["name"],
                            "cycles": scenario["cycles"],
                            "hz": scenario["hz"],
                            "gust": scenario.get("gust", False),
                            "log": str(log_path.relative_to(repo_root)),
                            "return_code": rc,
                            "status": status,
                            "ok": ok,
                            "reason_counts": scenario_reason_counts,
                            "reset_error": reset_error,
                        }
                    )
                    continue

                if reset_wait_s > 0:
                    time.sleep(reset_wait_s)

                if airborne_after_reset:
                    try:
                        _teleport_airborne(
                            host,
                            port,
                            altitude_agl_ft=airborne_altitude_agl_ft,
                            airspeed_kias=airborne_airspeed_kias,
                            wait_s=airborne_wait_s,
                        )
                    except Exception as exc:
                        print(f"[campaign] warning: airborne teleport failed: {exc}")

                    if scenario.get("init_lat") is not None and scenario.get("init_lon") is not None:
                        try:
                            _inject_scenario_position(
                                host,
                                port,
                                lat_deg=float(scenario["init_lat"]),
                                lon_deg=float(scenario["init_lon"]),
                                heading_deg=float(scenario.get("init_heading_deg", 90.0)),
                                airspeed_kias=float(
                                    scenario.get("init_airspeed_kias", airborne_airspeed_kias)
                                ),
                                init_pitch_deg=float(scenario.get("init_pitch_deg", 3.0)),
                                init_bank_deg=float(scenario.get("init_bank_deg", 0.0)),
                                init_elev_trim=float(scenario.get("init_elev_trim", 0.0)),
                                settle_s=float(scenario.get("init_position_wait_s", 2.0)),
                            )
                        except Exception as exc:
                            print(f"[campaign] warning: position inject failed: {exc}")

                _eff_throttle = (
                    float(scenario["init_throttle_ratio"])
                    if "init_throttle_ratio" in scenario
                    else post_reset_throttle_ratio
                )
                _eff_hold_s = (
                    float(scenario.get("init_propulsion_hold_s", post_reset_propulsion_hold_s))
                )
                if _eff_throttle is not None:
                    try:
                        _apply_post_reset_propulsion_state(
                            host,
                            port,
                            throttle_ratio=_eff_throttle,
                            mixture_ratio=post_reset_mixture_ratio,
                            hold_s=_eff_hold_s,
                        )
                    except Exception as exc:
                        print(f"[campaign] warning: propulsion init failed: {exc}")

                _scenario_autopilot = scenario.get("engage_autopilot", engage_autopilot_after_reset)
                if _scenario_autopilot:
                    try:
                        _engage_xplane_autopilot(host, port)
                    except Exception as exc:
                        print(f"[campaign] warning: autopilot engage failed: {exc}")

            if readiness_ok and airborne_each_run:
                if pause_during_airborne_setup:
                    try:
                        force_pause(host, port)
                    except Exception as exc:
                        print(f"[campaign] warning: could not pause before airborne setup: {exc}")

                try:
                    _teleport_airborne(
                        host,
                        port,
                        altitude_agl_ft=airborne_altitude_agl_ft,
                        airspeed_kias=airborne_airspeed_kias,
                        wait_s=airborne_wait_s,
                    )
                except Exception as exc:
                    print(f"[campaign] warning: airborne_each_run teleport failed: {exc}")

                if post_reset_throttle_ratio is not None:
                    try:
                        _apply_post_reset_propulsion_state(
                            host,
                            port,
                            throttle_ratio=post_reset_throttle_ratio,
                            mixture_ratio=post_reset_mixture_ratio,
                            hold_s=post_reset_propulsion_hold_s,
                        )
                    except Exception as exc:
                        print(f"[campaign] warning: airborne_each_run propulsion init failed: {exc}")

                if pause_during_airborne_setup:
                    try:
                        force_unpause(host, port)
                    except Exception as exc:
                        print(f"[campaign] warning: could not unpause after airborne setup: {exc}")

            if readiness_ok:
                if preflight_active_recovery:
                    try:
                        _active_recovery_hold(
                            host,
                            port,
                            duration_s=preflight_recovery_duration_s,
                            rate_hz=preflight_recovery_rate_hz,
                            target_pitch_deg=preflight_target_pitch_deg,
                            throttle_ratio=preflight_throttle_ratio,
                            mixture_ratio=preflight_mixture_ratio,
                            override_controls=preflight_override_controls,
                        )
                    except Exception as exc:
                        print(f"[campaign] warning: preflight active recovery failed: {exc}")
                rc = run_one_sil(repo_root, host, scenario, log_path)
                ok = rc == 0
                status = "PASS" if ok else "FAIL"
                scenario_reason_counts = _extract_reason_counts(log_path)
                _merge_reason_counts(reason_counts, scenario_reason_counts)
            else:
                rc = 2
                ok = False
                status = "INFRA_FAIL"
                scenario_reason_counts = {}
                for rf in readiness_failures:
                    code = rf["reason_code"]
                    reason_counts[code] = reason_counts.get(code, 0) + 1
                    scenario_reason_counts[code] = scenario_reason_counts.get(code, 0) + 1

            if not ok:
                failures += 1
            summary.append(
                {
                    "repeat": rep,
                    "scenario_id": scenario_id,
                    "scenario": scenario["name"],
                    "cycles": scenario["cycles"],
                    "hz": scenario["hz"],
                    "gust": scenario.get("gust", False),
                    "log": str(log_path.relative_to(repo_root)),
                    "return_code": rc,
                    "status": status,
                    "ok": ok,
                    "reason_counts": scenario_reason_counts,
                }
            )

    summary_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "host": host,
        "port": port,
        "repeats": repeats,
        "total_runs": total,
        "failures": failures,
        "readiness_ok": readiness_ok,
        "readiness_failures": readiness_failures,
        "reset_each_run": reset_each_run,
        "reset_wait_s": reset_wait_s,
        "reset_request_timeout_s": reset_request_timeout_s,
        "reset_retries": reset_retries,
        "airborne_after_reset": airborne_after_reset,
        "airborne_each_run": airborne_each_run,
        "pause_during_airborne_setup": pause_during_airborne_setup,
        "airborne_altitude_agl_ft": airborne_altitude_agl_ft,
        "airborne_airspeed_kias": airborne_airspeed_kias,
        "post_reset_throttle_ratio": post_reset_throttle_ratio,
        "post_reset_mixture_ratio": post_reset_mixture_ratio,
        "post_reset_propulsion_hold_s": post_reset_propulsion_hold_s,
        "preflight_active_recovery": preflight_active_recovery,
        "preflight_recovery_duration_s": preflight_recovery_duration_s,
        "preflight_recovery_rate_hz": preflight_recovery_rate_hz,
        "preflight_target_pitch_deg": preflight_target_pitch_deg,
        "preflight_throttle_ratio": preflight_throttle_ratio,
        "preflight_mixture_ratio": preflight_mixture_ratio,
        "preflight_override_controls": preflight_override_controls,
        "startup_flight_defined": startup_flight is not None,
        "reason_counts": reason_counts,
        "results": summary,
    }

    summary_path = run_dir / "summary.json"
    campaign_summary_json = run_dir / "campaign_summary.json"
    campaign_summary_md = run_dir / "campaign_summary.md"

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)
    with campaign_summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    _write_campaign_markdown(
        campaign_summary_md,
        host=host,
        port=port,
        repeats=repeats,
        total_runs=total,
        failures=failures,
        reason_counts=reason_counts,
        results=summary,
    )

    print(f"[campaign] complete: total_runs={total}, failures={failures}")
    print(f"[campaign] artifacts: {campaign_summary_json.relative_to(repo_root)}")
    print(f"[campaign] artifacts: {campaign_summary_md.relative_to(repo_root)}")
    if args.stabilize_on_exit:
        try:
            stabilize_and_climb(
                host,
                port,
                target_altitude_ft=args.cleanup_target_altitude_ft,
                duration_s=args.cleanup_duration_s,
            )
        except Exception as exc:
            print(f"[campaign] warning: cleanup stabilize failed: {exc}")
    if args.pause_on_exit:
        try:
            force_pause(host, port)
        except Exception as exc:
            print(f"[campaign] warning: could not pause sim at exit: {exc}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
