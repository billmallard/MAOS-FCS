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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

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
from xte_oracle import XteOracle, XteScenario

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


# ---------------------------------------------------------------------------
# FCS mode and protection oracle
# ---------------------------------------------------------------------------

@dataclass
class FcsModeOracleConfig:
    """Assertions evaluated at end of run against collected mode/protection data."""

    # Mode assertions
    assert_mode_stable: Optional[str] = None        # mode must never leave this value
    assert_mode_final: Optional[str] = None          # mode must be this at run end
    assert_transitions_min: Optional[int] = None     # at least N mode transitions
    assert_transitions_max: Optional[int] = None     # at most N mode transitions
    # assert mode transitions within N cycles of fault injection start
    assert_transition_within: Optional[int] = None
    fault_start_cycle: Optional[int] = None          # reference cycle for transition_within

    # Protection assertions
    assert_protection_fires: List[str] = field(default_factory=list)
    assert_protection_never: List[str] = field(default_factory=list)

    # Structural assertions
    assert_frames_min: Optional[int] = None          # at least N frames emitted total
    assert_state_fresh_min_pct: Optional[float] = None  # at least N% cycles had fresh state


@dataclass
class FcsModeOracleResult:
    passed: bool
    reasons: List[str]
    final_mode: str
    mode_transitions: List[tuple]   # (cycle, from_mode, to_mode)
    protection_fired: Set[str]
    total_frames: int
    fresh_cycles: int
    total_cycles: int

    def summary(self) -> Dict:
        return {
            "passed": self.passed,
            "reasons": self.reasons,
            "final_mode": self.final_mode,
            "mode_transition_count": len(self.mode_transitions),
            "mode_transitions": [
                {"cycle": c, "from": f, "to": t} for c, f, t in self.mode_transitions
            ],
            "protection_fired": sorted(self.protection_fired),
            "total_frames": self.total_frames,
            "fresh_pct": (
                round(100.0 * self.fresh_cycles / self.total_cycles, 1)
                if self.total_cycles > 0 else 0.0
            ),
        }


def _evaluate_fcs_oracle(
    cfg: FcsModeOracleConfig,
    mode_transitions: List[tuple],
    final_mode: str,
    mode_history: List[str],
    protection_fired: Set[str],
    total_frames: int,
    fresh_cycles: int,
    total_cycles: int,
) -> FcsModeOracleResult:
    reasons: List[str] = []

    # --- mode_stable ---
    if cfg.assert_mode_stable is not None:
        unstable = [m for m in mode_history if m != cfg.assert_mode_stable]
        if unstable:
            reasons.append(
                f"mode_stable: expected {cfg.assert_mode_stable!r} throughout "
                f"but saw {sorted(set(unstable))}"
            )

    # --- mode_final ---
    if cfg.assert_mode_final is not None and final_mode != cfg.assert_mode_final:
        reasons.append(
            f"mode_final: expected {cfg.assert_mode_final!r} got {final_mode!r}"
        )

    # --- transitions count ---
    n = len(mode_transitions)
    if cfg.assert_transitions_min is not None and n < cfg.assert_transitions_min:
        reasons.append(
            f"transitions_min: expected ≥{cfg.assert_transitions_min} transitions, got {n}"
        )
    if cfg.assert_transitions_max is not None and n > cfg.assert_transitions_max:
        reasons.append(
            f"transitions_max: expected ≤{cfg.assert_transitions_max} transitions, got {n}"
        )

    # --- transition_within N cycles of fault start ---
    if cfg.assert_transition_within is not None and cfg.fault_start_cycle is not None:
        deadline = cfg.fault_start_cycle + cfg.assert_transition_within
        first_after = next(
            (c for c, _, _ in mode_transitions if c >= cfg.fault_start_cycle), None
        )
        if first_after is None:
            reasons.append(
                f"transition_within: no transition found after fault_start={cfg.fault_start_cycle}"
            )
        elif first_after > deadline:
            reasons.append(
                f"transition_within: first transition at cycle {first_after}, "
                f"expected within {cfg.assert_transition_within} cycles of fault_start={cfg.fault_start_cycle}"
            )

    # --- protection_fires ---
    for flag in cfg.assert_protection_fires:
        if flag not in protection_fired:
            reasons.append(f"protection_fires: {flag!r} never triggered")

    # --- protection_never ---
    for flag in cfg.assert_protection_never:
        if flag in protection_fired:
            reasons.append(f"protection_never: {flag!r} triggered but must not fire")

    # --- frames_min ---
    if cfg.assert_frames_min is not None and total_frames < cfg.assert_frames_min:
        reasons.append(
            f"frames_min: expected ≥{cfg.assert_frames_min} frames, got {total_frames}"
        )

    # --- state_fresh_min_pct ---
    if cfg.assert_state_fresh_min_pct is not None and total_cycles > 0:
        pct = 100.0 * fresh_cycles / total_cycles
        if pct < cfg.assert_state_fresh_min_pct:
            reasons.append(
                f"state_fresh: {pct:.1f}% fresh cycles, "
                f"expected ≥{cfg.assert_state_fresh_min_pct:.0f}%"
            )

    passed = len(reasons) == 0
    return FcsModeOracleResult(
        passed=passed,
        reasons=reasons,
        final_mode=final_mode,
        mode_transitions=mode_transitions,
        protection_fired=protection_fired,
        total_frames=total_frames,
        fresh_cycles=fresh_cycles,
        total_cycles=total_cycles,
    )


