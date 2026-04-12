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
"""

from __future__ import annotations

import argparse
import json
import os
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


def force_unpause(host: str, port: int) -> None:
    # Prefer direct dataref write so this remains deterministic (no pause-toggle ambiguity).
    dr_name = "sim/time/paused"
    dr_id = _get_dataref_id(host, port, dr_name)
    if dr_id is None:
        print(f"[campaign] warning: could not resolve {dr_name}, leaving pause state unchanged")
        return

    url = f"{_api_base(host, port)}/datarefs/{dr_id}/value"
    resp = requests.patch(url, json={"data": 0}, timeout=3.0)
    resp.raise_for_status()
    print("[campaign] sim unpause command sent (sim/time/paused=0)")


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
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_root = repo_root / "logs" / "sil_campaign"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    host = args.host
    port = args.port
    repeats = args.repeats

    scenarios: List[Dict[str, Any]]
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = (repo_root / manifest_path).resolve()
        manifest = load_manifest(manifest_path)
        host = manifest.get("host", host)
        port = int(manifest.get("port", port))
        repeats = int(manifest.get("repeats", repeats))
        scenarios = [dict(s) for s in manifest["scenarios"]]
        print(f"[campaign] using manifest: {manifest_path}")
    else:
        base_scenarios = DEFAULT_SCENARIOS if args.profile == "default" else SMOKE_SCENARIOS
        scenarios = [dict(s) for s in base_scenarios]
        if args.include_gust:
            scenarios.append({"name": "runway_idle_gust", "cycles": 600, "hz": 20, "gust": True})

    try:
        check_web_api(host, port)
    except Exception as exc:
        print(f"[campaign] error: X-Plane Web API unavailable: {exc}")
        return 2

    try:
        force_unpause(host, port)
    except Exception as exc:
        print(f"[campaign] warning: could not force unpause: {exc}")

    summary: List[Dict[str, Any]] = []
    total = 0
    failures = 0

    for rep in range(1, repeats + 1):
        print(f"[campaign] repetition {rep}/{repeats}")
        for scenario in scenarios:
            total += 1
            log_name = f"{rep:03d}_{scenario['name']}.jsonl"
            log_path = run_dir / log_name
            rc = run_one_sil(repo_root, host, scenario, log_path)
            ok = rc == 0
            if not ok:
                failures += 1
            summary.append(
                {
                    "repeat": rep,
                    "scenario": scenario["name"],
                    "cycles": scenario["cycles"],
                    "hz": scenario["hz"],
                    "gust": scenario.get("gust", False),
                    "log": str(log_path.relative_to(repo_root)),
                    "return_code": rc,
                    "ok": ok,
                }
            )

    summary_path = run_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "host": host,
                "port": port,
                "repeats": repeats,
                "total_runs": total,
                "failures": failures,
                "results": summary,
            },
            f,
            indent=2,
        )

    print(f"[campaign] complete: total_runs={total}, failures={failures}")
    print(f"[campaign] artifacts: {summary_path.relative_to(repo_root)}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
