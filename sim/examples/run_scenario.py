#!/usr/bin/env python3
"""X-Plane SIL Test Scenario Runner

Usage:
    python sim/examples/run_scenario.py <scenario_name> [--plot]

Available scenarios:
    level_flight        — Steady level flight (5 sec, neutral controls)
    gentle_climb        — Gentle continuous climb at max 5° pitch
    steep_turn          — Coordinated 20° bank turn
    envelope_test       — Test control law protection limits
    fault_injection     — Simulate lane failure scenarios
    stall_recovery      — Approach stall and recovery
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from control_arch import ControlProvider, FlightState, FixedCommandProvider, ProviderOutput, ProviderRegistry
from aircraft_config import build_axis_profile_map, load_aircraft_config, resolve_profiles
from actuator_runtime import build_actuator_command_frames
from control_law_engine import AircraftState, apply_protections, load_protection_config
from event_log import EventLogger
from fcs_runtime import FcsRuntime
from triplex_voter import LaneSample
from xplane_bridge import XPlaneCommandSink, XPlaneControlProvider, XPlaneStateSource, XPlaneState

_REPO_ROOT = Path(__file__).parent.parent.parent
_AIRCRAFT_CFG = _REPO_ROOT / "configs" / "aircraft" / "ga_default.json"
_PROFILES_DIR = _REPO_ROOT / "configs" / "actuator_profiles"
_CONTROL_LAWS = _REPO_ROOT / "configs" / "control_laws" / "ga_default.json"


class CommandInjector(ControlProvider):
    """Injects scripted commands for test scenarios."""

    def __init__(
        self,
        name: str,
        priority: int,
        command_generator: Callable[[int, float], Dict[str, float]],
    ) -> None:
        self.name = name
        self.priority = priority
        self.command_generator = command_generator
        self._cycle = 0

    def provided_axes(self) -> set[str]:
        return {"pitch", "roll", "yaw", "flap"}

    def provide(self, flight_state: FlightState) -> ProviderOutput:
        cmds = self.command_generator(self._cycle, flight_state.airspeed_kias)
        self._cycle += 1
        return ProviderOutput(axis_commands=cmds)


def scenario_level_flight(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Maintain level flight with neutral controls."""
    return {"pitch": 0.0, "roll": 0.0, "yaw": 0.0, "flap": 0.0}


