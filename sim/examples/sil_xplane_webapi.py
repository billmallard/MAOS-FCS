"""MAOS-FCS Software-in-the-Loop (SIL) example with X-Plane Web API integration.

Similar to sil_xplane.py but uses X-Plane's REST API (port 8086) instead of UDP.

This version uses the built-in Web API that's available in X-Plane 12.1.1+.

Usage
-----
1. Start X-Plane 12 with an aircraft loaded (not paused)
2. Run::

    python sim/examples/sil_xplane_webapi.py

Optional environment variables:
    XPLANE_HOST   IP address (default: 127.0.0.1)
    SIL_HZ        Loop rate in Hz (default: 20)
    SIL_CYCLES    Max cycles (default: 200)
    SIL_LOG       Event log path (default: sil_events_webapi.jsonl)

The Web API connection is more reliable than UDP and doesn't require
firewall configuration.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Allow running from repo root without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aircraft_config import build_axis_profile_map, load_aircraft_config, resolve_profiles
from actuator_runtime import build_actuator_command_frames
from control_arch import FixedCommandProvider, FlightState, ProviderRegistry
from control_law_engine import AircraftState, apply_protections, load_protection_config
from event_log import EventLogger
from fcs_runtime import FcsRuntime
from gust_alleviation_provider import GustAlleviationProvider
from triplex_voter import LaneSample
from xplane_web_api_bridge import (
    XPlaneWebAPICommandSink,
    XPlaneWebAPIControlProvider,
    XPlaneWebAPIStateSource,
)

# ---------------------------------------------------------------------------
# Configuration paths (relative to repo root)
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_AIRCRAFT_CFG = os.path.join(_REPO_ROOT, "configs", "aircraft", "ga_default.json")
_PROFILES_DIR = os.path.join(_REPO_ROOT, "configs", "actuator_profiles")
_CONTROL_LAWS = os.path.join(_REPO_ROOT, "configs", "control_laws", "ga_default.json")
_DEFAULT_LOG = os.path.join(_REPO_ROOT, "sil_events_webapi.jsonl")

# ---------------------------------------------------------------------------
# Environment knobs
# ---------------------------------------------------------------------------

XPLANE_HOST = os.environ.get("XPLANE_HOST", "127.0.0.1")
SIL_HZ = int(os.environ.get("SIL_HZ", "20"))
SIL_CYCLES = int(os.environ.get("SIL_CYCLES", "200"))
SIL_LOG = os.environ.get("SIL_LOG", _DEFAULT_LOG)
SIL_ENABLE_GUST = os.environ.get("SIL_ENABLE_GUST", "0").lower() in ("1", "true", "yes")


def _make_synthetic_lanes(pitch: float, roll: float, yaw: float) -> list[LaneSample]:
    """Create three nominally-agreeing lane samples for the voter."""
    return [
        LaneSample(lane_id="A", command=pitch, healthy=True),
        LaneSample(lane_id="B", command=pitch, healthy=True),
        LaneSample(lane_id="C", command=pitch, healthy=True),
    ]


def run_sil_loop(
    *,
    cycles: int = SIL_CYCLES,
    hz: int = SIL_HZ,
    xplane_host: str = XPLANE_HOST,
    log_path: str = SIL_LOG,
    enable_gust: bool | None = None,
) -> None:
    """Run the SIL loop for `cycles` iterations at `hz` Hz using Web API."""

    if enable_gust is None:
        enable_gust = SIL_ENABLE_GUST

    # ------------------------------------------------------------------
    # Boot sequence
    # ------------------------------------------------------------------
    print(f"[SIL] Loading aircraft config: {_AIRCRAFT_CFG}")
    aircraft_cfg = load_aircraft_config(_AIRCRAFT_CFG)
    profiles = resolve_profiles(aircraft_cfg, _PROFILES_DIR)
    axis_profile_map = build_axis_profile_map(profiles)
    primary_profile = profiles[0]

    print(f"[SIL] Aircraft: {aircraft_cfg.aircraft_name}")
    print(f"[SIL] Active profiles: {[p.vendor_key for p in profiles]}")
    print(f"[SIL] Covered axes: {sorted(axis_profile_map)}")

    protection_cfg = load_protection_config(_CONTROL_LAWS)
    print(
        f"[SIL] Protections: {protection_cfg.min_airspeed_kias:.0f}–"
        f"{protection_cfg.max_airspeed_kias:.0f} KIAS, "
        f"max bank {protection_cfg.max_bank_deg:.0f}°"
    )

    logger = EventLogger(log_path)
    runtime = FcsRuntime()

    # Provider registry: neutral trim + X-Plane Web API autopilot
    registry = ProviderRegistry()
    registry.register(
        FixedCommandProvider(
            name="neutral_trim",
            priority=10,
            command_map={"pitch": 0.0, "roll": 0.0, "yaw": 0.0},
        )
    )

    # X-Plane Web API state source and command sink
    print(f"[SIL] Connecting to X-Plane Web API at {xplane_host}:8086...")
    xp_source = XPlaneWebAPIStateSource(xplane_host=xplane_host, poll_hz=hz)
    xp_sink = XPlaneWebAPICommandSink(xplane_host=xplane_host)
    xp_provider = XPlaneWebAPIControlProvider(
        name="xplane_webapi",
        priority=50,
        state_source=xp_source,
    )
    registry.register(xp_provider)

    # Optional gust alleviation provider
    if enable_gust:
        gust_provider = GustAlleviationProvider(priority=60)
        registry.register(gust_provider)
        print("[SIL] Gust alleviation enabled (priority 60)")

    # Start polling X-Plane state
    xp_source.start()

    dt = 1.0 / hz
    sequence = 0

    print(f"[SIL] Starting loop: {cycles} cycles @ {hz} Hz")
    logger.emit(
        event_type="sil_start",
        mode="triplex",
        reason_code="boot",
        details={
            "aircraft_name": aircraft_cfg.aircraft_name,
            "active_profiles": [p.vendor_key for p in profiles],
            "hz": hz,
            "cycles": cycles,
            "api_type": "webapi",
            "xplane_host": xplane_host,
            "gust_enabled": enable_gust,
        },
    )

    try:
        for cycle in range(cycles):
            t0 = time.monotonic()

            # 1. Gather current flight state from X-Plane (or defaults)
            if xp_source.state.is_fresh():
                flight_state = xp_source.state.as_flight_state()
                aircraft_state = xp_source.state.as_aircraft_state()
            else:
                flight_state = FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0)
                aircraft_state = AircraftState(airspeed_kias=90.0, bank_deg=0.0)

            # 2. Aggregate axis commands from provider registry
            raw_commands = registry.aggregated_commands(flight_state)

            # 3. Apply envelope protections
            protection_result = apply_protections(raw_commands, aircraft_state, protection_cfg)
            protected_commands = protection_result.commands

            # 4. Run vote cycle
            pitch_cmd = protected_commands.get("pitch", 0.0)
            lanes = _make_synthetic_lanes(
                pitch_cmd,
                protected_commands.get("roll", 0.0),
                protected_commands.get("yaw", 0.0),
            )
            vote_result = runtime.run_vote_cycle(lanes, logger=logger)

            # 5. Build actuator command frames
            frames = build_actuator_command_frames(
                profile=primary_profile,
                axis_commands=protected_commands,
                sequence=sequence,
            )

            # 6. Send to X-Plane
            xp_sink.send_commands(protected_commands)

            # 7. Log cycle summary every second
            if cycle % hz == 0:
                flags = protection_result.flags
                active = [k for k, v in flags.items() if v]
                print(
                    f"[SIL] cycle={cycle:4d}  mode={vote_result.mode:8s}  "
                    f"IAS={aircraft_state.airspeed_kias:5.1f}  "
                    f"pitch={pitch_cmd:+.3f}  frames={len(frames)}  "
                    f"protections={active or 'none'}"
                )

            sequence += 1

            # Pace to target Hz
            elapsed = time.monotonic() - t0
            sleep_s = dt - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    finally:
        xp_source.stop()
        xp_sink.close()
        print(f"[SIL] Loop complete. Events logged to: {log_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MAOS-FCS SIL loop via X-Plane Web API.")
    parser.add_argument("--cycles", type=int, default=SIL_CYCLES, help="Number of loop cycles")
    parser.add_argument("--hz", type=int, default=SIL_HZ, help="Loop rate in Hz")
    parser.add_argument("--host", default=XPLANE_HOST, help="X-Plane host (default: 127.0.0.1)")
    parser.add_argument("--log", default=SIL_LOG, help="Path to JSONL event log")
    parser.add_argument("--gust", action="store_true", help="Enable gust alleviation provider")
    args = parser.parse_args()

    run_sil_loop(
        cycles=args.cycles,
        hz=args.hz,
        xplane_host=args.host,
        log_path=args.log,
        enable_gust=args.gust,
    )