# ---------------------------------------------------------------------------
# Lane sample factory with optional fault injection
# ---------------------------------------------------------------------------

def _make_synthetic_lanes(
    pitch: float,
    roll: float,
    yaw: float,
    *,
    lane_c_bias: float = 0.0,
) -> List[LaneSample]:
    """Create three lane samples for the voter, with optional bias on lane C."""
    return [
        LaneSample(lane_id="A", command=pitch, healthy=True),
        LaneSample(lane_id="B", command=pitch, healthy=True),
        LaneSample(lane_id="C", command=pitch + lane_c_bias, healthy=True),
    ]


# ---------------------------------------------------------------------------
# Main SIL loop
# ---------------------------------------------------------------------------

def run_sil_loop(
    *,
    cycles: int = SIL_CYCLES,
    hz: int = SIL_HZ,
    xplane_host: str = XPLANE_HOST,
    log_path: str = SIL_LOG,
    enable_gust: bool | None = None,
    xte_scenario: Optional[XteScenario] = None,
    # Fault injection
    fault_start_cycle: Optional[int] = None,
    fault_bias: float = 0.15,
    fault_clear_cycle: Optional[int] = None,
    # FCS mode / protection oracle
    fcs_oracle_cfg: Optional[FcsModeOracleConfig] = None,
    # Config overrides
    aircraft_config_path: Optional[str] = None,
) -> bool:
    """Run the SIL loop for `cycles` iterations at `hz` Hz using Web API.

    Returns True if all oracle checks passed (or no oracle), False on any failure.
    """
    if enable_gust is None:
        enable_gust = SIL_ENABLE_GUST

    # ------------------------------------------------------------------
    # Boot sequence
    # ------------------------------------------------------------------
    _cfg_path = aircraft_config_path or _AIRCRAFT_CFG
    print(f"[SIL] Loading aircraft config: {_cfg_path}")
    aircraft_cfg = load_aircraft_config(_cfg_path)
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

    if fault_start_cycle is not None:
        print(
            f"[SIL] Fault injection: lane C bias={fault_bias:+.3f} "
            f"start={fault_start_cycle} "
            f"clear={fault_clear_cycle if fault_clear_cycle is not None else 'never'}"
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

    if enable_gust:
        gust_provider = GustAlleviationProvider(priority=60)
        registry.register(gust_provider)
        print("[SIL] Gust alleviation enabled (priority 60)")

    xp_source.start()

    oracle = XteOracle(xte_scenario) if xte_scenario is not None else None
    if oracle is not None:
        print(
            f"[SIL] XTE oracle armed: wp=({xte_scenario.wp_lat},{xte_scenario.wp_lon}) "
            f"course={xte_scenario.desired_course_deg}° "
            f"sample={xte_scenario.sample_start_cycle}–{xte_scenario.sample_end_cycle} "
            f"range=[{xte_scenario.expected_min_nm},{xte_scenario.expected_max_nm}] nm"
        )

    dt = 1.0 / hz
    sequence = 0

    # FCS oracle tracking state
    mode_transitions: List[tuple] = []   # (cycle, from_mode, to_mode)
    mode_history: List[str] = []
    protection_fired: Set[str] = set()
    total_frames = 0
    fresh_cycles = 0
    prev_tracked_mode = "triplex"

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
            "fault_start_cycle": fault_start_cycle,
            "fault_bias": fault_bias if fault_start_cycle is not None else None,
            "fault_clear_cycle": fault_clear_cycle,
        },
    )

    try:
        for cycle in range(cycles):
            t0 = time.monotonic()

            # 1. Gather current flight state from X-Plane (or defaults)
            is_fresh = xp_source.state.is_fresh()
            if is_fresh:
                flight_state = xp_source.state.as_flight_state()
                aircraft_state = xp_source.state.as_aircraft_state()
                fresh_cycles += 1
            else:
                flight_state = FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0)
                aircraft_state = AircraftState(airspeed_kias=90.0, bank_deg=0.0)

            # 2. Aggregate axis commands from provider registry
            raw_commands = registry.aggregated_commands(flight_state)

            # 3. Apply envelope protections
            protection_result = apply_protections(raw_commands, aircraft_state, protection_cfg)
            protected_commands = protection_result.commands

            # Track which protection flags fired this cycle
            for flag, active in protection_result.flags.items():
                if active:
                    protection_fired.add(flag)

            # 4. Run vote cycle with optional fault injection on lane C
            pitch_cmd = protected_commands.get("pitch", 0.0)
            active_bias = 0.0
            if fault_start_cycle is not None and cycle >= fault_start_cycle:
                if fault_clear_cycle is None or cycle < fault_clear_cycle:
                    active_bias = fault_bias

            lanes = _make_synthetic_lanes(
                pitch_cmd,
                protected_commands.get("roll", 0.0),
                protected_commands.get("yaw", 0.0),
                lane_c_bias=active_bias,
            )
            vote_result = runtime.run_vote_cycle(lanes, logger=logger)

            # Track mode transitions for FCS oracle
            mode_history.append(vote_result.mode)
            if vote_result.mode != prev_tracked_mode:
                mode_transitions.append((cycle, prev_tracked_mode, vote_result.mode))
                prev_tracked_mode = vote_result.mode

            # 5. Build actuator command frames
            frames = build_actuator_command_frames(
                profile=primary_profile,
                axis_commands=protected_commands,
                sequence=sequence,
            )
            total_frames += len(frames)

            # 6. Send to X-Plane
            xp_sink.send_commands(protected_commands)

            # 7. XTE oracle sample
            if oracle is not None:
                lat = xp_source.state.lat_deg
                lon = xp_source.state.lon_deg
                if lat is not None and lon is not None:
                    xte = oracle.record(cycle, lat, lon)
                    if xte is not None and cycle % hz == 0:
                        logger.emit(
                            event_type="xte_sample",
                            mode=vote_result.mode,
                            reason_code="xte_sample",
                            details={
                                "cycle": cycle,
                                "lat": round(lat, 6),
                                "lon": round(lon, 6),
                                "xte_nm": round(xte, 4),
                            },
                        )

            # 8. Log cycle summary every second
            if cycle % hz == 0:
                flags = protection_result.flags
                active_flags = [k for k, v in flags.items() if v]
                xte_str = ""
                if oracle is not None:
                    lat = xp_source.state.lat_deg
                    lon = xp_source.state.lon_deg
                    if lat is not None and lon is not None and oracle._samples:
                        xte_str = f"  xte={oracle._samples[-1].xte_nm:+.3f}nm"
                fault_str = f"  bias={active_bias:+.3f}" if active_bias != 0.0 else ""
                print(
                    f"[SIL] cycle={cycle:4d}  mode={vote_result.mode:8s}  "
                    f"IAS={aircraft_state.airspeed_kias:5.1f}  "
                    f"bank={aircraft_state.bank_deg:+6.1f}  "
                    f"pitch={pitch_cmd:+.3f}  frames={len(frames)}  "
                    f"protections={active_flags or 'none'}{xte_str}{fault_str}"
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

    all_passed = True

    # --- XTE oracle ---
    if oracle is not None:
        result = oracle.evaluate()
        logger.emit(
            event_type="oracle_result",
            mode="triplex",
            reason_code="oracle_pass" if result.passed else "oracle_fail",
            details=result.summary(),
        )
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[SIL] XTE oracle {status}: "
            f"samples={result.samples} "
            f"mean={result.mean_xte_nm:+.3f}nm "
            f"std={result.std_xte_nm:.3f}nm "
            f"reason={result.reason}"
        )
        if not result.passed:
            all_passed = False

    # --- FCS mode / protection oracle ---
    if fcs_oracle_cfg is not None:
        fcs_result = _evaluate_fcs_oracle(
            cfg=fcs_oracle_cfg,
            mode_transitions=mode_transitions,
            final_mode=prev_tracked_mode,
            mode_history=mode_history,
            protection_fired=protection_fired,
            total_frames=total_frames,
            fresh_cycles=fresh_cycles,
            total_cycles=cycles,
        )
        status = "PASS" if fcs_result.passed else "FAIL"
        print(
            f"[SIL] FCS oracle {status}: "
            f"transitions={len(mode_transitions)} "
            f"final_mode={fcs_result.final_mode} "
            f"protections_fired={sorted(protection_fired) or 'none'} "
            f"frames={total_frames} "
            f"fresh={fcs_result.summary()['fresh_pct']}%"
        )
        if not fcs_result.passed:
            print(f"[SIL] FCS oracle failures: {fcs_result.reasons}")
        logger.emit(
            event_type="fcs_oracle_result",
            mode=prev_tracked_mode,
            reason_code="fcs_oracle_pass" if fcs_result.passed else "fcs_oracle_fail",
            details=fcs_result.summary(),
        )
        if not fcs_result.passed:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MAOS-FCS SIL loop via X-Plane Web API.")
    parser.add_argument("--cycles", type=int, default=SIL_CYCLES, help="Number of loop cycles")
    parser.add_argument("--hz", type=int, default=SIL_HZ, help="Loop rate in Hz")
    parser.add_argument("--host", default=XPLANE_HOST, help="X-Plane host (default: 127.0.0.1)")
    parser.add_argument("--log", default=SIL_LOG, help="Path to JSONL event log")
    parser.add_argument("--gust", action="store_true", help="Enable gust alleviation provider")
    parser.add_argument(
        "--aircraft-config", default=None,
        help="Path to aircraft config JSON (overrides default ga_default.json)",
    )

    # XTE oracle args
    parser.add_argument("--xte-wp-lat", type=float, default=None)
    parser.add_argument("--xte-wp-lon", type=float, default=None)
    parser.add_argument("--xte-course", type=float, default=None)
    parser.add_argument("--xte-sample-start", type=int, default=30)
    parser.add_argument("--xte-sample-end", type=int, default=270)
    parser.add_argument("--xte-min-nm", type=float, default=None)
    parser.add_argument("--xte-max-nm", type=float, default=None)

    # Fault injection args
    parser.add_argument(
        "--fault-start-cycle", type=int, default=None,
        help="Inject lane C bias starting at this cycle",
    )
    parser.add_argument(
        "--fault-bias", type=float, default=0.15,
        help="Lane C command offset (default 0.15; voter threshold is 0.08)",
    )
    parser.add_argument(
        "--fault-clear-cycle", type=int, default=None,
        help="Stop injecting fault at this cycle (omit to keep fault for rest of run)",
    )

    # FCS mode oracle args
    parser.add_argument(
        "--assert-mode-stable", default=None,
        help="Assert mode never leaves this value (e.g. triplex)",
    )
    parser.add_argument(
        "--assert-mode-final", default=None,
        help="Assert mode equals this value at end of run",
    )
    parser.add_argument(
        "--assert-transitions-min", type=int, default=None,
        help="Assert at least N mode transitions occurred",
    )
    parser.add_argument(
        "--assert-transitions-max", type=int, default=None,
        help="Assert at most N mode transitions occurred",
    )
    parser.add_argument(
        "--assert-transition-within", type=int, default=None,
        help="Assert a transition occurred within N cycles of --fault-start-cycle",
    )

    # FCS protection oracle args
    parser.add_argument(
        "--assert-protection-fires", action="append", default=[],
        metavar="FLAG",
        help="Assert this protection flag fired at least once (repeatable)",
    )
    parser.add_argument(
        "--assert-protection-never", action="append", default=[],
        metavar="FLAG",
        help="Assert this protection flag never fired (repeatable)",
    )

    # Structural oracle args
    parser.add_argument(
        "--assert-frames-min", type=int, default=None,
        help="Assert at least N actuator frames were emitted",
    )
    parser.add_argument(
        "--assert-state-fresh-min-pct", type=float, default=None,
        help="Assert at least N%% of cycles had fresh X-Plane state",
    )

    args = parser.parse_args()

    xte_scenario: Optional[XteScenario] = None
    if args.xte_wp_lat is not None and args.xte_wp_lon is not None and args.xte_course is not None:
        xte_scenario = XteScenario(
            wp_lat=args.xte_wp_lat,
            wp_lon=args.xte_wp_lon,
            desired_course_deg=args.xte_course,
            sample_start_cycle=args.xte_sample_start,
            sample_end_cycle=args.xte_sample_end,
            expected_min_nm=args.xte_min_nm,
            expected_max_nm=args.xte_max_nm,
        )

    fcs_oracle_cfg: Optional[FcsModeOracleConfig] = None
    _has_fcs_assert = any([
        args.assert_mode_stable,
        args.assert_mode_final,
        args.assert_transitions_min is not None,
        args.assert_transitions_max is not None,
        args.assert_transition_within is not None,
        args.assert_protection_fires,
        args.assert_protection_never,
        args.assert_frames_min is not None,
        args.assert_state_fresh_min_pct is not None,
    ])
    if _has_fcs_assert:
        fcs_oracle_cfg = FcsModeOracleConfig(
            assert_mode_stable=args.assert_mode_stable,
            assert_mode_final=args.assert_mode_final,
            assert_transitions_min=args.assert_transitions_min,
            assert_transitions_max=args.assert_transitions_max,
            assert_transition_within=args.assert_transition_within,
            fault_start_cycle=args.fault_start_cycle,
            assert_protection_fires=args.assert_protection_fires,
            assert_protection_never=args.assert_protection_never,
            assert_frames_min=args.assert_frames_min,
            assert_state_fresh_min_pct=args.assert_state_fresh_min_pct,
        )

    passed = run_sil_loop(
        cycles=args.cycles,
        hz=args.hz,
        xplane_host=args.host,
        log_path=args.log,
        enable_gust=args.gust,
        xte_scenario=xte_scenario,
        fault_start_cycle=args.fault_start_cycle,
        fault_bias=args.fault_bias,
        fault_clear_cycle=args.fault_clear_cycle,
        fcs_oracle_cfg=fcs_oracle_cfg,
        aircraft_config_path=args.aircraft_config,
    )
    sys.exit(0 if passed else 1)