def scenario_gentle_climb(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Gentle continuous climb, max 5° pitch authority."""
    # Ramp pitch command from 0 to +0.1 (normalized) over 10 seconds (200 cycles at 20 Hz)
    frac = min(cycle / 200.0, 1.0)
    pitch_cmd = frac * 0.1  # Max ~5° pitch
    return {"pitch": pitch_cmd, "roll": 0.0, "yaw": 0.0, "flap": 0.0}


def scenario_steep_turn(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Coordinated 20° bank turn."""
    # Bank angle cycles: 0 → 20° → 0 → -20° → 0 over the run
    phase = (cycle % 400) / 100.0  # 4 phases of 100 cycles each
    if phase < 1.0:
        # Bank right: 0 → 20°
        roll_cmd = phase * 0.25
    elif phase < 2.0:
        # Level: 20° → 0°
        roll_cmd = (2.0 - phase) * 0.25
    elif phase < 3.0:
        # Bank left: 0 → -20°
        roll_cmd = -(phase - 2.0) * 0.25
    else:
        # Level: -20° → 0°
        roll_cmd = -(4.0 - phase) * 0.25

    # Gentle pitch to maintain altitude in turn
    pitch_cmd = 0.05
    return {"pitch": pitch_cmd, "roll": roll_cmd, "yaw": 0.0, "flap": 0.0}


def scenario_envelope_test(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Test control law protection by pushing envelope limits."""
    # Try to command extreme pitches and banks; protections should limit them
    if cycle < 100:
        # Push nose down then up
        pitch_cmd = -0.5 if cycle < 50 else 0.5
    else:
        # Push hard banks
        roll_cmd = 0.8 if cycle < 150 else -0.8
        return {"pitch": 0.0, "roll": roll_cmd, "yaw": 0.0, "flap": 0.0}

    return {"pitch": pitch_cmd, "roll": 0.0, "yaw": 0.0, "flap": 0.0}


def scenario_fault_injection(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Inject lane failures and observe degradation."""
    # This is a dry-run scenario; lane faults are simulated in voter logic
    # For now, command gentle maneuver
    if cycle < 100:
        return {"pitch": 0.05, "roll": 0.0, "yaw": 0.0, "flap": 0.0}
    else:
        return {"pitch": 0.0, "roll": 0.1, "yaw": 0.0, "flap": 0.0}


def scenario_stall_recovery(cycle: int, airspeed: float) -> Dict[str, float]:
    """Scenario: Approach stall (low airspeed) and command recovery."""
    # This is a dry-run scenario; actual airspeed depends on X-Plane or synthetic state
    if cycle < 50:
        # Reduce power, pitch up (nose heavy)
        return {"pitch": 0.3, "roll": 0.0, "yaw": 0.0, "flap": 0.2}
    elif cycle < 100:
        # Stall condition holding
        return {"pitch": 0.35, "roll": 0.0, "yaw": 0.0, "flap": 0.2}
    else:
        # Recovery: push nose down, reduce flaps
        return {"pitch": -0.1, "roll": 0.0, "yaw": 0.0, "flap": 0.0}


SCENARIOS = {
    "level_flight": {
        "cycles": 100,
        "hz": 20,
        "description": "Steady neutral controls, 5 sec",
        "generator": scenario_level_flight,
    },
    "gentle_climb": {
        "cycles": 200,
        "hz": 20,
        "description": "Gradual climb to 5° pitch, 10 sec",
        "generator": scenario_gentle_climb,
    },
    "steep_turn": {
        "cycles": 400,
        "hz": 20,
        "description": "Coordinated turns, 20 sec",
        "generator": scenario_steep_turn,
    },
    "envelope_test": {
        "cycles": 200,
        "hz": 20,
        "description": "Push control law limits, 10 sec",
        "generator": scenario_envelope_test,
    },
    "fault_injection": {
        "cycles": 300,
        "hz": 20,
        "description": "Lane fault scenarios, 15 sec",
        "generator": scenario_fault_injection,
    },
    "stall_recovery": {
        "cycles": 150,
        "hz": 20,
        "description": "Stall approach and recovery, 7.5 sec",
        "generator": scenario_stall_recovery,
    },
}


def run_scenario(
    scenario_name: str,
    xplane_host: str = "127.0.0.1",
    dry_run: bool = False,
) -> None:
    """Run a named test scenario."""
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    scenario = SCENARIOS[scenario_name]
    cycles = scenario["cycles"]
    hz = scenario["hz"]
    generator = scenario["generator"]

    print(f"\n{'─' * 70}")
    print(f"Scenario: {scenario_name.upper()}")
    print(f"{'─' * 70}")
    print(f"Duration: {cycles / hz:.1f} sec @ {hz} Hz")
    print(f"Description: {scenario['description']}\n")

    # Load configs
    aircraft_cfg = load_aircraft_config(_AIRCRAFT_CFG)
    profiles = resolve_profiles(aircraft_cfg, _PROFILES_DIR)
    primary_profile = profiles[0]

    protection_cfg = load_protection_config(_CONTROL_LAWS)
    logger = EventLogger(f"scenario_{scenario_name}.jsonl")
    runtime = FcsRuntime()

    # Provider registry
    registry = ProviderRegistry()
    registry.register(
        FixedCommandProvider(
            name="neutral_trim",
            priority=10,
            command_map={"pitch": 0.0, "roll": 0.0, "yaw": 0.0},
        )
    )

    # Scenario injector (high priority)
    registry.register(
        CommandInjector(
            name=f"scenario_{scenario_name}",
            priority=100,
            command_generator=generator,
        )
    )

    # X-Plane state source
    xp_source = XPlaneStateSource(xplane_host=xplane_host) if not dry_run else None
    xp_sink = XPlaneCommandSink(xplane_host=xplane_host) if not dry_run else None

    if not dry_run and xp_source is not None:
        print(f"[SCENARIO] Connecting to X-Plane at {xplane_host}...")
        xp_source.start()

    dt = 1.0 / hz
    events_emitted = []

    print(f"[SCENARIO] Running scenario...\n")
    try:
        for cycle in range(cycles):
            t0 = time.monotonic()

            # Gather flight state
            if xp_source is not None and xp_source.state.is_fresh():
                flight_state = xp_source.state.as_flight_state()
                aircraft_state = xp_source.state.as_aircraft_state()
            else:
                flight_state = FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0)
                aircraft_state = AircraftState(airspeed_kias=90.0, bank_deg=0.0)

            # Aggregate commands
            raw_commands = registry.aggregated_commands(flight_state)

            # Apply protections
            protection_result = apply_protections(raw_commands, aircraft_state, protection_cfg)
            protected_commands = protection_result.commands

            # Vote
            pitch_cmd = protected_commands.get("pitch", 0.0)
            lanes = [
                LaneSample(lane_id="A", command=pitch_cmd, healthy=True),
                LaneSample(lane_id="B", command=pitch_cmd, healthy=True),
                LaneSample(lane_id="C", command=pitch_cmd, healthy=True),
            ]
            vote_result = runtime.run_vote_cycle(lanes, logger=logger)

            # Send to X-Plane
            if xp_sink is not None:
                xp_sink.send_commands(protected_commands)

            # Log summary every ~1 sec
            if cycle % hz == 0:
                flags = protection_result.flags
                active = [k for k, v in flags.items() if v]
                line = (
                    f"[{cycle:3d}/{cycles}] IAS={aircraft_state.airspeed_kias:5.1f}  "
                    f"pitch={pitch_cmd:+.3f}  roll={protected_commands.get('roll', 0.0):+.3f}  "
                    f"protections={active or '(none)'}"
                )
                print(line)
                events_emitted.append(line)

            # Pace
            elapsed = time.monotonic() - t0
            sleep_s = dt - elapsed
            if sleep_s > 0 and not dry_run:
                time.sleep(sleep_s)

    finally:
        if not dry_run:
            if xp_source is not None:
                xp_source.stop()
            if xp_sink is not None:
                xp_sink.close()

        print(f"\n[SCENARIO] Complete. Events: scenario_{scenario_name}.jsonl\n")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("Examples:")
        print("  python sim/examples/run_scenario.py level_flight")
        print("  python sim/examples/run_scenario.py gentle_climb")
        print("  python sim/examples/run_scenario.py steep_turn")
        sys.exit(0)

    scenario_name = sys.argv[1]
    plot = "--plot" in sys.argv

    try:
        run_scenario(scenario_name, dry_run=True)  # Default to dry-run
    except KeyboardInterrupt:
        print("\n[SCENARIO] Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
