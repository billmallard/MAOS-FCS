#!/usr/bin/env python3
"""Run X-Plane SIL matrix campaigns for issue #22 (XTE).

This script writes a temporary manifest and delegates execution to
`tools/testing/run_sil_campaign_webapi.py`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Active waypoint: 40.0°N, 88.0°W; desired course: 090° (due east)
# All scenarios start near that point at 100 KIAS heading east.
#
# Sign convention (FIX-Gateway unit tests, compute.py):
#   Negative XTE => aircraft north (left) of eastbound course
#   Positive XTE => aircraft south (right) of eastbound course
#
# Note: the test-matrix document X-PLANE-TEST-MATRIX-PHASE-1B.md had this inverted.
# Oracle ranges below use the correct FIX-Gateway convention.
#
# Lat offset reference: 0.05° ≈ 3.0 nm; 0.5° ≈ 30 nm.

_WP_LAT = 40.0
_WP_LON = -88.0
_COURSE = 90.0

SCENARIOS: List[Dict[str, Any]] = [
    # 22.1: Aircraft starts on course (40.0°N). XTE should remain near zero.
    # Oracle ±0.5 nm: the FCS SIL has no lateral autopilot, so the C172's natural
    # prop-induced drift (~0.3 nm over 5 min) is within this bound. This validates
    # that the XTE compute function returns near-zero when on-course, not that the
    # aircraft holds track precisely.
    {
        "id": "22.1",
        "name": "xte_22_1_on_course_zero",
        "cycles": 300,
        "hz": 20,
        "gust": False,
        "init_lat": 40.0,
        "init_lon": -88.0,
        "init_heading_deg": 90.0,
        "extra_sil_args": [
            "--xte-wp-lat", str(_WP_LAT),
            "--xte-wp-lon", str(_WP_LON),
            "--xte-course", str(_COURSE),
            "--xte-sample-start", "30",
            "--xte-sample-end", "270",
            "--xte-min-nm", "-0.50",
            "--xte-max-nm", "0.50",
        ],
    },
    # 22.2: Aircraft starts 0.05° (≈3 nm) SOUTH of course.
    # FIX-Gateway: south of eastbound → positive XTE ≈ +3.0 nm.
    {
        "id": "22.2",
        "name": "xte_22_2_left_deviation_negative",
        "cycles": 300,
        "hz": 20,
        "gust": False,
        "init_lat": 39.95,
        "init_lon": -88.0,
        "init_heading_deg": 90.0,
        "extra_sil_args": [
            "--xte-wp-lat", str(_WP_LAT),
            "--xte-wp-lon", str(_WP_LON),
            "--xte-course", str(_COURSE),
            "--xte-sample-start", "30",
            "--xte-sample-end", "270",
            "--xte-min-nm", "2.5",
            "--xte-max-nm", "3.5",
        ],
    },
    # 22.3: Aircraft starts 0.05° (≈3 nm) NORTH of course.
    # FIX-Gateway: north of eastbound → negative XTE ≈ -3.0 nm.
    {
        "id": "22.3",
        "name": "xte_22_3_right_deviation_positive",
        "cycles": 300,
        "hz": 20,
        "gust": False,
        "init_lat": 40.05,
        "init_lon": -88.0,
        "init_heading_deg": 90.0,
        "extra_sil_args": [
            "--xte-wp-lat", str(_WP_LAT),
            "--xte-wp-lon", str(_WP_LON),
            "--xte-course", str(_COURSE),
            "--xte-sample-start", "30",
            "--xte-sample-end", "270",
            "--xte-min-nm", "-3.5",
            "--xte-max-nm", "-2.5",
        ],
    },
    # 22.4: Aircraft starts 0.5° (≈30 nm) NORTH of course.
    # FIX-Gateway: north → strongly negative XTE ≈ -30 nm.
    # Tests that large deviations don't saturate or wrap.
    {
        "id": "22.4",
        "name": "xte_22_4_large_deviation_recovery",
        "cycles": 600,
        "hz": 20,
        "gust": False,
        "init_lat": 40.5,
        "init_lon": -88.0,
        "init_heading_deg": 90.0,
        "extra_sil_args": [
            "--xte-wp-lat", str(_WP_LAT),
            "--xte-wp-lon", str(_WP_LON),
            "--xte-course", str(_COURSE),
            "--xte-sample-start", "30",
            "--xte-sample-end", "270",
            "--xte-max-nm", "-25.0",
        ],
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    selected_ids = set(args.tests) if args.tests else {s["id"] for s in SCENARIOS}
    selected = [s for s in SCENARIOS if s["id"] in selected_ids]
    if not selected:
        raise ValueError("No scenarios selected. Use --tests with values like 22.1 22.2")

    return {
        "host": args.host,
        "port": args.port,
        "repeats": args.repeats,
        "reset_each_run": True,
        "reset_wait_s": 10,
        "reset_request_timeout_s": 90,
        "reset_retries": 2,
        "airborne_after_reset": True,
        "airborne_altitude_agl_ft": 3000,
        "airborne_airspeed_kias": 100,
        "airborne_wait_s": 3,
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
                "time_in_24_hours": 12.0
            }
        },
        "scenarios": [
            {
                "scenario_id": item["id"],
                "name": item["name"],
                "cycles": item["cycles"],
                "hz": item["hz"],
                "gust": item["gust"],
                "init_lat": item.get("init_lat"),
                "init_lon": item.get("init_lon"),
                "init_heading_deg": item.get("init_heading_deg", 90.0),
                "extra_sil_args": item.get("extra_sil_args", []),
            }
            for item in selected
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run issue #22 XTE SIL matrix")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8086)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--tests", nargs="*", help="Subset test IDs, e.g. 22.1 22.2")
    parser.add_argument("--throttle", type=float, default=0.70, help="Post-reset throttle ratio")
    parser.add_argument("--mixture", type=float, default=1.0, help="Post-reset mixture ratio")
    parser.add_argument("--propulsion-hold-s", type=float, default=4.0)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    repo_root = _repo_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_dir = repo_root / "logs" / "sil_campaign" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"xte_matrix_{ts}.json"

    manifest = _build_manifest(args)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[xte-matrix] manifest: {manifest_path.relative_to(repo_root)}")

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "testing" / "run_sil_campaign_webapi.py"),
        "--manifest",
        str(manifest_path),
        "--stabilize-on-exit",
    ]
    print("[xte-matrix] command:", " ".join(cmd))

    if args.print_only:
        return 0

    result = subprocess.run(cmd, cwd=repo_root)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
