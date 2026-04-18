#!/usr/bin/env python3
"""Run X-Plane SIL matrix campaigns for issue #23 (Garmin adapter)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCENARIOS: List[Dict[str, Any]] = [
    {"id": "23.1", "name": "garmin_23_1_position_accuracy", "cycles": 600, "hz": 20, "gust": False},
    {"id": "23.2", "name": "garmin_23_2_velocity_track", "cycles": 360, "hz": 20, "gust": False},
    {"id": "23.3", "name": "garmin_23_3_cold_start", "cycles": 420, "hz": 20, "gust": False},
    {"id": "23.4", "name": "garmin_23_4_latency_budget", "cycles": 300, "hz": 20, "gust": False},
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    selected_ids = set(args.tests) if args.tests else {s["id"] for s in SCENARIOS}
    selected = [s for s in SCENARIOS if s["id"] in selected_ids]
    if not selected:
        raise ValueError("No scenarios selected. Use --tests with values like 23.1 23.2")

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
                "airport_id": "KPDX",
                "runway": "28L"
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
            }
            for item in selected
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run issue #23 Garmin SIL matrix")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8086)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--tests", nargs="*", help="Subset test IDs, e.g. 23.1 23.2")
    parser.add_argument("--throttle", type=float, default=0.70, help="Post-reset throttle ratio")
    parser.add_argument("--mixture", type=float, default=1.0, help="Post-reset mixture ratio")
    parser.add_argument("--propulsion-hold-s", type=float, default=4.0)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    repo_root = _repo_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_dir = repo_root / "logs" / "sil_campaign" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"garmin_matrix_{ts}.json"

    manifest = _build_manifest(args)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[garmin-matrix] manifest: {manifest_path.relative_to(repo_root)}")

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "testing" / "run_sil_campaign_webapi.py"),
        "--manifest",
        str(manifest_path),
        "--stabilize-on-exit",
    ]
    print("[garmin-matrix] command:", " ".join(cmd))

    if args.print_only:
        return 0

    result = subprocess.run(cmd, cwd=repo_root)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
