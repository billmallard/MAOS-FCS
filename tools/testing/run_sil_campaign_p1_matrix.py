#!/usr/bin/env python3
"""Run MAOS-FCS SIL Phase-1 test matrix (issues #4–#13).

Defines all 12 P1 scenarios from docs/sil_phase1_test_matrix.md and delegates
execution to tools/testing/run_sil_campaign_webapi.py.

Scenario summary:
  P1-001  Triplex nominal — no faults, mode stays "triplex"
  P1-002  Lane C outlier injection — degradation trigger
  P1-003  Lane C recovery — triplex resume after bias clear
  P1-004  Stall approach — pitch protection engagement (IAS < 58 KIAS)
  P1-005  Overspeed approach — pitch protection at high IAS (> 165 KIAS)
  P1-006  Bank angle limit — roll protection at bank > 45°
  P1-007  Actuator frame roundtrip — frame count and no decode errors
  P1-008  Aircraft config baseline — ga_default.json loads and runs
  P1-009  Aircraft config multi-profile — ga_experimental.json priority arbitration
  P1-010  Provider registry arbitration — X-Plane provider dominates
  P1-011  X-Plane state freshness — >90 %% of cycles have fresh state
  P1-012  Event logging completeness — JSONL structure and field completeness
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default test coordinates: near KCMI at 4000 ft MSL, heading 090°
_INIT_LAT = 40.0
_INIT_LON = -88.0
_INIT_HEADING = 90.0

# Fault injection constants
_FAULT_CYCLE_30S = 600   # 30 s × 20 Hz
_FAULT_CYCLE_60S = 1200  # 60 s × 20 Hz

# Standard run lengths
_CYCLES_120S = 2400   # 2400 cycles @ 20 Hz = 120 s full scenario
_CYCLES_60S  = 1200   # 1200 cycles @ 20 Hz = 60 s  medium scenario
_CYCLES_30S  = 600    # 600 cycles  @ 20 Hz = 30 s  short scenario
_CYCLES_15S  = 300    # 300 cycles  @ 20 Hz = 15 s  quick scenario

# Protection thresholds (from ga_default.json control laws)
_STALL_THRESHOLD_KIAS      = 58.0
_OVERSPEED_THRESHOLD_KIAS  = 165.0
_MAX_BANK_DEG              = 45.0

# Airspeeds / attitudes for protection scenarios
# For stall: start well below threshold so protection fires on first cycle
_STALL_INIT_KIAS      = 52.0
# For bank: start with 75° bank so protection fires before the C172's dihedral
# recovers to below 45°.
_BANK_INIT_DEG        = 75.0


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: List[Dict[str, Any]] = [
    # ── P1-001: Triplex nominal ────────────────────────────────────────────
    # All three lanes healthy. 60 s is ample to confirm stable triplex.
    # Oracle: mode never leaves "triplex", zero transitions, no protections.
    {
        "id": "P1-001",
        "name": "p1_001_triplex_nominal",
        "cycles": _CYCLES_60S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--assert-mode-stable",        "triplex",
            "--assert-transitions-max",    "0",
            "--assert-protection-never",   "stall_protection_active",
            "--assert-protection-never",   "overspeed_protection_active",
            "--assert-protection-never",   "bank_protection_active",
            "--assert-frames-min",         "1100",
            "--assert-state-fresh-min-pct", "90.0",
        ],
    },

    # ── P1-002: Lane C outlier — degradation trigger ───────────────────────
    # +0.15 bias injected at T=30 s (cycle 600). Voter threshold is 0.08.
    # Oracle: at least one transition, first transition within 2 cycles of
    # fault_start, final mode "degraded".
    {
        "id": "P1-002",
        "name": "p1_002_lane_c_outlier_degradation",
        "cycles": _CYCLES_120S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--fault-start-cycle",         str(_FAULT_CYCLE_30S),
            "--fault-bias",                "0.15",
            "--assert-mode-final",         "degraded",
            "--assert-transitions-min",    "1",
            "--assert-transition-within",  "2",
            "--assert-frames-min",         "2300",
        ],
    },

    # ── P1-003: Lane C recovery — triplex resume ───────────────────────────
    # Bias injected at T=30 s, cleared at T=60 s. Both transitions expected:
    # triplex→degraded at T=30 s, degraded→triplex at T=60 s.
    # Oracle: at least 2 transitions, final mode "triplex".
    {
        "id": "P1-003",
        "name": "p1_003_lane_c_recovery_triplex_resume",
        "cycles": _CYCLES_120S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--fault-start-cycle",         str(_FAULT_CYCLE_30S),
            "--fault-bias",                "0.15",
            "--fault-clear-cycle",         str(_FAULT_CYCLE_60S),
            "--assert-mode-final",         "triplex",
            "--assert-transitions-min",    "2",
            "--assert-transition-within",  "2",
            "--assert-frames-min",         "2300",
        ],
    },

    # ── P1-004: Stall protection engagement ───────────────────────────────
    # Aircraft starts at 52 KIAS with near-idle throttle (0.15) so that the
    # propulsion hold does not accelerate the aircraft past the 58 KIAS
    # protection threshold before the SIL starts.
    # Oracle: stall_protection_active fires at least once.
    {
        "id": "P1-004",
        "name": "p1_004_stall_protection_engagement",
        "cycles": _CYCLES_15S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "init_airspeed_kias": _STALL_INIT_KIAS,
        "init_throttle_ratio": 0.0,
        "init_propulsion_hold_s": 0.0,
        "engage_autopilot": False,
        "extra_sil_args": [
            "--assert-protection-fires",   "stall_protection_active",
            "--assert-frames-min",         "280",
        ],
    },

    # ── P1-005: Overspeed protection engagement ────────────────────────────
    # Aircraft starts at level flight (100 KIAS), then 15° nose-down + 90%
    # throttle for 12 s before the SIL starts. At that point IAS is well
    # above the 165 KIAS threshold and overspeed protection fires immediately.
    # (Velocity injection at 175 KIAS exceeds the C172SP Vne and triggers
    # X-Plane structural failure before the SIL reads a single overspeed cycle.)
    # Oracle: overspeed_protection_active fires at least once.
    {
        "id": "P1-005",
        "name": "p1_005_overspeed_protection_engagement",
        "cycles": _CYCLES_15S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "init_pitch_deg": -15.0,
        "init_elev_trim": -0.8,
        "init_position_wait_s": 0.0,
        "init_throttle_ratio": 0.90,
        "init_propulsion_hold_s": 12.0,
        "engage_autopilot": False,
        "extra_sil_args": [
            "--assert-protection-fires",   "overspeed_protection_active",
            "--assert-frames-min",         "280",
        ],
    },

    # ── P1-006: Bank angle protection engagement ───────────────────────────
    # Aircraft starts at 75° bank. Both position-inject settle and propulsion
    # hold are set to 0 so the SIL starts within ~0.1 s of the position write
    # while bank is still well above the 45° threshold.
    # Oracle: bank_angle_protection_active fires at least once.
    {
        "id": "P1-006",
        "name": "p1_006_bank_angle_protection_engagement",
        "cycles": _CYCLES_15S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "init_bank_deg": _BANK_INIT_DEG,
        "init_position_wait_s": 0.0,
        "init_throttle_ratio": 0.70,
        "init_propulsion_hold_s": 0.0,
        "engage_autopilot": False,
        "extra_sil_args": [
            "--assert-protection-fires",   "bank_protection_active",
            "--assert-frames-min",         "280",
        ],
    },

    # ── P1-007: Actuator frame roundtrip ──────────────────────────────────
    # Nominal triplex run. CRC checks are embedded in the FCS runtime;
    # any failure drops the frame count below the minimum.
    # Oracle: ≥1100 frames, mode stable "triplex", state fresh >90 %.
    {
        "id": "P1-007",
        "name": "p1_007_actuator_frame_roundtrip",
        "cycles": _CYCLES_60S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--assert-mode-stable",        "triplex",
            "--assert-frames-min",         "1100",
            "--assert-state-fresh-min-pct", "90.0",
        ],
    },

    # ── P1-008: Aircraft config baseline (ga_default.json) ────────────────
    # Verifies ga_default.json loads and the SIL loop runs to completion.
    # A startup parse error would exit with rc≠0 before any frames are logged.
    # Oracle: ≥500 frames emitted (config loaded, loop ran).
    {
        "id": "P1-008",
        "name": "p1_008_aircraft_config_baseline",
        "cycles": _CYCLES_30S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--assert-frames-min", "500",
        ],
    },

    # ── P1-009: Aircraft config multi-profile (ga_experimental.json) ──────
    # Verifies ga_experimental.json loads (smart-ema, generic-servo, fadec-bridge)
    # and the SIL loop runs with the experimental profile active.
    # Oracle: ≥500 frames emitted (config loaded, loop ran).
    {
        "id": "P1-009",
        "name": "p1_009_aircraft_config_multi_profile",
        "cycles": _CYCLES_30S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "aircraft_config": "configs/aircraft/ga_experimental.json",
        "extra_sil_args": [
            "--assert-frames-min", "500",
        ],
    },

    # ── P1-010: Provider registry arbitration ─────────────────────────────
    # X-Plane provider (higher priority) should dominate neutral_trim (0.0).
    # With X-Plane connected and flying, pitch commands will be non-zero.
    # Oracle: state fresh >90 % (X-Plane provider active), frames ≥500.
    {
        "id": "P1-010",
        "name": "p1_010_provider_registry_arbitration",
        "cycles": _CYCLES_30S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--assert-frames-min",          "500",
            "--assert-state-fresh-min-pct", "90.0",
        ],
    },

    # ── P1-011: X-Plane state freshness ───────────────────────────────────
    # 60 s run. With X-Plane connected, >90 % of cycles should have fresh
    # state (timeout 0.5 s). Validates FCS-SIL-002 freshness tracking.
    # Oracle: state_fresh_min_pct ≥ 90 %, frames ≥ 1100.
    {
        "id": "P1-011",
        "name": "p1_011_xplane_state_freshness",
        "cycles": _CYCLES_60S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--assert-frames-min",          "1100",
            "--assert-state-fresh-min-pct", "90.0",
        ],
    },

    # ── P1-012: Event logging completeness ────────────────────────────────
    # Fault-injection run so the log contains mode transitions + sil_start.
    # Oracle: ≥1100 frames, ≥1 transition.
    {
        "id": "P1-012",
        "name": "p1_012_event_logging_completeness",
        "cycles": _CYCLES_60S,
        "hz": 20,
        "gust": False,
        "init_lat": _INIT_LAT,
        "init_lon": _INIT_LON,
        "init_heading_deg": _INIT_HEADING,
        "extra_sil_args": [
            "--fault-start-cycle",         str(_FAULT_CYCLE_30S),
            "--fault-bias",                "0.15",
            "--assert-transitions-min",    "1",
            "--assert-frames-min",         "1100",
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    selected_ids = set(args.tests) if args.tests else {s["id"] for s in SCENARIOS}
    selected = [s for s in SCENARIOS if s["id"] in selected_ids]
    if not selected:
        raise ValueError(
            "No scenarios selected. Use --tests with values like P1-001 P1-002"
        )

    repo_root = _repo_root()
    scenario_list = []
    for item in selected:
        extra_args = list(item.get("extra_sil_args", []))

        # Inject --aircraft-config for scenarios that need a non-default config
        if "aircraft_config" in item:
            cfg_path = str(repo_root / item["aircraft_config"])
            extra_args = ["--aircraft-config", cfg_path] + extra_args

        entry: Dict[str, Any] = {
            "scenario_id": item["id"],
            "name": item["name"],
            "cycles": item["cycles"],
            "hz": item["hz"],
            "gust": item["gust"],
            "init_lat": item.get("init_lat"),
            "init_lon": item.get("init_lon"),
            "init_heading_deg": item.get("init_heading_deg", _INIT_HEADING),
            "extra_sil_args": extra_args,
        }
        for key in (
            "init_airspeed_kias",
            "init_bank_deg",
            "init_pitch_deg",
            "init_elev_trim",
            "init_position_wait_s",
            "init_throttle_ratio",
            "init_propulsion_hold_s",
            "engage_autopilot",
        ):
            if key in item:
                entry[key] = item[key]

        scenario_list.append(entry)

    return {
        "host": args.host,
        "port": args.port,
        "repeats": args.repeats,
        "reset_each_run": True,
        "reset_wait_s": 10,
        "reset_request_timeout_s": 90,
        "reset_retries": 2,
        "airborne_after_reset": True,
        "airborne_altitude_agl_ft": 4000,
        "airborne_airspeed_kias": 100,
        "airborne_wait_s": 3,
        "engage_autopilot_after_reset": True,
        "post_reset_throttle_ratio": args.throttle,
        "post_reset_mixture_ratio": args.mixture,
        "post_reset_propulsion_hold_s": args.propulsion_hold_s,
        "startup_flight": {
            "aircraft": {
                "path": "Aircraft/Laminar Research/Cessna 172 SP/Cessna_172SP.acf"
            },
            "runway_start": {
                "airport_id": "KCMI",
                "runway": "32L"
            },
            "local_time": {
                "day_of_year": 120,
                "time_in_24_hours": 12.0,
            },
        },
        "scenarios": scenario_list,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MAOS-FCS SIL Phase-1 test matrix"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8086)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--tests", nargs="*",
        help="Subset of test IDs to run, e.g. P1-001 P1-002 P1-006",
    )
    parser.add_argument(
        "--throttle", type=float, default=0.70,
        help="Post-reset throttle ratio (default 0.70)",
    )
    parser.add_argument(
        "--mixture", type=float, default=1.0,
        help="Post-reset mixture ratio (default 1.0)",
    )
    parser.add_argument(
        "--propulsion-hold-s", type=float, default=4.0,
        help="Seconds to hold throttle/mixture after reset (default 4.0)",
    )
    parser.add_argument(
        "--print-only", action="store_true",
        help="Write manifest and print command without executing",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_dir = repo_root / "logs" / "sil_campaign" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"p1_matrix_{ts}.json"

    manifest = _build_manifest(args)
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[p1-matrix] manifest: {manifest_path.relative_to(repo_root)}")

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "testing" / "run_sil_campaign_webapi.py"),
        "--manifest", str(manifest_path),
        "--stabilize-on-exit",
    ]
    print("[p1-matrix] command:", " ".join(cmd))

    if args.print_only:
        return 0

    result = subprocess.run(cmd, cwd=repo_root)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
