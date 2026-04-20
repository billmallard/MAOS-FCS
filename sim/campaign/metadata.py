"""Run metadata envelope writer (issue P0-A3).

Writes run_env.json alongside each scenario artifact with fields needed for
deterministic replay and traceability: run_id, scenario_id, seed, git_commit,
and timestamp_utc.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


@dataclass
class RunMetadata:
    run_id: str
    scenario_id: str
    seed: Optional[int]
    git_commit: str
    timestamp_utc: str


def write_run_env(
    artifact_dir: Path,
    scenario_id: str,
    *,
    stem: str = "run_env",
    seed: Optional[int] = None,
) -> RunMetadata:
    """Write <stem>.json to artifact_dir and return the metadata."""
    meta = RunMetadata(
        run_id=str(uuid.uuid4()),
        scenario_id=scenario_id,
        seed=seed,
        git_commit=_git_commit(),
        timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    out = artifact_dir / f"{stem}.json"
    out.write_text(json.dumps(asdict(meta), indent=2) + "\n", encoding="utf-8")
    return meta
